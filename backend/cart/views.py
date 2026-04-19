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

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product_slug=data['product_slug'],
        defaults={
            'product_name': data['product_name'],
            'brand': data['brand'],
            'description': data.get('description', ''),
            'accent': data.get('accent', ''),
            'image_url': data.get('image_url', ''),
            'unit_price': Decimal(data['unit_price']),
            'quantity': data.get('quantity', 1),
        },
    )

    if not created:
        item.quantity += data.get('quantity', 1)
        item.product_name = data['product_name']
        item.brand = data['brand']
        item.description = data.get('description', '')
        item.accent = data.get('accent', '')
        item.image_url = data.get('image_url', '')
        item.unit_price = Decimal(data['unit_price'])
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

