from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Brand(models.Model):
    """
    Sneaker brand — Nike, Adidas, Jordan, New Balance, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Sneaker category — Running, Basketball, Lifestyle, Skate, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Sneaker(models.Model):
    """
    Core product model for a sneaker.
    Stock is managed per-size through SneakerSize.
    Price starts as null and is set by the sales manager.
    """
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='sneakers'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sneakers'
    )

    # Identification
    name = models.CharField(max_length=255)           # "Air Force 1 '07"
    model_number = models.CharField(max_length=100)   # "CW2288-111"
    colorway = models.CharField(max_length=255)       # "White/White-White"
    sku = models.CharField(max_length=100, unique=True)  # brand-specific SKU

    # Description
    description = models.TextField(blank=True)
    serial_number = models.CharField(max_length=255, unique=True)

    # Pricing — null until sales manager sets it
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    # Discount — set by sales manager
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Product details
    warranty_status = models.CharField(max_length=255, blank=True)
    distributor_information = models.TextField(blank=True)

    # Flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Analytics
    popularity_score = models.IntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sneakers'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cost_price__gte=0),
                name='sneaker_cost_price_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(discount_percentage__gte=0)
                & models.Q(discount_percentage__lte=100),
                name='sneaker_discount_0_to_100'
            ),
        ]

    def __str__(self):
        return f'{self.brand.name} {self.name} — {self.colorway}'

    @property
    def total_stock(self):
        """Sum of stock across all sizes."""
        return sum(s.stock for s in self.sizes.all())

    @property
    def is_in_stock(self):
        return self.total_stock > 0

    @property
    def discounted_price(self):
        if self.price and self.discount_percentage:
            discount = self.price * (self.discount_percentage / 100)
            return round(self.price - discount, 2)
        return self.price


class SneakerSize(models.Model):
    """
    Stock per size per sneaker.
    One SneakerSize row = one size option with its own stock count.
    """
    SIZE_SYSTEM_CHOICES = [
        ('US', 'US'),
        ('EU', 'EU'),
        ('UK', 'UK'),
    ]

    sneaker = models.ForeignKey(
        Sneaker,
        on_delete=models.CASCADE,
        related_name='sizes'
    )
    size = models.CharField(max_length=10)   # "10", "10.5", "44", "9UK"
    size_system = models.CharField(
        max_length=5,
        choices=SIZE_SYSTEM_CHOICES,
        default='US'
    )
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'sneaker_sizes'
        unique_together = ('sneaker', 'size', 'size_system')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name='sneaker_size_stock_gte_0'
            ),
        ]

    def __str__(self):
        return f'{self.sneaker.name} — {self.size_system} {self.size} (stock: {self.stock})'


class SneakerImage(models.Model):
    """
    Multiple images per sneaker. One image can be marked as primary.
    """
    sneaker = models.ForeignKey(
        Sneaker,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image_url = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'sneaker_images'
        ordering = ['order']

    def __str__(self):
        return f'{self.sneaker.name} image ({self.order})'


class Wishlist(models.Model):
    """
    Customer wishlist — one row per (customer, sneaker) pair.
    When a sneaker's price drops (discount applied), the system
    notifies customers who have it on their wishlist.
    """
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    sneaker = models.ForeignKey(
        Sneaker,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlists'
        unique_together = ('customer', 'sneaker')

    def __str__(self):
        return f'{self.customer.email} → {self.sneaker.name}'


class Review(models.Model):
    """
    Customer review for a sneaker.
    Reviews require product manager approval before becoming visible.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    sneaker = models.ForeignKey(
        Sneaker,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        # One review per customer per sneaker
        unique_together = ('sneaker', 'customer')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='review_rating_1_to_5'
            )
        ]

    def __str__(self):
        return f'{self.customer.email} → {self.sneaker.name} ({self.rating}★)'