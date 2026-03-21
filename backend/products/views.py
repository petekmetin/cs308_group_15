from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from django.db.models import Q

from .models import Brand, Category, Sneaker, Wishlist, Review
from .serializers import (
    BrandSerializer, CategorySerializer,
    SneakerListSerializer, SneakerDetailSerializer,
    WishlistSerializer, ReviewSerializer,
)
from config.permissions import IsProductManager, IsSalesManager, IsCustomer


# ─── Brands ───────────────────────────────────────────────────────────────────

class BrandListCreateView(generics.ListCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsProductManager()]
        return [AllowAny()]


class BrandDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsProductManager()]


# ─── Categories ───────────────────────────────────────────────────────────────

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsProductManager()]
        return [AllowAny()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsProductManager()]


# ─── Sneakers ─────────────────────────────────────────────────────────────────

class SneakerListView(generics.ListAPIView):
    """
    GET /api/products/sneakers/
    Supports: ?search=air force, ?brand=1, ?category=2, ?min_price=50, ?max_price=200
    """
    serializer_class = SneakerListSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'colorway', 'sku', 'brand__name', 'description']
    ordering_fields = ['price', 'created_at', 'popularity_score', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Sneaker.objects.filter(is_active=True).select_related('brand', 'category')

        brand = self.request.query_params.get('brand')
        category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        in_stock = self.request.query_params.get('in_stock')
        featured = self.request.query_params.get('featured')

        if brand:
            qs = qs.filter(brand_id=brand)
        if category:
            qs = qs.filter(category_id=category)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if featured == 'true':
            qs = qs.filter(is_featured=True)

        return qs


class SneakerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/products/sneakers/<id>/    — anyone
    PATCH  /api/products/sneakers/<id>/   — product manager
    DELETE /api/products/sneakers/<id>/   — product manager
    """
    queryset = Sneaker.objects.select_related('brand', 'category').prefetch_related(
        'sizes', 'images', 'reviews'
    )

    def get_serializer_class(self):
        return SneakerDetailSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsProductManager()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view counter without triggering updated_at change
        Sneaker.objects.filter(pk=instance.pk).update(view_count=instance.view_count + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SneakerCreateView(generics.CreateAPIView):
    """
    POST /api/products/sneakers/create/
    Product managers only.
    """
    queryset = Sneaker.objects.all()
    serializer_class = SneakerDetailSerializer
    permission_classes = [IsProductManager]


@api_view(['PATCH'])
@permission_classes([IsSalesManager])
def set_sneaker_price(request, pk):
    """
    PATCH /api/products/sneakers/<pk>/set-price/
    Body: { price, discount_percentage }
    Sales managers only.
    """
    try:
        sneaker = Sneaker.objects.get(pk=pk)
    except Sneaker.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    price = request.data.get('price')
    discount = request.data.get('discount_percentage', sneaker.discount_percentage)

    if price is not None:
        sneaker.price = price
    sneaker.discount_percentage = discount
    sneaker.save(update_fields=['price', 'discount_percentage'])

    # Notify wishlist customers about discount if discount > 0
    if float(discount) > 0:
        wishlist_customers = Wishlist.objects.filter(
            sneaker=sneaker
        ).select_related('customer')
        # In production: send email or push notification here
        notified = [w.customer.email for w in wishlist_customers]

    return Response(SneakerDetailSerializer(sneaker).data)


# ─── Wishlist ─────────────────────────────────────────────────────────────────

class WishlistView(generics.ListCreateAPIView):
    """
    GET  /api/products/wishlist/   — customer's wishlist
    POST /api/products/wishlist/   — add a sneaker { sneaker_id: X }
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return Wishlist.objects.filter(customer=self.request.user).select_related('sneaker')

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def wishlist_remove(request, pk):
    """
    DELETE /api/products/wishlist/<sneaker_pk>/
    """
    try:
        item = Wishlist.objects.get(customer=request.user, sneaker_id=pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Wishlist.DoesNotExist:
        return Response({'detail': 'Not in wishlist.'}, status=404)


# ─── Reviews ──────────────────────────────────────────────────────────────────

class ReviewListView(generics.ListAPIView):
    """
    GET /api/products/sneakers/<pk>/reviews/
    Returns only approved reviews publicly.
    """
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Review.objects.filter(
            sneaker_id=self.kwargs['pk'],
            status='approved'
        ).select_related('customer')


class ReviewCreateView(generics.CreateAPIView):
    """
    POST /api/products/sneakers/<pk>/reviews/
    Customers only.
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomer]

    def perform_create(self, serializer):
        sneaker = Sneaker.objects.get(pk=self.kwargs['pk'])
        serializer.save(customer=self.request.user, sneaker=sneaker)


@api_view(['PATCH'])
@permission_classes([IsProductManager])
def moderate_review(request, pk):
    """
    PATCH /api/products/reviews/<pk>/moderate/
    Body: { status: "approved" | "rejected" }
    Product managers only.
    """
    try:
        review = Review.objects.get(pk=pk)
    except Review.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    new_status = request.data.get('status')
    if new_status not in ('approved', 'rejected'):
        return Response({'detail': 'Status must be approved or rejected.'}, status=400)

    review.status = new_status
    review.save(update_fields=['status'])
    return Response(ReviewSerializer(review).data)