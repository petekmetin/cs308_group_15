from decimal import Decimal

from django.db.models import Prefetch
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
from products.models import Sneaker, SneakerSize
from products.querysets import sneaker_summary_queryset


def build_media_url(request, file_field):
    if not file_field:
        return ''
    if isinstance(file_field, str):
        if file_field.startswith(('http://', 'https://')):
            return file_field
        return request.build_absolute_uri(f'/media/{file_field.lstrip("/")}')
    name = getattr(file_field, 'name', '')
    if isinstance(name, str) and name.startswith(('http://', 'https://')):
        return name
    return request.build_absolute_uri(file_field.url)


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def get_user_cart_with_items(user):
    cart_items = CartItem.objects.select_related('size').order_by('created_at', 'id')
    cart = (
        Cart.objects.filter(user=user)
        .prefetch_related(Prefetch('items', queryset=cart_items))
        .first()
    )
    if cart is not None:
        return cart

    cart = get_user_cart(user)
    return Cart.objects.prefetch_related(Prefetch('items', queryset=cart_items)).get(pk=cart.pk)


def get_active_sneaker(product_id):
    return (
        sneaker_summary_queryset(Sneaker.objects.select_related('brand'))
        .get(pk=product_id, is_active=True)
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_detail(request):
    cart = get_user_cart_with_items(request.user)
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
    size_id = data['size_id']

    product_name = data['product_name']
    brand = data['brand']
    description = data.get('description', '')
    accent = data.get('accent', '')
    image_url = data.get('image_url', '')
    unit_price = Decimal(data['unit_price'])

    try:
        sneaker = get_active_sneaker(product_id)
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

    try:
        size = SneakerSize.objects.get(pk=size_id)
    except SneakerSize.DoesNotExist:
        return Response(
            {'detail': 'Selected size was not found.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if size.sneaker_id != sneaker.id:
        return Response(
            {'detail': 'Selected size does not belong to this product.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if size.stock <= 0:
        return Response(
            {'detail': 'Selected size is out of stock.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if quantity > size.stock:
        return Response(
            {'detail': f'Only {size.stock} left for size {size.size_system} {size.size}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    primary_image = getattr(sneaker, 'primary_image', None)
    effective_price = sneaker.discounted_price if sneaker.discounted_price is not None else sneaker.price

    product_slug = f'sneaker-{sneaker.id}'
    product_name = sneaker.name
    brand = sneaker.brand.name
    description = sneaker.description or description
    image_url = build_media_url(request, primary_image) if primary_image else image_url
    unit_price = Decimal(str(effective_price))

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        sneaker=sneaker,
        size=size,
        defaults={
            'product_slug': product_slug,
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
        next_quantity = item.quantity + quantity
        if next_quantity > size.stock:
            return Response(
                {'detail': f'Only {size.stock} left for size {size.size_system} {size.size}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.quantity = next_quantity
        item.product_slug = product_slug
        item.product_name = product_name
        item.brand = brand
        item.description = description
        item.accent = accent
        item.image_url = image_url
        item.unit_price = unit_price
        item.sneaker = sneaker
        item.size = size
        item.save()

    cart = get_user_cart_with_items(request.user)
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

    new_quantity = serializer.validated_data['quantity']
    stock = item.size.stock if item.size else 0
    if new_quantity > stock:
        if item.size:
            detail = f'Only {stock} left for size {item.size.size_system} {item.size.size}.'
        else:
            detail = 'This cart item no longer has a valid size selection.'
        return Response(
            {'detail': detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    item.quantity = new_quantity
    item.save(update_fields=['quantity', 'updated_at'])
    cart = get_user_cart_with_items(request.user)
    return Response(CartSerializer(cart).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    cart = get_user_cart(request.user)
    cart.items.all().delete()
    return Response({'detail': 'Cart cleared.'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cart_item(request, item_id):
    cart = get_user_cart(request.user)
    try:
        item = cart.items.get(id=item_id)
    except CartItem.DoesNotExist:
        return Response({'detail': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

    item.delete()
    cart = get_user_cart_with_items(request.user)
    return Response(CartSerializer(cart).data)
