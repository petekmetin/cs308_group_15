from rest_framework import serializers

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = [
            'id',
            'product_slug',
            'product_name',
            'brand',
            'description',
            'accent',
            'image_url',
            'unit_price',
            'quantity',
        ]
        read_only_fields = ['id']


class AddCartItemSerializer(serializers.Serializer):
    product_slug = serializers.SlugField(max_length=120)
    product_name = serializers.CharField(max_length=255)
    brand = serializers.CharField(max_length=120)
    description = serializers.CharField(allow_blank=True, required=False)
    accent = serializers.CharField(max_length=120, allow_blank=True, required=False)
    image_url = serializers.CharField(max_length=255, allow_blank=True, required=False)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'item_count', 'total']

    def get_item_count(self, cart):
        return sum(item.quantity for item in cart.items.all())

    def get_total(self, cart):
        total = sum(item.quantity * item.unit_price for item in cart.items.all())
        return f"{total:.2f}"

