import logging
import os
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Order, Invoice, Delivery, OrderItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    InvoiceSerializer, InvoiceListSerializer, DeliverySerializer
)
from .services import email_invoice_pdf, generate_invoice_pdf
from config.permissions import IsCustomer, IsSalesManager, IsProductManager
from products.models import Sneaker, SneakerImage
from products.querysets import sneaker_summary_queryset

logger = logging.getLogger(__name__)


def money(value):
    amount = Decimal(str(value or 0)).quantize(Decimal('0.01'))
    return f'{amount:.2f}'


def parse_report_range(request):
    today = timezone.localdate()
    from_raw = request.query_params.get('from')
    to_raw = request.query_params.get('to')
    from_date = parse_date(from_raw) if from_raw else today - timedelta(days=30)
    to_date = parse_date(to_raw) if to_raw else today

    if from_date is None or to_date is None:
        return None, None, Response(
            {'detail': 'Use YYYY-MM-DD dates for from and to.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if from_date > to_date:
        return None, None, Response(
            {'detail': 'from must be before or equal to to.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return from_date, to_date, None


def optimized_order_queryset():
    return (
        Order.objects.select_related('customer', 'invoice', 'delivery')
        .prefetch_related(
            Prefetch(
                'items__sneaker',
                queryset=sneaker_summary_queryset(
                    Sneaker.objects.select_related('brand', 'category')
                ),
            )
        )
    )


def sync_delivery_from_order(order, *, status, is_completed=None):
    try:
        delivery = order.delivery
    except Delivery.DoesNotExist:
        return None

    delivery.status = status
    if is_completed is not None:
        delivery.is_completed = is_completed
    if status in {'cancelled', 'return_requested', 'returned', 'failed'}:
        delivery.is_completed = False
    if status in {'cancelled', 'return_requested', 'returned', 'failed', 'processing'}:
        delivery.delivered_at = None
    delivery.save(update_fields=['status', 'is_completed', 'delivered_at'])
    return delivery


class OrderListView(generics.ListAPIView):
    """
    GET /api/orders/
    Customers see their own orders.
    Managers see all orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        base_queryset = optimized_order_queryset()
        user = self.request.user
        if user.role == 'customer':
            return base_queryset.filter(customer=user)
        return base_queryset


class OrderCreateView(generics.CreateAPIView):
    """
    POST /api/orders/create/
    Customers only. Returns the full order plus invoice_number.
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsCustomer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        order = optimized_order_queryset().get(pk=order.pk)
        data = OrderSerializer(order, context={'request': request}).data
        try:
            data['invoice_number'] = order.invoice.invoice_number
        except Exception:
            data['invoice_number'] = None
        try:
            email_invoice_pdf(order.invoice)
            data['invoice_email_sent'] = True
        except Exception:
            logger.exception('Invoice email failed for order %s', order.id)
            data['invoice_email_sent'] = False
            data['invoice_email_error'] = 'Invoice email could not be sent.'
        return Response(data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/orders/<pk>/
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        base_queryset = optimized_order_queryset()
        user = self.request.user
        if user.role == 'customer':
            return base_queryset.filter(customer=user)
        return base_queryset


@api_view(['POST'])
@permission_classes([IsCustomer])
def cancel_order(request, pk):
    """
    POST /api/orders/<pk>/cancel/
    Customers can cancel pending or processing orders.
    """
    try:
        order = Order.objects.get(pk=pk, customer=request.user)
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found.'}, status=404)

    if order.status not in ('pending', 'processing'):
        return Response(
            {'detail': f'Cannot cancel an order with status "{order.status}".'},
            status=400
        )

    with transaction.atomic():
        for item in order.items.select_related('size').all():
            if item.size:
                item.size.stock += item.quantity
                item.size.save()

        order.status = 'cancelled'
        order.save(update_fields=['status'])
        sync_delivery_from_order(order, status='cancelled')
    order = optimized_order_queryset().get(pk=order.pk)
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([IsCustomer])
def request_refund(request, pk):
    """
    POST /api/orders/<pk>/refund/
    Customer can request refund within 30 days of delivery.
    """
    try:
        order = Order.objects.get(pk=pk, customer=request.user)
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found.'}, status=404)

    if order.status != 'delivered':
        return Response({'detail': 'Only delivered orders can be refunded.'}, status=400)

    days_since_delivery = (timezone.now() - order.updated_at).days
    if days_since_delivery > 30:
        return Response({'detail': 'Refund window of 30 days has passed.'}, status=400)

    order.status = 'return_requested'
    order.refund_requested_at = timezone.now()
    order.save(update_fields=['status', 'refund_requested_at'])
    sync_delivery_from_order(order, status='return_requested')
    order = optimized_order_queryset().get(pk=order.pk)
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([IsSalesManager])
def approve_refund(request, pk):
    """
    POST /api/orders/<pk>/approve-refund/
    Sales managers approve or deny refund requests.
    """
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if order.status != 'return_requested':
        return Response({'detail': 'Order is not awaiting refund.'}, status=400)

    with transaction.atomic():
        for item in order.items.select_related('size').all():
            if item.size:
                item.size.stock += item.quantity
                item.size.save()

        order.status = 'returned'
        order.refund_approved_at = timezone.now()
        order.refund_amount = order.total_price
        order.save(update_fields=['status', 'refund_approved_at', 'refund_amount'])
        sync_delivery_from_order(order, status='returned')
    order = optimized_order_queryset().get(pk=order.pk)
    return Response(OrderSerializer(order).data)


# ─── Invoices ─────────────────────────────────────────────────────────────────

class InvoiceListView(generics.ListAPIView):
    """
    GET /api/orders/invoices/
    Sales managers can filter by date: ?from=2024-01-01&to=2024-12-31
    """
    serializer_class = InvoiceListSerializer
    permission_classes = [IsSalesManager]

    def get_queryset(self):
        qs = Invoice.objects.select_related('order__customer').only(
            'id',
            'invoice_number',
            'issued_at',
            'pdf_path',
            'notes',
            'order__id',
            'order__customer_id',
            'order__customer__email',
            'order__status',
            'order__total_price',
            'order__delivery_address',
            'order__credit_card_last4',
            'order__created_at',
            'order__updated_at',
        )
        from_date = self.request.query_params.get('from')
        to_date = self.request.query_params.get('to')
        if from_date:
            qs = qs.filter(issued_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(issued_at__date__lte=to_date)
        return qs


@api_view(['GET'])
@permission_classes([IsSalesManager])
def invoice_pdf(request, pk):
    """
    GET /api/orders/invoices/<pk>/pdf/
    Sales managers download an invoice PDF, generating it if needed.
    """
    try:
        invoice = Invoice.objects.select_related('order__customer').get(pk=pk)
    except Invoice.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    absolute_path = ''
    if invoice.pdf_path:
        absolute_path = os.path.join(settings.MEDIA_ROOT, invoice.pdf_path)
    if not absolute_path or not os.path.exists(absolute_path):
        absolute_path = generate_invoice_pdf(invoice)

    with open(absolute_path, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsSalesManager])
def sales_summary_report(request):
    """
    GET /api/orders/reports/sales-summary/?from=YYYY-MM-DD&to=YYYY-MM-DD
    Revenue excludes cancelled orders. Profit subtracts product cost and approved refunds.
    """
    from_date, to_date, error_response = parse_report_range(request)
    if error_response is not None:
        return error_response

    orders = (
        Order.objects.exclude(status='cancelled')
        .filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
        .only('id', 'status', 'total_price', 'created_at')
        .prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('sneaker').only(
                    'id',
                    'order_id',
                    'sneaker_id',
                    'sneaker__id',
                    'sneaker__cost_price',
                    'quantity',
                ),
            )
        )
        .order_by('created_at')
    )
    refunds = (
        Order.objects.filter(
            refund_approved_at__date__gte=from_date,
            refund_approved_at__date__lte=to_date,
        )
        .exclude(refund_amount__isnull=True)
        .only('id', 'refund_approved_at', 'refund_amount')
        .order_by('refund_approved_at')
    )

    daily = defaultdict(lambda: {
        'revenue': Decimal('0.00'),
        'refunds': Decimal('0.00'),
        'cost': Decimal('0.00'),
        'orders_count': 0,
        'units_sold': 0,
    })

    for order in orders:
        day = timezone.localtime(order.created_at).date().isoformat()
        daily[day]['revenue'] += Decimal(order.total_price or 0)
        daily[day]['orders_count'] += 1
        for item in order.items.all():
            quantity = int(item.quantity or 0)
            daily[day]['units_sold'] += quantity
            daily[day]['cost'] += Decimal(item.sneaker.cost_price or 0) * quantity

    for order in refunds:
        day = timezone.localtime(order.refund_approved_at).date().isoformat()
        daily[day]['refunds'] += Decimal(order.refund_amount or 0)

    totals_raw = {
        'revenue': Decimal('0.00'),
        'refunds': Decimal('0.00'),
        'cost': Decimal('0.00'),
        'orders_count': 0,
        'units_sold': 0,
    }
    series = []
    current_day = from_date
    while current_day <= to_date:
        key = current_day.isoformat()
        row = daily[key]
        net_profit = row['revenue'] - row['refunds'] - row['cost']
        profit = max(net_profit, Decimal('0.00'))
        loss = max(-net_profit, Decimal('0.00'))
        for field in totals_raw:
            totals_raw[field] += row[field]
        if row['orders_count'] or row['units_sold'] or row['refunds']:
            series.append({
                'date': key,
                'revenue': money(row['revenue']),
                'refunds': money(row['refunds']),
                'cost': money(row['cost']),
                'profit': money(profit),
                'loss': money(loss),
                'net_profit': money(net_profit),
                'orders_count': row['orders_count'],
                'units_sold': row['units_sold'],
            })
        current_day += timedelta(days=1)

    total_net_profit = totals_raw['revenue'] - totals_raw['refunds'] - totals_raw['cost']
    totals = {
        'revenue': money(totals_raw['revenue']),
        'refunds': money(totals_raw['refunds']),
        'cost': money(totals_raw['cost']),
        'profit': money(max(total_net_profit, Decimal('0.00'))),
        'loss': money(max(-total_net_profit, Decimal('0.00'))),
        'net_profit': money(total_net_profit),
        'orders_count': totals_raw['orders_count'],
        'units_sold': totals_raw['units_sold'],
    }

    return Response({
        'from': from_date.isoformat(),
        'to': to_date.isoformat(),
        'totals': totals,
        'series': series,
    })


# ─── Deliveries ───────────────────────────────────────────────────────────────

class DeliveryListView(generics.ListAPIView):
    """
    GET /api/orders/deliveries/
    Product managers only.
    """
    serializer_class = DeliverySerializer
    permission_classes = [IsProductManager]

    def get_queryset(self):
        queryset = (
            Delivery.objects.select_related('order__invoice')
            .only(
                'id',
                'order_id',
                'status',
                'tracking_number',
                'delivery_address',
                'is_completed',
                'dispatched_at',
                'delivered_at',
                'notes',
                'order__id',
                'order__customer_id',
                'order__status',
                'order__total_price',
                'order__created_at',
                'order__invoice__invoice_number',
            )
            .prefetch_related(
                Prefetch(
                    'order__items',
                    queryset=OrderItem.objects.select_related('sneaker__brand').only(
                        'id',
                        'order_id',
                        'sneaker_id',
                        'sneaker__id',
                        'sneaker__name',
                        'sneaker__brand_id',
                        'sneaker__brand__id',
                        'sneaker__brand__name',
                        'quantity',
                    ),
                )
            )
            .prefetch_related(
                Prefetch(
                    'order__items__sneaker__images',
                    queryset=SneakerImage.objects.order_by('-is_primary', 'order', 'id'),
                    to_attr='prefetched_images',
                )
            )
            .order_by('-id')
        )
        status_filter = (self.request.query_params.get('status') or '').strip().lower()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


@api_view(['PATCH'])
@permission_classes([IsProductManager])
def update_delivery(request, pk):
    """
    PATCH /api/orders/deliveries/<pk>/
    Product managers update delivery status.
    """
    try:
        delivery = Delivery.objects.get(pk=pk)
    except Delivery.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    allowed_statuses = {'pending', 'processing', 'in_transit', 'delivered', 'failed'}
    new_status = request.data.get('status')
    if new_status is not None and new_status not in allowed_statuses:
        return Response({'detail': 'Invalid status.'}, status=400)

    if new_status is not None:
        delivery.status = new_status

    if 'is_completed' in request.data:
        raw_completed = request.data.get('is_completed')
        if isinstance(raw_completed, bool):
            delivery.is_completed = raw_completed
        elif isinstance(raw_completed, str):
            lowered = raw_completed.strip().lower()
            if lowered in {'true', '1', 'yes'}:
                delivery.is_completed = True
            elif lowered in {'false', '0', 'no'}:
                delivery.is_completed = False
            else:
                return Response({'detail': 'Invalid is_completed value.'}, status=400)
        else:
            return Response({'detail': 'Invalid is_completed value.'}, status=400)

    with transaction.atomic():
        if delivery.status in {'processing', 'in_transit'}:
            delivery.is_completed = False
            delivery.delivered_at = None
            delivery.order.status = 'shipped' if delivery.status == 'in_transit' else 'processing'
            delivery.order.save(update_fields=['status'])
            if delivery.status == 'in_transit' and delivery.dispatched_at is None:
                delivery.dispatched_at = timezone.now()

        if delivery.status == 'delivered':
            delivery.is_completed = True
            delivery.delivered_at = timezone.now()
            delivery.order.status = 'delivered'
            delivery.order.save(update_fields=['status'])

        delivery.tracking_number = request.data.get('tracking_number', delivery.tracking_number)
        delivery.notes = request.data.get('notes', delivery.notes)
        delivery.save()

    return Response(DeliverySerializer(delivery).data)
