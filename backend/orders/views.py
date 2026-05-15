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

from .models import Order, Invoice, OrderItem, ReturnRequest, ReturnRequestItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    InvoiceSerializer, InvoiceListSerializer, DeliverySerializer, ReturnRequestSerializer
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
        Order.objects.select_related('customer', 'invoice')
        .prefetch_related(
            Prefetch(
                'items__sneaker',
                queryset=sneaker_summary_queryset(
                    Sneaker.objects.select_related('brand', 'category')
                ),
            )
        )
        .prefetch_related(
            Prefetch(
                'return_requests',
                queryset=ReturnRequest.objects.prefetch_related('items'),
                to_attr='prefetched_return_requests',
            )
        )
    )


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
        order.is_completed = False
        order.delivered_at = None
        order.save(update_fields=['status', 'is_completed', 'delivered_at'])
    order = optimized_order_queryset().get(pk=order.pk)
    return Response(OrderSerializer(order).data)


def _return_window_error(order):
    if order.status != 'delivered':
        return 'Only delivered orders can be refunded.'
    if not order.delivered_at:
        return 'Delivery completion date is missing for this order.'
    if (timezone.now() - order.delivered_at).days > 30:
        return 'Refund window of 30 days has passed.'
    return ''


def _normalize_return_items_payload(request):
    if isinstance(request.data.get('items'), list):
        return request.data.get('items')
    if request.data.get('order_item_id') is not None:
        return [{
            'order_item_id': request.data.get('order_item_id'),
            'quantity': request.data.get('quantity', 1),
        }]
    return []


def _already_requested_quantity(order_item):
    total = 0
    for request_item in order_item.return_request_items.select_related('return_request').filter(
        return_request__status__in=['requested', 'received', 'approved']
    ):
        total += request_item.quantity
    return total


def _create_return_request_for_items(*, order, customer, normalized_items):
    with transaction.atomic():
        return_request = ReturnRequest.objects.create(
            customer=customer,
            order=order,
            status='requested',
        )
        total = Decimal('0.00')
        for order_item, quantity in normalized_items:
            unit_amount = Decimal(order_item.unit_price or 0)
            subtotal = unit_amount * quantity
            ReturnRequestItem.objects.create(
                return_request=return_request,
                order_item=order_item,
                quantity=quantity,
                unit_refund_amount=unit_amount,
                subtotal_refund_amount=subtotal,
            )
            total += subtotal
        return_request.total_refund_amount = total
        return_request.save(update_fields=['total_refund_amount'])
        if order.refund_requested_at is None:
            order.refund_requested_at = timezone.now()
            order.save(update_fields=['refund_requested_at'])
    return return_request


@api_view(['POST'])
@permission_classes([IsCustomer])
def create_return_request(request, pk):
    """
    POST /api/orders/<pk>/returns/
    Customer requests a partial item-level return within 30 days of delivery.
    """
    try:
        order = Order.objects.prefetch_related('items').get(pk=pk, customer=request.user)
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found.'}, status=404)

    window_error = _return_window_error(order)
    if window_error:
        return Response({'detail': window_error}, status=400)

    raw_items = _normalize_return_items_payload(request)
    if not raw_items:
        return Response({'detail': 'Select at least one purchased item to return.'}, status=400)

    normalized_items = []
    for raw_item in raw_items:
        try:
            order_item_id = int(raw_item.get('order_item_id'))
            quantity = int(raw_item.get('quantity', 1))
        except (TypeError, ValueError):
            return Response({'detail': 'Return items need valid order_item_id and quantity.'}, status=400)
        if quantity < 1:
            return Response({'detail': 'Return quantity must be at least 1.'}, status=400)
        try:
            order_item = order.items.get(pk=order_item_id)
        except OrderItem.DoesNotExist:
            return Response({'detail': f'Order item {order_item_id} does not belong to this order.'}, status=400)
        remaining = order_item.quantity - _already_requested_quantity(order_item)
        if quantity > remaining:
            return Response(
                {'detail': f'Only {remaining} unit(s) remain returnable for item {order_item_id}.'},
                status=400,
            )
        normalized_items.append((order_item, quantity))

    return_request = _create_return_request_for_items(
        order=order,
        customer=request.user,
        normalized_items=normalized_items,
    )
    return_request = return_request_queryset().get(pk=return_request.pk)
    return Response(ReturnRequestSerializer(return_request).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsCustomer])
