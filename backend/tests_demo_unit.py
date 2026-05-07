from decimal import Decimal
import signal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import serializers

from accounts.serializers import ChangePasswordSerializer, UserRegistrationSerializer
from accounts.validators import get_customer_profile_errors
from cart.models import Cart, CartItem
from cart.serializers import AddCartItemSerializer, CartSerializer
from orders.models import Delivery, Invoice, Order, OrderItem
from orders.serializers import OrderCreateSerializer
from products.models import Brand, Category, Review, Sneaker, SneakerSize, Wishlist
from products.serializers import SneakerPriceUpdateSerializer


class TestTimeoutExpired(Exception):
    """Raised when the demo timeout check is exceeded."""


class DemoDataMixin:
    """Shared test data for the sneaker-store unit test demo."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name="Nike", slug="nike")
        cls.category = Category.objects.create(name="Running", slug="running")

    def setUp(self):
        self.user_model = get_user_model()
        self.customer = self.user_model.objects.create_user(
            email="customer@example.com",
            username="customer",
            first_name="Casey",
            last_name="Runner",
            password="StrongPass123!",
            role="customer",
            tax_id="TAX-123",
            home_address="123 Demo Street",
        )
        self.sneaker = Sneaker.objects.create(
            brand=self.brand,
            category=self.category,
            name="Air Zoom Demo",
            model_number="AZD-001",
            colorway="White/Black",
            sku="SKU-AZD-001",
            serial_number="SER-AZD-001",
            description="Demo running sneaker.",
            price=Decimal("200.00"),
            cost_price=Decimal("80.00"),
            discount_percentage=Decimal("10.00"),
            is_active=True,
        )
        self.size = SneakerSize.objects.create(
            sneaker=self.sneaker,
            size_system="US",
            size="10",
            stock=5,
        )

    def tearDown(self):
        self.customer = None
        self.sneaker = None
        self.size = None


class AccountAndProfileUnitTests(DemoDataMixin, TestCase):
    """Suite 1: user identity and checkout-profile rules."""

    # Test 1
    def test_01_user_label_shows_email_and_role(self):
        """Checks the admin-facing user label format."""
        # Arrange
        user = self.customer

        # Act
        label = str(user)

        # Assert
        self.assertEqual(label, "customer@example.com (customer)")

    # Test 2
    def test_02_role_flags_mark_customer_and_exclude_manager_roles(self):
        """Checks the convenience role properties on the User model."""
        # Arrange
        user = self.customer

        # Act
        is_customer = user.is_customer
        is_sales_manager = user.is_sales_manager
        is_product_manager = user.is_product_manager

        # Assert
        self.assertTrue(is_customer)
        self.assertFalse(is_sales_manager)
        self.assertFalse(is_product_manager)

    # Test 3
    def test_03_complete_customer_profile_returns_no_checkout_errors(self):
        """Checks that a filled customer profile passes checkout validation."""
        # Arrange
        user = self.customer

        # Act
        errors = get_customer_profile_errors(user)

        # Assert
        self.assertEqual(errors, {})

    # Test 4
    def test_04_blank_tax_id_and_address_are_flagged_for_customers(self):
        """Checks that missing required checkout fields are reported."""
        # Arrange
        self.customer.tax_id = "   "
        self.customer.home_address = ""

        # Act
        errors = get_customer_profile_errors(self.customer)

        # Assert
        self.assertNotEqual(errors, {})
        self.assertIn("tax_id", errors)
        self.assertIn("home_address", errors)

    # Test 5
    def test_05_manager_accounts_skip_customer_checkout_validation(self):
        """Checks that non-customer roles are excluded from customer-only rules."""
        # Arrange
        manager = self.user_model.objects.create_user(
            email="sales@example.com",
            username="sales",
            first_name="",
            last_name="",
            password="StrongPass123!",
            role="sales_manager",
        )

        # Act
        errors = get_customer_profile_errors(manager)

        # Assert
        self.assertEqual(errors, {})


class ProductModelUnitTests(DemoDataMixin, TestCase):
    """Suite 2: product, stock, wishlist, and review model behavior."""

    # Test 6
    def test_06_brand_string_returns_brand_name(self):
        """Checks the display label for a brand."""
        # Arrange
        brand = self.brand

        # Act
        label = str(brand)

        # Assert
        self.assertEqual(label, "Nike")

    # Test 7
    def test_07_category_string_returns_category_name(self):
        """Checks the display label for a category."""
        # Arrange
        category = self.category

        # Act
        label = str(category)

        # Assert
        self.assertEqual(label, "Running")

    # Test 8
    def test_08_total_stock_adds_inventory_from_all_sizes(self):
        """Checks that sneaker stock is the sum of all size rows."""
        # Arrange
        SneakerSize.objects.create(
            sneaker=self.sneaker,
            size_system="US",
            size="11",
            stock=3,
        )

        # Act
        total_stock = self.sneaker.total_stock

        # Assert
        self.assertEqual(total_stock, 8)

    # Test 9
    def test_09_is_in_stock_becomes_false_when_inventory_reaches_zero(self):
        """Checks the out-of-stock rule for the product card."""
        # Arrange
        self.size.stock = 0
        self.size.save(update_fields=["stock"])

        # Act
        in_stock = self.sneaker.is_in_stock

        # Assert
        self.assertFalse(in_stock)

    # Test 10
    def test_10_discounted_price_applies_percentage_discount(self):
        """Checks the customer-facing sale price calculation."""
        # Arrange
        sneaker = self.sneaker

        # Act
        discounted_price = sneaker.discounted_price

        # Assert
        self.assertEqual(discounted_price, Decimal("180.00"))

    # Test 11
    def test_11_discounted_price_is_none_when_base_price_is_missing(self):
        """Checks that no sale price is shown for unpriced products."""
        # Arrange
        self.sneaker.price = None

        # Act
        discounted_price = self.sneaker.discounted_price

        # Assert
        self.assertIsNone(discounted_price)

    # Test 12
    def test_12_size_label_includes_size_system_size_and_stock(self):
        """Checks the inventory label for a sneaker size."""
        # Arrange
        size = self.size

        # Act
        label = str(size)

        # Assert
        self.assertIsNotNone(label)
        self.assertIn("US 10", label)
        self.assertIn("stock: 5", label)

    # Test 13
    def test_13_duplicate_wishlist_entry_raises_integrity_error(self):
        """Checks that one customer cannot wishlist the same sneaker twice."""
        # Arrange
        Wishlist.objects.create(customer=self.customer, sneaker=self.sneaker)

        # Act / Assert
        with self.assertRaises(IntegrityError):
            Wishlist.objects.create(customer=self.customer, sneaker=self.sneaker)

    # Test 14
    def test_14_review_rating_above_five_raises_validation_error(self):
        """Checks that review ratings stay within the 1-to-5 range."""
        # Arrange
        review = Review(
            sneaker=self.sneaker,
            customer=self.customer,
            rating=6,
            comment="Too high",
        )

        # Act / Assert
        with self.assertRaises(DjangoValidationError):
            review.full_clean()


class SerializerValidationUnitTests(DemoDataMixin, TestCase):
    """Suite 3: serializer validation for signup, password, and pricing."""

    # Test 15
    def test_15_registration_serializer_hashes_password_and_forces_customer_role(self):
        """Checks that self-signup cannot assign a manager role and stores a hash."""
        # Arrange
        serializer = UserRegistrationSerializer(
            data={
                "email": "new-user@example.com",
                "username": "new_user",
                "first_name": "New",
                "last_name": "User",
                "password": "StrongPass123!",
                "tax_id": "TAX-999",
                "home_address": "999 Signup Lane",
                "role": "sales_manager",
            }
        )

        # Act
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Assert
        self.assertEqual(user.role, "customer")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))

    # Test 16
    def test_16_registration_serializer_rejects_weak_passwords(self):
        """Checks that weak signup passwords are blocked."""
        # Arrange
        serializer = UserRegistrationSerializer(
            data={
                "email": "weak@example.com",
                "username": "weak_user",
                "first_name": "Weak",
                "last_name": "User",
                "password": "123",
                "tax_id": "TAX-001",
                "home_address": "Weak Street",
            }
        )

        # Act / Assert
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    # Test 17
    def test_17_change_password_serializer_accepts_matching_new_passwords(self):
        """Checks the happy path for password confirmation."""
        # Arrange
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "StrongPass123!",
                "new_password": "EvenStrongerPass123!",
                "new_password2": "EvenStrongerPass123!",
            }
        )

        # Act
        serializer.is_valid(raise_exception=True)

        # Assert
        self.assertEqual(
            serializer.validated_data["new_password"],
            serializer.validated_data["new_password2"],
        )

    # Test 18
    def test_18_change_password_serializer_rejects_mismatched_confirmation(self):
        """Checks that password confirmation must match exactly."""
        # Arrange
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "StrongPass123!",
                "new_password": "EvenStrongerPass123!",
                "new_password2": "DifferentPass123!",
            }
        )

        # Act / Assert
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    # Test 19
    def test_19_price_update_serializer_requires_price_or_discount(self):
        """Checks that price updates are not allowed with an empty payload."""
        # Arrange
        serializer = SneakerPriceUpdateSerializer(data={})

        # Act / Assert
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    # Test 20
    def test_20_price_update_serializer_rejects_discount_above_hundred(self):
        """Checks the upper limit for product discounts."""
        # Arrange
        serializer = SneakerPriceUpdateSerializer(
            data={"discount_percentage": "101.00"}
        )

        # Act / Assert
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)


class CartUnitTests(DemoDataMixin, TestCase):
    """Suite 4: cart validation and cart total calculation."""

    # Test 21
    def test_21_add_cart_item_serializer_rejects_zero_quantity(self):
        """Checks that cart items must have a quantity of at least one."""
        # Arrange
        serializer = AddCartItemSerializer(
            data={
                "product_id": self.sneaker.id,
                "size_id": self.size.id,
                "product_name": self.sneaker.name,
                "brand": self.brand.name,
                "unit_price": "200.00",
                "quantity": 0,
            }
        )

        # Act
        is_valid = serializer.is_valid()

        # Assert
        self.assertFalse(is_valid)
        self.assertIn("quantity", serializer.errors)

    # Test 22
    def test_22_cart_serializer_returns_item_count_and_total_cost(self):
        """Checks the cart summary shown before checkout."""
        # Arrange
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            sneaker=self.sneaker,
            size=self.size,
            product_slug="air-zoom-demo",
            product_name=self.sneaker.name,
            brand=self.brand.name,
            unit_price=Decimal("180.00"),
            quantity=2,
        )

        # Act
        data = CartSerializer(cart).data

        # Assert
        self.assertEqual(data["item_count"], 2)
        self.assertEqual(data["total"], "360.00")


class OrderFlowUnitTests(DemoDataMixin, TestCase):
    """Suite 5: order totals, stock deduction, and generated records."""

    # Test 23
    def test_23_order_item_subtotal_multiplies_unit_price_by_quantity(self):
        """Checks the subtotal for one line item in an order."""
        # Arrange
        order = Order.objects.create(
            customer=self.customer,
            total_price=Decimal("0.00"),
            delivery_address="123 Demo Street",
        )
        item = OrderItem.objects.create(
            order=order,
            sneaker=self.sneaker,
            size=self.size,
            quantity=3,
            unit_price=Decimal("180.00"),
        )

        # Act
        subtotal = item.subtotal

        # Assert
        self.assertEqual(subtotal, Decimal("540.00"))

    # Test 24
    def test_24_order_calculate_total_rebuilds_total_from_all_items(self):
        """Checks that order totals can be recalculated from stored order lines."""
        # Arrange
        order = Order.objects.create(
            customer=self.customer,
            total_price=Decimal("0.00"),
            delivery_address="123 Demo Street",
        )
        OrderItem.objects.create(
            order=order,
            sneaker=self.sneaker,
            size=self.size,
            quantity=2,
            unit_price=Decimal("180.00"),
        )

        # Act
        order.calculate_total()

        # Assert
        self.assertIsNotNone(order.total_price)
        self.assertEqual(order.total_price, Decimal("360.00"))

    # Test 25
    def test_25_order_creation_finishes_within_timeout_and_creates_side_effects(self):
        """Checks the full checkout side effects: total, invoice, delivery, and stock."""
        # Arrange
        def timeout_handler(_signum, _frame):
            raise TestTimeoutExpired("Order creation exceeded the one-second limit.")

        serializer = OrderCreateSerializer(
            data={
                "delivery_address": "123 Demo Street",
                "credit_card_last4": "4242",
                "items": [
                    {
                        "sneaker_id": self.sneaker.id,
                        "size_id": self.size.id,
                        "quantity": 2,
                    }
                ],
            },
            context={"request": SimpleNamespace(user=self.customer)},
        )
        serializer.is_valid(raise_exception=True)

        # Act
        previous_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 1)
        try:
            order = serializer.save()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)

        # Assert
        self.assertEqual(order.total_price, Decimal("360.00"))
        self.assertTrue(Invoice.objects.filter(order=order).exists())
        self.assertTrue(Delivery.objects.filter(order=order).exists())
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 3)
