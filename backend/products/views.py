from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q

from .models import Brand, Category, Sneaker, SneakerSize, Wishlist, Review
from .serializers import (
    BrandSerializer, CategorySerializer,
    SneakerListSerializer, SneakerDetailSerializer,
    WishlistSerializer, ReviewSerializer, SneakerSizeStockSerializer,
    SneakerPriceUpdateSerializer,
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
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'popularity_score']
    ordering = ['-popularity_score']

    def get_queryset(self):
        qs = Sneaker.objects.select_related('brand', 'category')

        include_inactive = self.request.query_params.get('include_inactive') == 'true'
        user = self.request.user
        if not (
            include_inactive
            and getattr(user, 'is_authenticated', False)
            and getattr(user, 'role', None) == 'product_manager'
        ):
            qs = qs.filter(is_active=True)

        brand_ids = self.request.query_params.getlist('brand')
        category_ids = self.request.query_params.getlist('category')
        size_filters = self.request.query_params.getlist('size')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        featured = self.request.query_params.get('featured')

        if brand_ids:
            qs = qs.filter(brand_id__in=brand_ids)
        if category_ids:
            qs = qs.filter(category_id__in=category_ids)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if featured == 'true':
            qs = qs.filter(is_featured=True)
        if size_filters:
            size_query = Q()
            for raw_size in size_filters:
                if ':' not in raw_size:
                    continue
                size_system, size_value = raw_size.split(':', 1)
                size_system = size_system.strip().upper()
                size_value = size_value.strip()
                if not size_system or not size_value:
                    continue
                size_query |= Q(
                    sizes__size_system=size_system,
                    sizes__size=size_value,
                )
            if size_query:
                qs = qs.filter(size_query)

        return qs.distinct()


class SneakerSizeOptionsView(generics.GenericAPIView):
    """
    GET /api/products/sizes/options/
    Returns distinct size options for active sneakers.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        size_options = (
            SneakerSize.objects.filter(sneaker__is_active=True)
            .values('size_system', 'size')
            .distinct()
            .order_by('size_system', 'size')
        )
        return Response(list(size_options))


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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_active:
            return Response(status=status.HTTP_204_NO_CONTENT)
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SneakerCreateView(generics.CreateAPIView):
    """
    POST /api/products/sneakers/create/
    Product managers only.
    """
    queryset = Sneaker.objects.all()
    serializer_class = SneakerDetailSerializer
    permission_classes = [IsProductManager]


# Updates stock for a single sneaker-size row.
class SneakerSizeStockUpdateView(generics.UpdateAPIView):
    queryset = SneakerSize.objects.select_related('sneaker')
    serializer_class = SneakerSizeStockSerializer
    permission_classes = [IsProductManager]
    http_method_names = ['patch']


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

    serializer = SneakerPriceUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    validated = serializer.validated_data
    update_fields = []

    if 'price' in validated:
        sneaker.price = validated['price']
        update_fields.append('price')
    if 'discount_percentage' in validated:
        sneaker.discount_percentage = validated['discount_percentage']
        update_fields.append('discount_percentage')

    if update_fields:
        sneaker.save(update_fields=update_fields)

    # Notify wishlist customers about discount if discount > 0
    if sneaker.discount_percentage > 0:
        # In production: send email or push notification here
        pass

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
        return (
            Review.objects.filter(
                sneaker_id=self.kwargs['pk'],
                status='approved'
            )
            .select_related('customer')
            .order_by('-created_at')
        )


class ReviewCreateView(generics.CreateAPIView):
    """
    POST /api/products/sneakers/<pk>/reviews/create/
    Customers only.
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomer]

    def perform_create(self, serializer):
        sneaker = Sneaker.objects.get(pk=self.kwargs['pk'])
        serializer.save(customer=self.request.user, sneaker=sneaker)


# Lists all pending reviews for product manager moderation.
class PendingReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsProductManager]

    def get_queryset(self):
        return (
            Review.objects.filter(status='pending')
            .select_related('customer', 'sneaker')
            .order_by('-created_at')
        )


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
