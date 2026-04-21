from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from products.models import Brand, Category, Sneaker, SneakerSize


class CartAddItemStockValidationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email='customer@example.com',
            username='customer',
            first_name='Test',
            last_name='User',
            password='StrongPass123!',
        )
        self.client.force_authenticate(user=self.user)

        brand = Brand.objects.create(name='Nike', slug='nike')
        category = Category.objects.create(name='Running', slug='running')

        self.in_stock = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Air Max 97',
            model_number='AM97-001',
            colorway='Silver',
            sku='SKU-AM97-001',
            serial_number='SER-AM97-001',
            description='In stock runner.',
            price='175.00',
            popularity_score=90,
            is_active=True,
        )
        SneakerSize.objects.create(
            sneaker=self.in_stock,
            size_system='US',
            size='10',
            stock=4,
        )

        self.out_of_stock = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Sold Out Retro',
            model_number='SOR-001',
            colorway='Black/Red',
            sku='SKU-SOR-001',
            serial_number='SER-SOR-001',
            description='Sold out pair.',
            price='210.00',
            popularity_score=70,
            is_active=True,
        )
        SneakerSize.objects.create(
            sneaker=self.out_of_stock,
            size_system='US',
            size='10',
            stock=0,
        )

    def _payload_for(self, sneaker):
        return {
            'product_id': sneaker.id,
            'product_slug': f'sneaker-{sneaker.id}',
            'product_name': sneaker.name,
            'brand': sneaker.brand.name,
            'description': sneaker.description,
            'accent': '',
            'image_url': '',
            'unit_price': str(sneaker.price),
            'quantity': 1,
        }

    def test_out_of_stock_product_cannot_be_added(self):
        response = self.client.post('/api/cart/items/', self._payload_for(self.out_of_stock), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'This product is out of stock.')

    def test_in_stock_product_can_be_added(self):
        response = self.client.post('/api/cart/items/', self._payload_for(self.in_stock), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['item_count'], 1)
        self.assertEqual(response.data['items'][0]['product_name'], self.in_stock.name)
