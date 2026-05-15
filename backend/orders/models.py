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
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
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

    # Legacy order-level refund totals are retained for reports/backward compatibility.
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refund_approved_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Fulfillment fields live on the order so status has one source of truth.
    tracking_number = models.CharField(max_length=100, blank=True)
    is_completed = models.BooleanField(default=False)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)

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


class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('received', 'Received'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='return_requests'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='return_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    requested_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    manager_note = models.TextField(blank=True)

    class Meta:
        db_table = 'return_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f'Return request #{self.id} for Order #{self.order_id} ({self.status})'


class ReturnRequestItem(models.Model):
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.PROTECT,
        related_name='return_request_items'
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal_refund_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'return_request_items'

    def __str__(self):
        return f'Return item #{self.id} x{self.quantity}'
