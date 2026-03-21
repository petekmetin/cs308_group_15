from rest_framework import serializers
from .models import Brand, Category, Sneaker, SneakerSize, SneakerImage, Wishlist, Review


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


class SneakerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SneakerImage
        fields = ['id', 'image_url', 'alt_text', 'is_primary', 'order']


class SneakerListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    Includes only what the product listing page needs.
    """
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    discounted_price = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    total_stock = serializers.ReadOnlyField()

    class Meta:
        model = Sneaker
        fields = [
            'id', 'name', 'colorway', 'brand_name', 'category_name',
            'sku', 'price', 'discounted_price', 'discount_percentage',
            'is_in_stock', 'total_stock', 'is_featured', 'primary_image',
            'popularity_score', 'created_at'
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first()
        if not img:
            img = obj.images.first()
        return img.image_url if img else None


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
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

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
            'average_rating', 'review_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'view_count', 'popularity_score', 'created_at', 'updated_at']

    def get_average_rating(self, obj):
        approved = obj.reviews.filter(status='approved')
        if not approved.exists():
            return None
        total = sum(r.rating for r in approved)
        return round(total / approved.count(), 1)

    def get_review_count(self, obj):
        return obj.reviews.filter(status='approved').count()


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'sneaker', 'customer', 'customer_name',
            'rating', 'comment', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'customer', 'status', 'created_at']

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