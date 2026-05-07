from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from accounts.validators import get_customer_profile_errors
from .models import Order, OrderItem, Invoice, Delivery
from products.serializers import SneakerListSerializer
from products.models import Sneaker, SneakerSize


class OrderItemSerializer(serializers.ModelSerializer):
    sneaker_detail = SneakerListSerializer(source='sneaker', read_only=True)
    subtotal = serializers.ReadOnlyField()
    size_value = serializers.CharField(source='size.size', read_only=True)
    size_system = serializers.CharField(source='size.size_system', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'sneaker',
            'sneaker_detail',
            'size',
            'size_value',
            'size_system',
            'quantity',
            'unit_price',
            'subtotal',
        ]
        read_only_fields = ['unit_price']


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Used when a customer places an order.
    Validates stock, deducts inventory, and snapshots the current price.
    """
    items = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Order
        fields = ['id', 'delivery_address', 'credit_card_last4', 'items']

    def validate(self, attrs):
        customer = self.context['request'].user
        profile_errors = get_customer_profile_errors(customer)
        if profile_errors:
            raise serializers.ValidationError(profile_errors)
        return attrs

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('Order must contain at least one item.')

        for item in items:
            try:
                sneaker = Sneaker.objects.get(id=item['sneaker_id'])
            except Sneaker.DoesNotExist:
                raise serializers.ValidationError(f'Sneaker {item["sneaker_id"]} not found.')

            if sneaker.price is None:
                raise serializers.ValidationError(
                    f'{sneaker.name} does not have a price set yet.'
                )

            try:
                size = SneakerSize.objects.get(id=item['size_id'])
            except SneakerSize.DoesNotExist:
                raise serializers.ValidationError(f'Size {item["size_id"]} not found.')

            if size.stock < item.get('quantity', 1):
                raise serializers.ValidationError(
                    f'Insufficient stock for {sneaker.name} size {size.size}.'
                )

        return items

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        customer = self.context['request'].user

        order = Order.objects.create(
            customer=customer,
            status='processing',
            **validated_data,
        )

        total = 0
        for item_data in items_data:
            sneaker = Sneaker.objects.get(id=item_data['sneaker_id'])
            # select_for_update locks the row so concurrent requests queue up
            # rather than both reading the same stock value simultaneously.
            size = SneakerSize.objects.select_for_update().get(id=item_data['size_id'])
            quantity = item_data.get('quantity', 1)

            # Re-check stock after acquiring the lock — another request may
            # have deducted stock between validate_items() and here.
            if size.stock < quantity:
                raise serializers.ValidationError(
                    f'Insufficient stock for {sneaker.name} size {size.size}.'
                )

            price = sneaker.discounted_price or sneaker.price

            OrderItem.objects.create(
                order=order,
                sneaker=sneaker,
                size=size,
                quantity=quantity,
                unit_price=price
            )

            # Deduct stock
            size.stock -= quantity
            size.save()

            # Increment popularity
            sneaker.popularity_score += quantity
            sneaker.save(update_fields=['popularity_score'])

            total += price * quantity

        order.total_price = total
        order.save(update_fields=['total_price'])

        # Auto-create invoice
        import uuid
        Invoice.objects.create(
            order=order,
            invoice_number=f'INV-{uuid.uuid4().hex[:8].upper()}'
        )

        # Auto-create delivery record
        Delivery.objects.create(
            order=order,
            status='processing',
            delivery_address=order.delivery_address
        )

        return order


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    invoice_number = serializers.SerializerMethodField()
    delivery_id = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    delivery_status_label = serializers.SerializerMethodField()
    delivery_is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_email', 'status',
            'total_price', 'delivery_address', 'credit_card_last4',
            'invoice_number', 'delivery_id', 'delivery_status',
            'delivery_status_label', 'delivery_is_completed',
            'items', 'refund_requested_at', 'refund_approved_at', 'refund_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'total_price', 'created_at', 'updated_at']

    def get_invoice_number(self, obj):
        try:
            return obj.invoice.invoice_number
        except ObjectDoesNotExist:
            return None

    def get_delivery_id(self, obj):
        try:
            return obj.delivery.id
        except ObjectDoesNotExist:
            return None

    def get_delivery_is_completed(self, obj):
        try:
            return bool(obj.delivery.is_completed)
        except ObjectDoesNotExist:
            return None

    def get_delivery_status(self, obj):
        try:
            return obj.delivery.status
        except ObjectDoesNotExist:
            return None

    def get_delivery_status_label(self, obj):
        try:
            return obj.delivery.get_status_display()
        except ObjectDoesNotExist:
            return None


class DeliveryOrderItemSerializer(serializers.ModelSerializer):
    sneaker_name = serializers.CharField(source='sneaker.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'sneaker', 'sneaker_name', 'quantity']


class DeliveryOrderSerializer(serializers.ModelSerializer):
    items = DeliveryOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'total_price', 'items']


class InvoiceSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'order', 'issued_at', 'notes']


class DeliverySerializer(serializers.ModelSerializer):
    order = DeliveryOrderSerializer(read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id', 'order', 'order_id', 'status', 'tracking_number',
            'delivery_address', 'is_completed',
            'dispatched_at', 'delivered_at', 'notes'
        ]
