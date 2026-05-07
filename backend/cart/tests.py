from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
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
        self.in_stock_us10 = SneakerSize.objects.create(
            sneaker=self.in_stock,
            size_system='US',
            size='10',
            stock=4,
        )
        self.in_stock_us9 = SneakerSize.objects.create(
            sneaker=self.in_stock,
            size_system='US',
            size='9',
            stock=2,
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
        self.out_of_stock_us10 = SneakerSize.objects.create(
            sneaker=self.out_of_stock,
            size_system='US',
            size='10',
            stock=0,
        )

    def _payload_for(self, sneaker, size, quantity=1):
        return {
            'product_id': sneaker.id,
            'size_id': size.id,
            'product_slug': f'sneaker-{sneaker.id}',
            'product_name': sneaker.name,
            'brand': sneaker.brand.name,
            'description': sneaker.description,
            'accent': '',
            'image_url': '',
            'unit_price': str(sneaker.price),
            'quantity': quantity,
        }

    def test_out_of_stock_product_cannot_be_added(self):
        response = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.out_of_stock, self.out_of_stock_us10),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'This product is out of stock.')

    def test_in_stock_product_can_be_added(self):
        response = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us10),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['item_count'], 1)
        item = response.data['items'][0]
        self.assertEqual(item['product_name'], self.in_stock.name)
        self.assertEqual(item['size_id'], self.in_stock_us10.id)
        self.assertEqual(item['size'], self.in_stock_us10.size)
        self.assertEqual(item['size_system'], self.in_stock_us10.size_system)

    def test_size_id_is_required(self):
        payload = self._payload_for(self.in_stock, self.in_stock_us10)
        payload.pop('size_id')
        response = self.client.post('/api/cart/items/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('size_id', response.data)

    def test_size_must_belong_to_the_requested_sneaker(self):
        response = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.out_of_stock_us10),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Selected size does not belong to this product.')

    def test_add_rejects_quantity_above_selected_size_stock(self):
        response = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us10, quantity=5),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Only 4 left for size US 10.')

    def test_add_existing_item_rejects_overflowing_quantity(self):
        first = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us10, quantity=3),
            format='json',
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us10, quantity=2),
            format='json',
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.data['detail'], 'Only 4 left for size US 10.')

    def test_same_sneaker_with_different_sizes_creates_two_cart_lines(self):
        first = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us10),
            format='json',
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us9),
            format='json',
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data['item_count'], 2)
        self.assertEqual(len(second.data['items']), 2)

    def test_update_rejects_quantity_above_size_stock(self):
        response = self.client.post(
            '/api/cart/items/',
            self._payload_for(self.in_stock, self.in_stock_us10),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        item_id = response.data['items'][0]['id']

        update = self.client.patch(
            f'/api/cart/items/{item_id}/',
            {'quantity': 9},
            format='json',
        )
        self.assertEqual(update.status_code, 400)
        self.assertEqual(update.data['detail'], 'Only 4 left for size US 10.')


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
        size_a = SneakerSize.objects.create(
            sneaker=sneaker,
            size_system='US',
            size='9',
            stock=10,
        )
        size_b = SneakerSize.objects.create(
            sneaker=sneaker,
            size_system='US',
            size='10',
            stock=10,
        )
        # Pre-load a cart with two items
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            sneaker=sneaker,
            size=size_a,
            product_slug='sneaker-1',
            product_name='Shoe A',
            brand='Brand A',
            unit_price='100.00',
            quantity=2,
        )
        CartItem.objects.create(
            cart=cart,
            sneaker=sneaker,
            size=size_b,
            product_slug='sneaker-2',
            product_name='Shoe B',
            brand='Brand B',
            unit_price='80.00',
            quantity=1,
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
        other_brand = Brand.objects.create(name='Other Brand', slug='other-brand')
        other_category = Category.objects.create(name='Other Cat', slug='other-cat')
        other_sneaker = Sneaker.objects.create(
            brand=other_brand,
            category=other_category,
            name='Other Shoe',
            model_number='OTH-001',
            colorway='Black',
            sku='SKU-OTH-001',
            serial_number='SER-OTH-001',
            description='Other test sneaker.',
            price='50.00',
            is_active=True,
        )
        other_size = SneakerSize.objects.create(
            sneaker=other_sneaker,
            size_system='US',
            size='8',
            stock=4,
        )
        CartItem.objects.create(
            cart=other_cart,
            sneaker=other_sneaker,
            size=other_size,
            product_slug='sneaker-99',
            product_name='Other Shoe',
            brand='Other Brand',
            unit_price='50.00',
            quantity=1,
        )

        self.client.post('/api/cart/clear/')

        other_cart.refresh_from_db()
        self.assertEqual(other_cart.items.count(), 1)


class CartDetailQueryTests(APITestCase):
    def setUp(self):
        self.customer = get_user_model().objects.create_user(
            email='detail-customer@test.com',
            username='detail_customer',
            first_name='Detail',
            last_name='Customer',
            password='StrongPass123!',
        )
        brand = Brand.objects.create(name='Detail Brand', slug='detail-brand')
        category = Category.objects.create(name='Detail Cat', slug='detail-cat')
        sneaker = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Detail Shoe',
            model_number='DET-001',
            colorway='White',
            sku='SKU-DET-001',
            serial_number='SER-DET-001',
            description='Detail test sneaker.',
            price='120.00',
            is_active=True,
        )
        size = SneakerSize.objects.create(
            sneaker=sneaker,
            size_system='US',
            size='9',
            stock=3,
        )
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            sneaker=sneaker,
            size=size,
            product_slug='sneaker-10',
            product_name='Detail Shoe',
            brand='Detail Brand',
            unit_price='120.00',
            quantity=2,
        )
        self.client.force_authenticate(self.customer)

    def test_cart_detail_reuses_prefetched_items_for_summary(self):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get('/api/cart/')

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(captured), 2)