def request_refund(request, pk):
    """
    Backward-compatible full-order refund request.
    Prefer POST /api/orders/<pk>/returns/ for item-level returns.
    """
    try:
        order = Order.objects.prefetch_related('items').get(pk=pk, customer=request.user)
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found.'}, status=404)

    window_error = _return_window_error(order)
    if window_error:
        return Response({'detail': window_error}, status=400)

    normalized_items = [
        (item, item.quantity - _already_requested_quantity(item))
        for item in order.items.all()
        if item.quantity - _already_requested_quantity(item) > 0
    ]
    if not normalized_items:
        return Response({'detail': 'No returnable items remain for this order.'}, status=400)

    return_request = _create_return_request_for_items(
        order=order,
        customer=request.user,
        normalized_items=normalized_items,
    )
    return_request = return_request_queryset().get(pk=return_request.pk)
    return Response(ReturnRequestSerializer(return_request).data, status=status.HTTP_201_CREATED)


def return_request_queryset():
    return ReturnRequest.objects.select_related('customer', 'order').prefetch_related(
        Prefetch(
            'items',
            queryset=ReturnRequestItem.objects.select_related(
                'order_item__sneaker__brand',
                'order_item__size',
            ),
        )
    )


@api_view(['GET'])
@permission_classes([IsSalesManager])
def return_request_list(request):
    queryset = return_request_queryset()
    status_filter = (request.query_params.get('status') or '').strip().lower()
    if status_filter:
        if status_filter not in {'requested', 'received', 'approved', 'rejected'}:
            return Response({'detail': 'Invalid return request status.'}, status=400)
        queryset = queryset.filter(status=status_filter)
    return Response(ReturnRequestSerializer(queryset, many=True).data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsSalesManager])
def return_request_detail(request, pk):
    try:
        return_request = return_request_queryset().get(pk=pk)
    except ReturnRequest.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        return Response(ReturnRequestSerializer(return_request).data)

    new_status = request.data.get('status')
    manager_note = request.data.get('manager_note')
    if new_status not in {'received', 'approved', 'rejected'}:
        return Response({'detail': 'Status must be received, approved, or rejected.'}, status=400)
    if return_request.status in {'approved', 'rejected'}:
        return Response({'detail': 'This return request is already closed.'}, status=400)
    if new_status == 'approved' and return_request.status not in {'requested', 'received'}:
        return Response({'detail': 'Return request cannot be approved from its current status.'}, status=400)

    with transaction.atomic():
        return_request = ReturnRequest.objects.select_for_update().get(pk=return_request.pk)
        now = timezone.now()
        if manager_note is not None:
            return_request.manager_note = str(manager_note)
        if new_status == 'received':
            return_request.status = 'received'
            return_request.received_at = return_request.received_at or now
        elif new_status == 'rejected':
            return_request.status = 'rejected'
            return_request.rejected_at = now
        elif new_status == 'approved':
            for request_item in return_request.items.select_related('order_item__size').all():
                size = request_item.order_item.size
                if size:
                    size.stock += request_item.quantity
                    size.save(update_fields=['stock'])
            return_request.status = 'approved'
            return_request.received_at = return_request.received_at or now
            return_request.approved_at = now
            order = return_request.order
            approved_total = ReturnRequest.objects.filter(
                order=order,
                status='approved',
            ).exclude(pk=return_request.pk)
            total_refund = sum(
                Decimal(req.total_refund_amount or 0)
                for req in approved_total
            ) + Decimal(return_request.total_refund_amount or 0)
            order.refund_approved_at = now
            order.refund_amount = total_refund
            order.save(update_fields=['refund_approved_at', 'refund_amount'])
        return_request.save()

    return_request = return_request_queryset().get(pk=return_request.pk)
    return Response(ReturnRequestSerializer(return_request).data)


