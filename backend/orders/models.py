from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from products.models import Sneaker, SneakerSize


class Order(models.Model):
    """
    A customer order. Can contain multiple OrderItems.
    Total price is stored denormalised for historical accuracy
    (prices may change after the order is placed).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Stored at time of order — do not change after creation
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    delivery_address = models.TextField()

    # Payment
    credit_card_last4 = models.CharField(max_length=4, blank=True)

    # Refund tracking
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refund_approved_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.id} — {self.customer.email} ({self.status})'

    def calculate_total(self):
        """Recalculate total from items. Call before saving."""
        self.total_price = sum(
            item.unit_price * item.quantity
            for item in self.items.all()
        )


class OrderItem(models.Model):
    """
    One line in an order. Stores the price at the time of purchase
    so historical reports remain accurate even if the sneaker price changes.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    sneaker = models.ForeignKey(
        Sneaker,
        on_delete=models.PROTECT
    )
    size = models.ForeignKey(
        SneakerSize,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f'Order #{self.order.id} — {self.sneaker.name} x{self.quantity}'

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Invoice(models.Model):
    """
    Auto-generated invoice for each order.
    Sales managers can view, print, or export these.
    """
    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='invoice'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_path = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-issued_at']

    def __str__(self):
        return f'Invoice {self.invoice_number} for Order #{self.order.id}'


class Delivery(models.Model):
    """
    Delivery tracking. Product managers use this to manage shipments.
    Matches the brief's delivery list requirements:
    delivery ID, customer ID, product ID, quantity, total price,
    delivery address, and completion status.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name='delivery'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    tracking_number = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField()
    is_completed = models.BooleanField(default=False)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'deliveries'

    def __str__(self):
        return f'Delivery for Order #{self.order.id} ({self.status})'