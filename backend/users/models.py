from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model. Always define this before the first migration.
    We use email as the login identifier, not username.
    username still exists (inherited from AbstractUser) but is only
    used internally. Users log in with email + password.
    """

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('sales_manager', 'Sales Manager'),
        ('product_manager', 'Product Manager'),
    ]

    email = models.EmailField(unique=True)

    # Customer-specific fields — nullable for manager roles
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    home_address = models.TextField(blank=True, null=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email to log in, not username
    USERNAME_FIELD = 'email'

    # Fields prompted when running createsuperuser
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f'{self.email} ({self.role})'

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_sales_manager(self):
        return self.role == 'sales_manager'

    @property
    def is_product_manager(self):
        return self.role == 'product_manager'