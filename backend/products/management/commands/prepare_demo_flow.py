from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cart.models import CartItem
from orders.models import Invoice, Order, ReturnRequest
from products.models import Brand, Category, Review, Sneaker, SneakerSize, Wishlist


DEMO_PASSWORD = 'Cemsarp1234'
DEMO_CUSTOMER_EMAIL = 'cemsarptakim@gmail.com'
DEMO_SALES_EMAIL = 'sales@gmail.com'
DEMO_PRODUCT_EMAIL = 'product@gmail.com'
DEMO_PRODUCT_PREFIX = 'DEMO-PRODUCT'
DEMO_MANAGER_CATEGORY_SLUG = 'final-demo-manager-category'


DEMO_PRODUCTS = [
    {
        'sku': 'DEMO-PRODUCT-A',
        'serial_number': 'DEMO-SERIAL-A',
        'name': 'Demo Product A - Out of Stock',
        'model_number': 'DEMO-A-000',
        'colorway': 'Black/Signal Red',
        'description': 'Demo flow Product A searchable by name and intentionally out of stock.',
        'price': Decimal('120.00'),
        'cost_price': Decimal('60.00'),
        'popularity_score': 30,
        'size': '42',
        'stock': 0,
    },
    {
        'sku': 'DEMO-PRODUCT-B',
        'serial_number': 'DEMO-SERIAL-B',
        'name': 'Demo Product B - Last Pair',
        'model_number': 'DEMO-B-001',
        'colorway': 'White/Royal Blue',
        'description': 'Demo flow Product B has exactly one pair in stock for cart checkout.',
        'price': Decimal('135.00'),
        'cost_price': Decimal('67.50'),
        'popularity_score': 60,
        'size': '43',
        'stock': 1,
    },
    {
        'sku': 'DEMO-PRODUCT-C',
        'serial_number': 'DEMO-SERIAL-C',
        'name': 'Demo Product C - Wishlist Runner',
        'model_number': 'DEMO-C-005',
        'colorway': 'Grey/Volt',
        'description': 'Product C has multiple stock units and is added to the wishlist during the demo.',
        'price': Decimal('155.00'),
        'cost_price': Decimal('77.50'),
        'popularity_score': 90,
        'size': '44',
        'stock': 5,
    },
    {
        'sku': 'DEMO-PRODUCT-E',
        'serial_number': 'DEMO-SERIAL-E',
        'name': 'Demo Product E - Old Delivered Pair',
        'model_number': 'DEMO-E-040',
        'colorway': 'Cream/Navy',
        'description': 'Product E was delivered more than 30 days ago and is outside the return window.',
        'price': Decimal('180.00'),
        'cost_price': Decimal('90.00'),
        'popularity_score': 55,
        'size': '42',
        'stock': 2,
    },
    {
        'sku': 'DEMO-PRODUCT-F',
        'serial_number': 'DEMO-SERIAL-F',
        'name': 'Demo Product F - Return Window Pair',
        'model_number': 'DEMO-F-008',
        'colorway': 'Forest/White',
        'description': 'Product F was delivered recently and can be returned during the demo.',
        'price': Decimal('165.00'),
        'cost_price': Decimal('82.50'),
        'popularity_score': 58,
        'size': '43',
        'stock': 2,
    },
    {
        'sku': 'DEMO-PRODUCT-G',
        'serial_number': 'DEMO-SERIAL-G',
        'name': 'Demo Product G - Processing Order Pair',
        'model_number': 'DEMO-G-001',
        'colorway': 'Orange/Black',
        'description': 'Product G has a recent processing order that the customer can cancel.',
        'price': Decimal('142.00'),
        'cost_price': Decimal('71.00'),
        'popularity_score': 52,
        'size': '44',
        'stock': 2,
    },
    {
        'sku': 'DEMO-PRODUCT-H',
        'serial_number': 'DEMO-SERIAL-H',
        'name': 'Demo Product H - In Transit Pair',
        'model_number': 'DEMO-H-002',
        'colorway': 'Silver/Black',
        'description': 'Product H has a recent in-transit order that cannot be cancelled or returned yet.',
        'price': Decimal('172.00'),
        'cost_price': Decimal('86.00'),
        'popularity_score': 54,
        'size': '45',
        'stock': 2,
    },
]


DEMO_ORDER_SCENARIOS = {
    'DEMO-PRODUCT-E': {
        'invoice_number': 'INV-DEMO-PRODUCT-E',
        'status': 'delivered',
        'created_days_ago': 45,
        'dispatched_days_ago': 43,
        'delivered_days_ago': 40,
        'tracking_number': 'DEMO-TRACK-E',
        'notes': 'Delivered outside the 30-day return window.',
    },
    'DEMO-PRODUCT-F': {
        'invoice_number': 'INV-DEMO-PRODUCT-F',
        'status': 'delivered',
        'created_days_ago': 12,
        'dispatched_days_ago': 10,
        'delivered_days_ago': 8,
        'tracking_number': 'DEMO-TRACK-F',
        'notes': 'Delivered inside the 30-day return window.',
    },
    'DEMO-PRODUCT-G': {
        'invoice_number': 'INV-DEMO-PRODUCT-G',
        'status': 'processing',
        'created_days_ago': 1,
        'tracking_number': '',
        'notes': 'Processing order prepared for cancellation.',
    },
    'DEMO-PRODUCT-H': {
        'invoice_number': 'INV-DEMO-PRODUCT-H',
        'status': 'in_transit',
        'created_days_ago': 2,
        'dispatched_days_ago': 1,
        'tracking_number': 'DEMO-TRACK-H',
        'notes': 'In transit order prepared for delivery status comparison.',
    },
}