@api_view(['POST'])
@permission_classes([IsSalesManager])
def approve_refund(request, pk):
    """
    Backward-compatible endpoint: approve the oldest open return for an order.
    """
    return_request = (
        ReturnRequest.objects
        .filter(order_id=pk, status__in=['requested', 'received'])
        .order_by('requested_at')
        .first()
    )
    if return_request is None:
        return Response({'detail': 'Order is not awaiting refund.'}, status=400)
    with transaction.atomic():
        now = timezone.now()
        for request_item in return_request.items.select_related('order_item__size').all():
            size = request_item.order_item.size
            if size:
                size.stock += request_item.quantity
                size.save(update_fields=['stock'])
        return_request.status = 'approved'
        return_request.received_at = return_request.received_at or now
        return_request.approved_at = now
        return_request.save()
        order = return_request.order
        order.refund_approved_at = now
        order.refund_amount = sum(
            Decimal(req.total_refund_amount or 0)
            for req in ReturnRequest.objects.filter(order=order, status='approved')
        )
        order.save(update_fields=['refund_approved_at', 'refund_amount'])
    return_request = return_request_queryset().get(pk=return_request.pk)
    return Response(ReturnRequestSerializer(return_request).data)


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
        ReturnRequest.objects.filter(
            status='approved',
            approved_at__date__gte=from_date,
            approved_at__date__lte=to_date,
        )
        .only('id', 'approved_at', 'total_refund_amount')
        .order_by('approved_at')
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

    for refund in refunds:
        day = timezone.localtime(refund.approved_at).date().isoformat()
        daily[day]['refunds'] += Decimal(refund.total_refund_amount or 0)

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

def delivery_order_queryset():
    return (
        Order.objects.select_related('invoice')
        .only(
            'id',
            'status',
            'tracking_number',
            'delivery_address',
            'is_completed',
            'dispatched_at',
            'delivered_at',
            'delivery_notes',
            'customer_id',
            'total_price',
            'created_at',
            'invoice__invoice_number',
        )
        .prefetch_related(
            Prefetch(
                'items',
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
                'items__sneaker__images',
                queryset=SneakerImage.objects.order_by('-is_primary', 'order', 'id'),
                to_attr='prefetched_images',
            )
        )
        .order_by('-id')
    )


class DeliveryListView(generics.ListAPIView):
    """
    GET /api/orders/deliveries/
    Product managers only.
    """
    serializer_class = DeliverySerializer
    permission_classes = [IsProductManager]

    def get_queryset(self):
        queryset = delivery_order_queryset()
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
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    allowed_statuses = {'pending', 'processing', 'in_transit', 'delivered', 'failed'}
    new_status = request.data.get('status')
    if new_status is not None and new_status not in allowed_statuses:
        return Response({'detail': 'Invalid status.'}, status=400)

    if 'is_completed' in request.data:
        raw_completed = request.data.get('is_completed')
        if isinstance(raw_completed, bool):
            order.is_completed = raw_completed
        elif isinstance(raw_completed, str):
            lowered = raw_completed.strip().lower()
            if lowered in {'true', '1', 'yes'}:
                order.is_completed = True
            elif lowered in {'false', '0', 'no'}:
                order.is_completed = False
            else:
                return Response({'detail': 'Invalid is_completed value.'}, status=400)
        else:
            return Response({'detail': 'Invalid is_completed value.'}, status=400)

    with transaction.atomic():
        if new_status is not None:
            order.status = new_status
        if order.status in {'pending', 'processing', 'in_transit', 'failed'}:
            order.is_completed = False
            if order.status in {'pending', 'processing', 'failed'}:
                order.delivered_at = None
            if order.status == 'in_transit' and order.dispatched_at is None:
                order.dispatched_at = timezone.now()

        if order.status == 'delivered':
            order.is_completed = True
            order.delivered_at = order.delivered_at or timezone.now()

        order.tracking_number = request.data.get('tracking_number', order.tracking_number)
        order.delivery_notes = request.data.get('notes', order.delivery_notes)
        order.save()

    order = delivery_order_queryset().get(pk=order.pk)
    return Response(DeliverySerializer(order, context={'request': request}).data)
