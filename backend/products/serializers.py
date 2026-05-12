from django.conf import settings
from rest_framework import serializers
from .models import Brand, Category, Sneaker, SneakerSize, SneakerImage, Wishlist, Review


def build_media_url(request, file_field):
    if not file_field:
        return None
    if isinstance(file_field, str):
        if file_field.startswith(('http://', 'https://')):
            return file_field
        if request is None:
            return file_field
        media_url = settings.MEDIA_URL
        if not media_url.endswith('/'):
            media_url = f'{media_url}/'
        return request.build_absolute_uri(f'{media_url}{file_field.lstrip("/")}')
    name = getattr(file_field, 'name', '')
    if isinstance(name, str) and name.startswith(('http://', 'https://')):
        return name
    url = file_field.url
    if request is None:
        return url
    return request.build_absolute_uri(url)


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'description', 'logo_url']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']


class SneakerSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SneakerSize
        fields = ['id', 'size', 'size_system', 'stock']


class SneakerSizeStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = SneakerSize
        fields = ['id', 'stock']
        read_only_fields = ['id']


class SneakerSizeCreateSerializer(serializers.ModelSerializer):
    sneaker_id = serializers.PrimaryKeyRelatedField(
        queryset=Sneaker.objects.all(),
        source='sneaker',
        write_only=True,
    )

    class Meta:
        model = SneakerSize
        fields = ['id', 'sneaker_id', 'size', 'size_system', 'stock']
        read_only_fields = ['id']


class SneakerPriceUpdateSerializer(serializers.Serializer):
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                {'detail': 'At least one of price or discount_percentage must be provided.'}
            )
        return attrs


class SneakerBatchDiscountSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
    )

    def validate_product_ids(self, value):
        seen = set()
        unique_ids = []
        for product_id in value:
            if product_id in seen:
                continue
            seen.add(product_id)
            unique_ids.append(product_id)
        return unique_ids


class SneakerImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = SneakerImage
        fields = ['id', 'image_url', 'alt_text', 'is_primary', 'order']

    def get_image_url(self, obj):
        request = self.context.get('request')
        return build_media_url(request, obj.image)


class SneakerImageManageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    sneaker_id = serializers.IntegerField(source='sneaker.id', read_only=True)

    class Meta:
        model = SneakerImage
        fields = ['id', 'sneaker_id', 'image', 'image_url', 'alt_text', 'is_primary', 'order']
        read_only_fields = ['id', 'sneaker_id', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        return build_media_url(request, obj.image)


class SneakerListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    Includes only what the product listing page needs.
    """
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand_id = serializers.IntegerField(source='brand.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    primary_image = serializers.SerializerMethodField()
    discounted_price = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    total_stock = serializers.ReadOnlyField()
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    rating_count = serializers.IntegerField(read_only=True)
    latest_approved_comment = serializers.CharField(
        read_only=True, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Sneaker
        fields = [
            'id', 'name', 'description', 'colorway', 'model_number',
            'brand_id', 'brand_name',
            'category_id', 'category_name',
            'sku', 'price', 'original_price', 'cost_price',
            'discounted_price', 'discount_percentage',
            'is_in_stock', 'total_stock', 'is_featured', 'primary_image',
            'is_active', 'popularity_score', 'average_rating', 'rating_count',
            'latest_approved_comment', 'created_at'
        ]

    def get_primary_image(self, obj):
        annotated_image = getattr(obj, 'primary_image', None)
        if annotated_image:
            request = self.context.get('request')
            return build_media_url(request, annotated_image)

        prefetched_images = getattr(obj, 'prefetched_images', None)
        if prefetched_images is not None:
            img = next((image for image in prefetched_images if image.is_primary), None)
            if not img and prefetched_images:
                img = prefetched_images[0]
            request = self.context.get('request')
            return build_media_url(request, img.image if img else None)

        img = obj.images.filter(is_primary=True).first()
        if not img:
            img = obj.images.first()
        request = self.context.get('request')
        return build_media_url(request, img.image if img else None)


class SneakerDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for the product detail page.
    """
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True,
        required=False, allow_null=True
    )
    sizes = SneakerSizeSerializer(many=True, read_only=True)
    images = SneakerImageSerializer(many=True, read_only=True)
    discounted_price = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    total_stock = serializers.ReadOnlyField()
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    review_count = serializers.IntegerField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sneaker
        fields = [
            'id', 'name', 'colorway', 'model_number', 'sku', 'serial_number',
            'description', 'brand', 'brand_id', 'category', 'category_id',
            'price', 'original_price', 'cost_price', 'discount_percentage',
            'discounted_price', 'sizes', 'images',
            'warranty_status', 'distributor_information',
            'is_active', 'is_featured', 'is_in_stock', 'total_stock',
            'popularity_score', 'view_count',
            'average_rating', 'review_count', 'rating_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'view_count', 'popularity_score', 'created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    sneaker_name = serializers.CharField(source='sneaker.name', read_only=True)
    customer_name = serializers.SerializerMethodField()
    comment = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Review
        fields = [
            'id', 'sneaker', 'sneaker_name', 'customer', 'customer_name',
            'rating', 'comment', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'sneaker', 'customer', 'status', 'created_at']
        validators = []

    def get_customer_name(self, obj):
        return f'{obj.customer.first_name} {obj.customer.last_name}'


class WishlistSerializer(serializers.ModelSerializer):
    sneaker = SneakerListSerializer(read_only=True)
    sneaker_id = serializers.PrimaryKeyRelatedField(
        queryset=Sneaker.objects.all(), source='sneaker', write_only=True
    )

    class Meta:
        model = Wishlist
        fields = ['id', 'sneaker', 'sneaker_id', 'added_at']
        read_only_fields = ['id', 'added_at']