class Command(BaseCommand):
    help = 'Reset and create deterministic data for the CS308 final demo flow.'

    def handle(self, *args, **options):
        with transaction.atomic():
            customer = self._upsert_user(
                email=DEMO_CUSTOMER_EMAIL,
                username='final_demo_customer',
                first_name='Cem',
                last_name='Sarp',
                role='customer',
                tax_id='TR-FINAL-DEMO-001',
                home_address='Final Demo Apartment, 15 Demo Street, Istanbul',
            )
            sales_manager = self._upsert_user(
                email=DEMO_SALES_EMAIL,
                username='final_demo_sales',
                first_name='Final',
                last_name='Sales',
                role='sales_manager',
            )
            product_manager = self._upsert_user(
                email=DEMO_PRODUCT_EMAIL,
                username='final_demo_product',
                first_name='Final',
                last_name='Product',
                role='product_manager',
            )

            self._clear_previous_demo_state()
            products = self._prepare_products()
            self._prepare_orders(customer, products)

        prepared = ', '.join(
            f"{sku} stock={products[sku].total_stock}"
            for sku in ['DEMO-PRODUCT-A', 'DEMO-PRODUCT-B', 'DEMO-PRODUCT-C']
        )
        self.stdout.write(
            self.style.SUCCESS(
                'Prepared CS308 final demo data: '
                f'customer={customer.email}, sales={sales_manager.email}, '
                f'product={product_manager.email}; {prepared}; Product D absent.'
            )
        )

    def _upsert_user(self, *, email, username, first_name, last_name, role, tax_id='', home_address=''):
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'tax_id': tax_id or None,
                'home_address': home_address or None,
                'is_active': True,
            },
        )
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.tax_id = tax_id or None
        user.home_address = home_address or None
        user.is_active = True
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _clear_previous_demo_state(self):
        demo_orders = Order.objects.filter(
            items__sneaker__sku__startswith=DEMO_PRODUCT_PREFIX,
        ).distinct()
        ReturnRequest.objects.filter(order__in=demo_orders).delete()
        Invoice.objects.filter(order__in=demo_orders).delete()
        demo_orders.delete()

        CartItem.objects.filter(sneaker__sku__startswith=DEMO_PRODUCT_PREFIX).delete()
        Wishlist.objects.filter(sneaker__sku__startswith=DEMO_PRODUCT_PREFIX).delete()
        Review.objects.filter(sneaker__sku__startswith=DEMO_PRODUCT_PREFIX).delete()

        Sneaker.objects.filter(sku='DEMO-PRODUCT-D').delete()
        Category.objects.filter(slug=DEMO_MANAGER_CATEGORY_SLUG).delete()

    def _prepare_products(self):
        brand, _ = Brand.objects.get_or_create(
            slug='demo-flow',
            defaults={
                'name': 'Demo Flow',
                'description': 'Deterministic products for the CS308 demo flow.',
            },
        )
        category, _ = Category.objects.get_or_create(
            slug='demo-flow',
            defaults={
                'name': 'Demo Flow',
                'description': 'Products prepared for scripted demo scenarios.',
            },
        )

        products = {}
        for item in DEMO_PRODUCTS:
            sneaker, _ = Sneaker.objects.update_or_create(
                sku=item['sku'],
                defaults={
                    'brand': brand,
                    'category': category,
                    'name': item['name'],
                    'model_number': item['model_number'],
                    'colorway': item['colorway'],
                    'serial_number': item['serial_number'],
                    'description': item['description'],
                    'price': item['price'],
                    'original_price': item['price'],
                    'cost_price': item['cost_price'],
                    'discount_percentage': Decimal('0.00'),
                    'warranty_status': 'Final demo warranty',
                    'distributor_information': 'Prepared by prepare_demo_flow.',
                    'is_active': True,
                    'is_featured': True,
                    'popularity_score': item['popularity_score'],
                },
            )

            sneaker.sizes.all().delete()
            SneakerSize.objects.create(
                sneaker=sneaker,
                size_system='EU',
                size=item['size'],
                stock=item['stock'],
            )
            products[item['sku']] = sneaker
        return products

    def _prepare_orders(self, customer, products):
        now = timezone.now()
        for sku, scenario in DEMO_ORDER_SCENARIOS.items():
            sneaker = products[sku]
            size = sneaker.sizes.get()
            price = sneaker.discounted_price or sneaker.price
            created_at = now - timedelta(days=scenario['created_days_ago'])
            dispatched_at = None
            delivered_at = None
            if scenario.get('dispatched_days_ago') is not None:
                dispatched_at = now - timedelta(days=scenario['dispatched_days_ago'])
            if scenario.get('delivered_days_ago') is not None:
                delivered_at = now - timedelta(days=scenario['delivered_days_ago'])

            order = Order.objects.create(
                customer=customer,
                status=scenario['status'],
                total_price=price,
                delivery_address=customer.home_address,
                credit_card_last4='4242',
                tracking_number=scenario['tracking_number'],
                is_completed=scenario['status'] == 'delivered',
                dispatched_at=dispatched_at,
                delivered_at=delivered_at,
                delivery_notes=scenario['notes'],
            )
            order.items.create(
                sneaker=sneaker,
                size=size,
                quantity=1,
                unit_price=price,
            )
            invoice = Invoice.objects.create(
                order=order,
                invoice_number=scenario['invoice_number'],
            )
            Order.objects.filter(pk=order.pk).update(
                created_at=created_at,
                updated_at=created_at,
            )
            Invoice.objects.filter(pk=invoice.pk).update(issued_at=created_at)
