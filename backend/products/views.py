import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import generics, filters, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q, ExpressionWrapper, F, DecimalField
from django.db.models.functions import Coalesce

from .models import Brand, Category, Sneaker, SneakerImage, SneakerSize, Wishlist, Review
from .querysets import sneaker_detail_queryset, sneaker_summary_queryset
from .serializers import (
    BrandSerializer, CategorySerializer,
    SneakerListSerializer, SneakerDetailSerializer,
    WishlistSerializer, ReviewSerializer, SneakerSizeStockSerializer,
    SneakerImageManageSerializer, SneakerPriceUpdateSerializer,
    SneakerBatchDiscountSerializer, SneakerSizeCreateSerializer,
)
from config.permissions import IsProductManager, IsSalesManager, IsCustomer


logger = logging.getLogger(__name__)
PRICING_FIELDS = {'price', 'original_price', 'cost_price', 'discount_percentage'}


def send_discount_email(customer_email, sneaker):
    subject = f'Discount on {sneaker.name}'
    body = (
        f'Good news from SoleVault.\n\n'
        f'{sneaker.brand.name} {sneaker.name} now has a '
        f'{sneaker.discount_percentage}% discount. '
        f'The new price is ${sneaker.discounted_price}.\n\n'
        f'SoleVault'
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [customer_email],
        fail_silently=False,
    )


def notify_discount_watchers(sneaker):
    if not sneaker.discount_percentage or sneaker.discount_percentage <= 0:
        return {'notification_count': 0, 'failed_notification_count': 0}

    wishlist_items = (
        Wishlist.objects.filter(sneaker=sneaker)
        .select_related('customer')
        .exclude(customer__email='')
    )
    notified = 0
    failed = 0
    for item in wishlist_items:
        try:
            send_discount_email(item.customer.email, sneaker)
            notified += 1
        except Exception:
            failed += 1
            logger.exception(
                'Discount notification failed for sneaker %s and customer %s',
                sneaker.id,
                item.customer_id,
            )

    return {'notification_count': notified, 'failed_notification_count': failed}


