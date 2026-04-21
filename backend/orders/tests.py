from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from products.models import Brand, Category, Sneaker, SneakerSize

from .models import Delivery, Order, OrderItem


class DeliveryEndpointsTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.pm_user = user_model.objects.create_user(
            email='pm-orders@example.com',
            username='pm_orders',
            first_name='Order',
            last_name='Manager',
            password='StrongPass123!',
            role='product_manager',
        )
        self.customer_user = user_model.objects.create_user(
            email='customer-orders@example.com',
            username='customer_orders',
            first_name='Regular',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
        )

        brand = Brand.objects.create(name='Asics', slug='asics')
        category = Category.objects.create(name='Training', slug='training')
        sneaker = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Tempo Runner',
            model_number='TR-001',
            colorway='Navy',
            sku='SKU-TR-001',
            serial_number='SER-TR-001',
            description='Stable daily runner.',
            price='140.00',
            is_active=True,
        )
        size = SneakerSize.objects.create(
            sneaker=sneaker,
            size_system='US',
            size='10',
            stock=7,
        )

        self.order = Order.objects.create(
            customer=self.customer_user,
            status='pending',
            total_price='280.00',
            delivery_address='123 Test Street',
            credit_card_last4='4242',
        )
        OrderItem.objects.create(
            order=self.order,
            sneaker=sneaker,
            size=size,
            quantity=2,
            unit_price='140.00',
        )
        self.delivery = Delivery.objects.create(
            order=self.order,
            status='pending',
            delivery_address=self.order.delivery_address,
            is_completed=False,
        )

    def test_delivery_list_is_pm_only_and_contains_nested_order_shape(self):
        customer_client = self.client_class()
        customer_client.force_authenticate(self.customer_user)
        denied = customer_client.get('/api/orders/deliveries/')
        self.assertEqual(denied.status_code, 403)

        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        response = pm_client.get('/api/orders/deliveries/')
        self.assertEqual(response.status_code, 200)

        rows = response.data.get('results', response.data)
        self.assertEqual(len(rows), 1)
        row = rows[0]

        self.assertEqual(row['id'], self.delivery.id)
        self.assertEqual(row['delivery_address'], self.order.delivery_address)
        self.assertEqual(row['status'], 'pending')
        self.assertFalse(row['is_completed'])
        self.assertEqual(row['order']['id'], self.order.id)
        self.assertEqual(row['order']['customer'], self.customer_user.id)
        self.assertEqual(str(row['order']['total_price']), str(self.order.total_price))
        self.assertEqual(len(row['order']['items']), 1)
        self.assertEqual(row['order']['items'][0]['sneaker'], self.order.items.first().sneaker_id)
        self.assertEqual(row['order']['items'][0]['quantity'], 2)
        self.assertTrue(row['order']['items'][0]['sneaker_name'])

    def test_delivery_patch_updates_status_and_marks_completed_on_delivered(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        in_transit = pm_client.patch(
            f'/api/orders/deliveries/{self.delivery.id}/',
            {'status': 'in_transit'},
            format='json',
        )
        self.assertEqual(in_transit.status_code, 200)
        self.assertEqual(in_transit.data['status'], 'in_transit')
        self.assertFalse(in_transit.data['is_completed'])

        delivered = pm_client.patch(
            f'/api/orders/deliveries/{self.delivery.id}/',
            {'status': 'delivered'},
            format='json',
        )
        self.assertEqual(delivered.status_code, 200)
        self.assertEqual(delivered.data['status'], 'delivered')
        self.assertTrue(delivered.data['is_completed'])

        self.delivery.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.delivery.is_completed)
        self.assertEqual(self.order.status, 'delivered')

        list_after_delivery = pm_client.get('/api/orders/deliveries/')
        self.assertEqual(list_after_delivery.status_code, 200)
        rows = list_after_delivery.data.get('results', list_after_delivery.data)
        self.assertEqual(rows, [])
