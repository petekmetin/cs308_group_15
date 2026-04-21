from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f"Cart<{self.user.email}>"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product_slug = models.SlugField(max_length=120)
    product_name = models.CharField(max_length=255)
    brand = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    accent = models.CharField(max_length=120, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product_slug'],
                name='unique_cart_product_slug',
            )
        ]

    def __str__(self):
        return f"CartItem<{self.product_slug} x {self.quantity}>"
