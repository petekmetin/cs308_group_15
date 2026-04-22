from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from products.models import Brand, Category, Sneaker, SneakerSize
from .models import Cart, CartItem


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


class CartClearTests(APITestCase):
    """
    Tests for POST /api/cart/clear/
    """

    def setUp(self):
        self.customer = get_user_model().objects.create_user(
            email='clear-customer@test.com',
            username='clear_customer',
            first_name='Clear',
            last_name='Customer',
            password='StrongPass123!',
        )
        brand    = Brand.objects.create(name='Clear Brand', slug='clear-brand')
        category = Category.objects.create(name='Clear Cat', slug='clear-cat')
        sneaker  = Sneaker.objects.create(
            brand=brand, category=category,
            name='Clear Shoe', model_number='CLR-001',
            colorway='White', sku='SKU-CLR-001',
            serial_number='SER-CLR-001',
            description='Test sneaker.', price='100.00', is_active=True,
        )
        # Pre-load a cart with two items
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart, product_slug='sneaker-1', product_name='Shoe A',
            brand='Brand A', unit_price='100.00', quantity=2,
        )
        CartItem.objects.create(
            cart=cart, product_slug='sneaker-2', product_name='Shoe B',
            brand='Brand B', unit_price='80.00', quantity=1,
        )
        self.client.force_authenticate(self.customer)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/cart/clear/')
        self.assertEqual(response.status_code, 401)

    def test_clear_removes_all_items(self):
        response = self.client.post('/api/cart/clear/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'Cart cleared.')
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 0)

    def test_clear_on_empty_cart_succeeds(self):
        """Clearing an already empty cart should not error."""
        Cart.objects.filter(user=self.customer).first().items.all().delete()
        response = self.client.post('/api/cart/clear/')
        self.assertEqual(response.status_code, 200)

    def test_clear_only_affects_own_cart(self):
        """Clearing one customer's cart must not touch another customer's cart."""
        other = get_user_model().objects.create_user(
            email='other-clear@test.com', username='other_clear',
            first_name='O', last_name='C', password='StrongPass123!',
        )
        other_cart = Cart.objects.create(user=other)
        CartItem.objects.create(
            cart=other_cart, product_slug='sneaker-99', product_name='Other Shoe',
            brand='Other Brand', unit_price='50.00', quantity=1,
        )

        self.client.post('/api/cart/clear/')

        other_cart.refresh_from_db()
        self.assertEqual(other_cart.items.count(), 1)
