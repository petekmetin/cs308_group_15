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
from config.permissions import IsCustomer, IsSalesManager, IsProductManager


class OrderListView(generics.ListAPIView):
    """
    GET /api/orders/
    Customers see their own orders.
    Managers see all orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Order.objects.filter(customer=user).prefetch_related('items__sneaker')
        return Order.objects.all().prefetch_related('items__sneaker')


class OrderCreateView(generics.CreateAPIView):
    """
    POST /api/orders/
    Customers only.
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsCustomer]

    def perform_create(self, serializer):
        serializer.save()


class OrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/orders/<pk>/
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Order.objects.filter(customer=user)
        return Order.objects.all()


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

    # Restore stock
    for item in order.items.select_related('size').all():
        if item.size:
            item.size.stock += item.quantity
            item.size.save()

    order.status = 'cancelled'
    order.save(update_fields=['status'])
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

    # Return stock to inventory
    for item in order.items.select_related('size').all():
        if item.size:
            item.size.stock += item.quantity
            item.size.save()

    order.status = 'returned'
    order.refund_approved_at = timezone.now()
    order.refund_amount = order.total_price
    order.save(update_fields=['status', 'refund_approved_at', 'refund_amount'])
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
        return Delivery.objects.select_related('order__customer').filter(
            is_completed=False
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

    new_status = request.data.get('status')
    if new_status == 'delivered':
        delivery.is_completed = True
        delivery.delivered_at = timezone.now()
        delivery.order.status = 'delivered'
        delivery.order.save(update_fields=['status'])

    delivery.status = new_status or delivery.status
    delivery.tracking_number = request.data.get('tracking_number', delivery.tracking_number)
    delivery.notes = request.data.get('notes', delivery.notes)
    delivery.save()

    return Response(DeliverySerializer(delivery).data)