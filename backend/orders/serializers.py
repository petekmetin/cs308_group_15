from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from accounts.validators import get_customer_profile_errors
from .models import Order, OrderItem, Invoice, ReturnRequest, ReturnRequestItem
from products.serializers import SneakerListSerializer, build_media_url
from products.models import Sneaker, SneakerSize


class OrderItemSerializer(serializers.ModelSerializer):
    sneaker_detail = SneakerListSerializer(source='sneaker', read_only=True)
    subtotal = serializers.ReadOnlyField()
    size_value = serializers.CharField(source='size.size', read_only=True)
    size_system = serializers.CharField(source='size.size_system', read_only=True)
    returnable_quantity = serializers.SerializerMethodField()

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
            'returnable_quantity',
        ]
        read_only_fields = ['unit_price']

    def get_returnable_quantity(self, obj):
        returned = 0
        for request_item in getattr(obj, 'prefetched_return_request_items', []):
            if request_item.return_request.status in {'requested', 'received', 'approved'}:
                returned += request_item.quantity
        if not hasattr(obj, 'prefetched_return_request_items'):
            returned = sum(
                item.quantity
                for item in obj.return_request_items.select_related('return_request').filter(
                    return_request__status__in=['requested', 'received', 'approved']
                )
            )
        return max(int(obj.quantity or 0) - int(returned or 0), 0)


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

        return order


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    invoice_number = serializers.SerializerMethodField()
    delivery_id = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    delivery_status_label = serializers.SerializerMethodField()
    delivery_is_completed = serializers.BooleanField(source='is_completed', read_only=True)
    delivered_at = serializers.DateTimeField(read_only=True)
    return_requests = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_email', 'status',
            'total_price', 'delivery_address', 'credit_card_last4',
            'invoice_number', 'delivery_id', 'delivery_status',
            'delivery_status_label', 'delivery_is_completed',
            'items', 'refund_requested_at', 'refund_approved_at', 'refund_amount',
            'tracking_number', 'dispatched_at', 'delivered_at', 'delivery_notes',
            'return_requests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'total_price', 'created_at', 'updated_at']

    def get_invoice_number(self, obj):
        try:
            return obj.invoice.invoice_number
        except ObjectDoesNotExist:
            return None

    def get_delivery_id(self, obj):
        return obj.id

    def get_delivery_status(self, obj):
        return obj.status

    def get_delivery_status_label(self, obj):
        return obj.get_status_display()

    def get_return_requests(self, obj):
        requests = getattr(obj, 'prefetched_return_requests', None)
        if requests is None:
            requests = obj.return_requests.prefetch_related('items').all()[:10]
        return ReturnRequestSummarySerializer(requests, many=True).data


class DeliveryOrderItemSerializer(serializers.ModelSerializer):
    sneaker_name = serializers.CharField(source='sneaker.name', read_only=True)
    sneaker_brand = serializers.CharField(source='sneaker.brand.name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'sneaker', 'sneaker_name', 'sneaker_brand', 'primary_image', 'quantity']

    def get_primary_image(self, obj):
        images = getattr(obj.sneaker, 'prefetched_images', None)
        if images is not None:
            image = images[0] if images else None
            return build_media_url(self.context.get('request'), image.image if image else None)
        image = obj.sneaker.images.order_by('-is_primary', 'order', 'id').first()
        return build_media_url(self.context.get('request'), image.image if image else None)


class DeliveryOrderSerializer(serializers.ModelSerializer):
    items = DeliveryOrderItemSerializer(many=True, read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'status', 'total_price', 'invoice_number', 'items', 'created_at']


class InvoiceSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'order', 'issued_at', 'pdf_path', 'notes']


class InvoiceListOrderSerializer(serializers.ModelSerializer):
    customer_email = serializers.CharField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_email', 'status',
            'total_price', 'delivery_address', 'credit_card_last4',
            'created_at', 'updated_at',
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    order = InvoiceListOrderSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'order', 'issued_at', 'pdf_path', 'notes']


class DeliverySerializer(serializers.ModelSerializer):
    order = DeliveryOrderSerializer(source='*', read_only=True)
    order_id = serializers.IntegerField(source='id', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    notes = serializers.CharField(source='delivery_notes', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order', 'order_id', 'status', 'tracking_number',
            'delivery_address', 'is_completed',
            'dispatched_at', 'delivered_at', 'notes', 'invoice_number'
        ]


class ReturnRequestItemSerializer(serializers.ModelSerializer):
    order_item_id = serializers.IntegerField(source='order_item.id', read_only=True)
    sneaker = serializers.IntegerField(source='order_item.sneaker_id', read_only=True)
    sneaker_name = serializers.CharField(source='order_item.sneaker.name', read_only=True)
    sneaker_brand = serializers.CharField(source='order_item.sneaker.brand.name', read_only=True)
    size_value = serializers.CharField(source='order_item.size.size', read_only=True)
    size_system = serializers.CharField(source='order_item.size.size_system', read_only=True)

    class Meta:
        model = ReturnRequestItem
        fields = [
            'id',
            'order_item_id',
            'sneaker',
            'sneaker_name',
            'sneaker_brand',
            'size_value',
            'size_system',
            'quantity',
            'unit_refund_amount',
            'subtotal_refund_amount',
        ]


class ReturnRequestSummarySerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequest
        fields = [
            'id',
            'status',
            'requested_at',
            'received_at',
            'approved_at',
            'rejected_at',
            'total_refund_amount',
            'manager_note',
            'items_count',
        ]

    def get_items_count(self, obj):
        items = getattr(obj, 'items', None)
        if hasattr(items, 'all'):
            return sum(item.quantity for item in items.all())
        return obj.items.count()


class ReturnRequestSerializer(serializers.ModelSerializer):
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_total = serializers.DecimalField(source='order.total_price', max_digits=10, decimal_places=2, read_only=True)
    items = ReturnRequestItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReturnRequest
        fields = [
            'id',
            'order',
            'customer',
            'customer_email',
            'order_status',
            'order_total',
            'status',
            'requested_at',
            'received_at',
            'approved_at',
            'rejected_at',
            'total_refund_amount',
            'manager_note',
            'items',
        ]
