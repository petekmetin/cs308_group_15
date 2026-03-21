from django.contrib import admin
from .models import Brand, Category, Sneaker, SneakerSize, SneakerImage, Wishlist, Review


class SneakerSizeInline(admin.TabularInline):
    model = SneakerSize
    extra = 3


class SneakerImageInline(admin.TabularInline):
    model = SneakerImage
    extra = 2


@admin.register(Sneaker)
class SneakerAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'brand', 'category', 'sku',
        'price', 'discount_percentage', 'total_stock', 'is_active'
    ]
    list_filter = ['brand', 'category', 'is_active', 'is_featured']
    search_fields = ['name', 'sku', 'serial_number', 'colorway']
    readonly_fields = ['view_count', 'popularity_score', 'created_at', 'updated_at']
    inlines = [SneakerSizeInline, SneakerImageInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['sneaker', 'customer', 'rating', 'status', 'created_at']
    list_filter = ['status', 'rating']
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(status='approved')
    approve_reviews.short_description = 'Approve selected reviews'

    def reject_reviews(self, request, queryset):
        queryset.update(status='rejected')
    reject_reviews.short_description = 'Reject selected reviews'


admin.site.register(SneakerSize)
admin.site.register(Wishlist)