from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)
from products.models import Sneaker


def build_media_url(request, file_field):
    if not file_field:
        return ''
    name = getattr(file_field, 'name', '')
    if isinstance(name, str) and name.startswith(('http://', 'https://')):
        return name
    return request.build_absolute_uri(file_field.url)


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_detail(request):
    cart = get_user_cart(request.user)
    return Response(CartSerializer(cart).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_cart_item(request):
    serializer = AddCartItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    cart = get_user_cart(request.user)
    data = serializer.validated_data
    quantity = data.get('quantity', 1)
    product_id = data['product_id']

    product_name = data['product_name']
    brand = data['brand']
    description = data.get('description', '')
    accent = data.get('accent', '')
    image_url = data.get('image_url', '')
    unit_price = Decimal(data['unit_price'])

    try:
        sneaker = (
            Sneaker.objects.select_related('brand')
            .prefetch_related('sizes', 'images')
            .get(pk=product_id, is_active=True)
        )
    except Sneaker.DoesNotExist:
        return Response(
            {'detail': 'Product not found.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not sneaker.is_in_stock:
        return Response(
            {'detail': 'This product is out of stock.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if sneaker.price is None:
        return Response(
            {'detail': 'This product is not available for purchase yet.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    primary_image = sneaker.images.filter(is_primary=True).first() or sneaker.images.first()
    effective_price = sneaker.discounted_price if sneaker.discounted_price is not None else sneaker.price

    product_slug = f'sneaker-{sneaker.id}'
    product_name = sneaker.name
    brand = sneaker.brand.name
    description = sneaker.description or description
    image_url = build_media_url(request, primary_image.image) if primary_image else image_url
    unit_price = Decimal(str(effective_price))

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product_slug=product_slug,
        defaults={
            'product_name': product_name,
            'brand': brand,
            'description': description,
            'accent': accent,
            'image_url': image_url,
            'unit_price': unit_price,
            'quantity': quantity,
        },
    )

    if not created:
        item.quantity += quantity
        item.product_name = product_name
        item.brand = brand
        item.description = description
        item.accent = accent
        item.image_url = image_url
        item.unit_price = unit_price
        item.save()

    cart.refresh_from_db()
    return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    serializer = UpdateCartItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    cart = get_user_cart(request.user)
    try:
        item = cart.items.get(id=item_id)
    except CartItem.DoesNotExist:
        return Response({'detail': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

    item.quantity = serializer.validated_data['quantity']
    item.save(update_fields=['quantity', 'updated_at'])
    cart.refresh_from_db()
    return Response(CartSerializer(cart).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cart_item(request, item_id):
    cart = get_user_cart(request.user)
    try:
        item = cart.items.get(id=item_id)
    except CartItem.DoesNotExist:
        return Response({'detail': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

    item.delete()
    cart.refresh_from_db()
    return Response(CartSerializer(cart).data)
