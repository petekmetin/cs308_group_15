import logging

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Order, Invoice, Delivery
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    InvoiceSerializer, DeliverySerializer
)
from .services import email_invoice_pdf
from config.permissions import IsCustomer, IsSalesManager, IsProductManager
from products.models import Sneaker
from products.querysets import sneaker_summary_queryset

logger = logging.getLogger(__name__)


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
    order = optimized_order_queryset().get(pk=order.pk)
    return Response(OrderSerializer(order).data)


# ─── Invoices ─────────────────────────────────────────────────────────────────

class InvoiceListView(generics.ListAPIView):
    """
    GET /api/orders/invoices/
    Sales managers can filter by date: ?from=2024-01-01&to=2024-12-31
    """
    serializer_class = InvoiceSerializer
    permission_classes = [IsSalesManager]

    def get_queryset(self):
        qs = Invoice.objects.all().select_related('order__customer')
        from_date = self.request.query_params.get('from')
        to_date = self.request.query_params.get('to')
        if from_date:
            qs = qs.filter(issued_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(issued_at__date__lte=to_date)
        return qs


# ─── Deliveries ───────────────────────────────────────────────────────────────

class DeliveryListView(generics.ListAPIView):
    """
    GET /api/orders/deliveries/
    Product managers only.
    """
    serializer_class = DeliverySerializer
    permission_classes = [IsProductManager]

    def get_queryset(self):
        return (
            Delivery.objects.select_related('order__customer')
            .prefetch_related(
                Prefetch(
                    'order__items__sneaker',
                    queryset=sneaker_summary_queryset(
                        Sneaker.objects.select_related('brand', 'category')
                    ),
                )
            )
            .filter(is_completed=False)
            .order_by('id')
        )


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
            delivery.order.status = 'processing'
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