def ensure_primary_image(sneaker, preferred_image_id=None):
    """
    Enforce "at most one primary" and keep one primary when images exist.
    """
    images = sneaker.images.order_by('order', 'id')
    if not images.exists():
        return

    if preferred_image_id is not None:
        images.exclude(id=preferred_image_id).update(is_primary=False)
        images.filter(id=preferred_image_id).update(is_primary=True)
        return

    current_primary = images.filter(is_primary=True).first()
    if current_primary:
        images.exclude(id=current_primary.id).update(is_primary=False)
        return

    first_image = images.first()
    images.exclude(id=first_image.id).update(is_primary=False)
    images.filter(id=first_image.id).update(is_primary=True)


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
    # DRF SearchFilter defaults to case-insensitive substring (__icontains).
    # Including brand__name and category__name means typing "n" matches Nike,
    # "a" matches Adidas, "run" matches Running category, etc.
    search_fields = ['name', 'description', 'sku', 'model_number', 'brand__name', 'category__name']
    ordering_fields = ['effective_price', 'popularity_score']
    ordering = ['-popularity_score']

    def get_queryset(self):
        qs = sneaker_summary_queryset(Sneaker.objects.select_related('brand', 'category'))
        qs = qs.annotate(
            effective_price=ExpressionWrapper(
                F('price') * (1 - Coalesce(F('discount_percentage'), 0) / 100.0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )

        include_inactive = self.request.query_params.get('include_inactive') == 'true'
        user = self.request.user
        if not (
            include_inactive
            and getattr(user, 'is_authenticated', False)
            and getattr(user, 'role', None) in {'product_manager', 'sales_manager'}
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
    queryset = sneaker_detail_queryset(
        Sneaker.objects.select_related('brand', 'category').prefetch_related(
            'sizes', 'images'
        )
    )

    def get_serializer_class(self):
        return SneakerDetailSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsProductManager()]

    def update(self, request, *args, **kwargs):
        incoming_fields = set(request.data.keys())
        blocked_fields = sorted(PRICING_FIELDS.intersection(incoming_fields))
        if blocked_fields:
            return Response(
                {
                    'detail': (
                        'Product managers cannot update pricing fields. '
                        f'Blocked: {", ".join(blocked_fields)}.'
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

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


class SneakerSizeCreateView(generics.CreateAPIView):
    queryset = SneakerSize.objects.select_related('sneaker')
    serializer_class = SneakerSizeCreateSerializer
    permission_classes = [IsProductManager]


class SneakerImageCreateView(generics.CreateAPIView):
    queryset = SneakerImage.objects.select_related('sneaker')
    serializer_class = SneakerImageManageSerializer
    permission_classes = [IsProductManager]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        try:
            sneaker = Sneaker.objects.get(pk=self.kwargs['pk'])
        except Sneaker.DoesNotExist:
            raise serializers.ValidationError({'detail': 'Sneaker not found.'})

        with transaction.atomic():
            image = serializer.save(sneaker=sneaker)
            preferred_id = image.id if image.is_primary else None
            ensure_primary_image(sneaker, preferred_id)


class SneakerImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SneakerImage.objects.select_related('sneaker')
    serializer_class = SneakerImageManageSerializer
    permission_classes = [IsProductManager]
    http_method_names = ['patch', 'delete']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_update(self, serializer):
        with transaction.atomic():
            image = serializer.save()
            preferred_id = image.id if image.is_primary else None
            ensure_primary_image(image.sneaker, preferred_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        sneaker = instance.sneaker
        with transaction.atomic():
            instance.delete()
            ensure_primary_image(sneaker)
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    notification_summary = {'notification_count': 0, 'failed_notification_count': 0}
    if 'discount_percentage' in validated and sneaker.discount_percentage > 0:
        notification_summary = notify_discount_watchers(sneaker)

    response_data = SneakerDetailSerializer(sneaker, context={'request': request}).data
    response_data.update(notification_summary)
    return Response(response_data)


@api_view(['PATCH'])
@permission_classes([IsSalesManager])
def batch_discount_sneakers(request):
    """
    PATCH /api/products/sneakers/batch-discount/
    Body: { product_ids: [1, 2], discount_percentage: "15.00" }
    Sales managers only.
    """
    serializer = SneakerBatchDiscountSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    product_ids = serializer.validated_data['product_ids']
    discount_percentage = serializer.validated_data['discount_percentage']
    sneakers = list(
        Sneaker.objects.filter(id__in=product_ids)
        .select_related('brand', 'category')
        .prefetch_related('sizes', 'images')
    )

    found_ids = {sneaker.id for sneaker in sneakers}
    missing_ids = [product_id for product_id in product_ids if product_id not in found_ids]
    if missing_ids:
        return Response(
            {'product_ids': [f'Unknown product id(s): {", ".join(map(str, missing_ids))}.']},
            status=400,
        )

    for sneaker in sneakers:
        sneaker.discount_percentage = discount_percentage
        sneaker.save(update_fields=['discount_percentage'])

    notification_count = 0
    failed_notification_count = 0
    if discount_percentage > 0:
        for sneaker in sneakers:
            summary = notify_discount_watchers(sneaker)
            notification_count += summary['notification_count']
            failed_notification_count += summary['failed_notification_count']

    return Response({
        'updated_count': len(sneakers),
        'notification_count': notification_count,
        'failed_notification_count': failed_notification_count,
        'products': SneakerListSerializer(
            sneakers,
            many=True,
            context={'request': request},
        ).data,
    })


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
            .exclude(comment='')
            .select_related('customer')
            .order_by('-created_at')
        )


class ReviewCreateView(generics.CreateAPIView):
    """
    POST /api/products/sneakers/<pk>/reviews/create/
    Customers only. Reviews are created as pending and require
    product-manager moderation before they become public.
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomer]

    def create(self, request, *args, **kwargs):
        try:
            sneaker = Sneaker.objects.get(pk=self.kwargs['pk'])
        except Sneaker.DoesNotExist:
            return Response({'detail': 'Sneaker not found.'}, status=404)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating = serializer.validated_data['rating']
        comment = serializer.validated_data.get('comment', '').strip()

        review, created = Review.objects.get_or_create(
            sneaker=sneaker,
            customer=request.user,
            defaults={
                'rating': rating,
                'comment': comment,
                'status': 'pending' if comment else 'approved',
            },
        )

        if not created:
            review.rating = rating
            update_fields = ['rating', 'updated_at']
            if comment:
                review.comment = comment
                review.status = 'pending'
                update_fields.extend(['comment', 'status'])
            elif not review.comment:
                review.status = 'approved'
                update_fields.append('status')
            review.save(update_fields=update_fields)

        response_serializer = self.get_serializer(review)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


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


class ReviewManagementListView(generics.ListAPIView):
    """
    GET /api/products/reviews/
    Product managers can list all reviews, optionally filtered by status.
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsProductManager]

    def get_queryset(self):
        queryset = Review.objects.select_related('customer', 'sneaker').order_by('-created_at')
        status_filter = (self.request.query_params.get('status') or '').strip().lower()
        if status_filter:
            if status_filter not in {'pending', 'approved', 'rejected'}:
                return Review.objects.none()
            queryset = queryset.filter(status=status_filter)
        return queryset


class ReviewDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/products/reviews/<pk>/
    Product managers can hard-delete any review.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsProductManager]
    http_method_names = ['delete']


@api_view(['DELETE'])
@permission_classes([IsProductManager])
def clear_rejected_reviews(request):
    """
    DELETE /api/products/reviews/rejected/clear/
    Removes all rejected reviews and returns deleted count.
    """
    deleted_count, _ = Review.objects.filter(status='rejected').delete()
    return Response({'deleted_count': deleted_count})


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
    if new_status not in ('pending', 'approved', 'rejected'):
        return Response({'detail': 'Status must be pending, approved, or rejected.'}, status=400)

    review.status = new_status
    review.save(update_fields=['status'])
    return Response(ReviewSerializer(review).data)
