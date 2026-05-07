from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Brand, Category, Sneaker, SneakerSize


DEMO_PRODUCTS = [
    {
        'sku': 'DEMO-PRODUCT-A',
        'serial_number': 'DEMO-SERIAL-A',
        'name': 'Demo Product A - Out of Stock',
        'model_number': 'DEMO-A-000',
        'colorway': 'Black/Signal Red',
        'description': 'Demo flow Product A searchable by name and intentionally out of stock.',
        'price': Decimal('120.00'),
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
        'popularity_score': 60,
        'size': '43',
        'stock': 1,
    },
    {
        'sku': 'DEMO-PRODUCT-C',
        'serial_number': 'DEMO-SERIAL-C',
        'name': 'Demo Product C - Review Runner',
        'model_number': 'DEMO-C-005',
        'colorway': 'Grey/Volt',
        'description': 'demo-description-target Product C has multiple stock units and supports comment approval.',
        'price': Decimal('155.00'),
        'popularity_score': 90,
        'size': '44',
        'stock': 5,
    },
]


class Command(BaseCommand):
    help = 'Create deterministic products for the CS308 shopping demo flow.'

    def handle(self, *args, **options):
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

        prepared = []
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
                    'cost_price': item['price'] / Decimal('2'),
                    'discount_percentage': Decimal('0.00'),
                    'warranty_status': 'Demo warranty',
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
            prepared.append(f"{item['sku']} stock={item['stock']}")

        self.stdout.write(
            self.style.SUCCESS(
                'Prepared CS308 demo products: ' + ', '.join(prepared)
            )
        )
