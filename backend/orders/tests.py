import threading
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from products.models import Brand, Category, Sneaker, SneakerSize

from .models import Delivery, Invoice, Order, OrderItem
from .serializers import OrderCreateSerializer


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


class OrderListMetadataTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.pm_user = user_model.objects.create_user(
            email='pm-metadata@example.com',
            username='pm_metadata',
            first_name='Meta',
            last_name='Manager',
            password='StrongPass123!',
            role='product_manager',
        )
        self.customer_user = user_model.objects.create_user(
            email='customer-metadata@example.com',
            username='customer_metadata',
            first_name='Meta',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
        )

        brand = Brand.objects.create(name='Meta Brand', slug='meta-brand')
        category = Category.objects.create(name='Meta Category', slug='meta-category')
        sneaker = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Meta Sneaker',
            model_number='META-001',
            colorway='White',
            sku='SKU-META-001',
            serial_number='SER-META-001',
            description='Metadata test sneaker.',
            price='100.00',
            is_active=True,
        )
        size = SneakerSize.objects.create(
            sneaker=sneaker,
            size_system='EU',
            size='42',
            stock=4,
        )

        self.order_with_meta = Order.objects.create(
            customer=self.customer_user,
            status='pending',
            total_price='100.00',
            delivery_address='Meta Street 1',
            credit_card_last4='1234',
        )
        OrderItem.objects.create(
            order=self.order_with_meta,
            sneaker=sneaker,
            size=size,
            quantity=1,
            unit_price='100.00',
        )
        self.invoice = Invoice.objects.create(
            order=self.order_with_meta,
            invoice_number='INV-META-0001',
        )
        self.delivery = Delivery.objects.create(
            order=self.order_with_meta,
            status='pending',
            delivery_address=self.order_with_meta.delivery_address,
            is_completed=False,
        )

        self.order_without_meta = Order.objects.create(
            customer=self.customer_user,
            status='pending',
            total_price='100.00',
            delivery_address='Meta Street 2',
            credit_card_last4='5678',
        )
        OrderItem.objects.create(
            order=self.order_without_meta,
            sneaker=sneaker,
            size=size,
            quantity=1,
            unit_price='100.00',
        )

    def test_manager_order_list_includes_invoice_and_delivery_metadata(self):
        client = self.client_class()
        client.force_authenticate(self.pm_user)
        response = client.get('/api/orders/')
        self.assertEqual(response.status_code, 200)
        rows = response.data.get('results', response.data)

        by_id = {row['id']: row for row in rows}
        with_meta = by_id[self.order_with_meta.id]
        without_meta = by_id[self.order_without_meta.id]

        self.assertEqual(with_meta['invoice_number'], self.invoice.invoice_number)
        self.assertEqual(with_meta['delivery_id'], self.delivery.id)
        self.assertFalse(with_meta['delivery_is_completed'])

        self.assertIsNone(without_meta['invoice_number'])
        self.assertIsNone(without_meta['delivery_id'])
        self.assertIsNone(without_meta['delivery_is_completed'])


class OrderTransactionTests(APITestCase):
    """
    Verifies that each multi-write operation is fully atomic:
    - Happy path: all writes committed together.
    - Failure path: a simulated crash mid-operation rolls back every prior write.
    """

    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(
            email='tx-customer@example.com',
            username='tx_customer',
            first_name='TX',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
            tax_id='TX-CUST-001',
            home_address='1 TX Customer Home',
        )
        self.sales_manager = User.objects.create_user(
            email='tx-sales@example.com',
            username='tx_sales',
            first_name='TX',
            last_name='Sales',
            password='StrongPass123!',
            role='sales_manager',
        )
        self.product_manager = User.objects.create_user(
            email='tx-pm@example.com',
            username='tx_pm',
            first_name='TX',
            last_name='PM',
            password='StrongPass123!',
            role='product_manager',
        )

        brand = Brand.objects.create(name='Nike TX', slug='nike-tx')
        category = Category.objects.create(name='Running TX', slug='running-tx')
        self.sneaker = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Air Max TX',
            model_number='AM-TX-001',
            colorway='Black',
            sku='SKU-AM-TX-001',
            serial_number='SER-AM-TX-001',
            description='Test sneaker.',
            price='120.00',
            is_active=True,
        )
        self.size = SneakerSize.objects.create(
            sneaker=self.sneaker,
            size_system='US',
            size='9',
            stock=10,
        )

    def _make_order(self, status='pending'):
        """Create an order + item directly in DB (bypasses stock deduction)."""
        order = Order.objects.create(
            customer=self.customer,
            status=status,
            total_price='240.00',
            delivery_address='1 Test Ave',
            credit_card_last4='1234',
        )
        OrderItem.objects.create(
            order=order,
            sneaker=self.sneaker,
            size=self.size,
            quantity=2,
            unit_price='120.00',
        )
        return order

    # ── Order Creation ──────────────────────────────────────────────────────

    def test_create_order_commits_all_writes(self):
        """Successful order: stock deducted, Order/Invoice/Delivery all created."""
        self.client.force_authenticate(self.customer)
        initial_stock = self.size.stock

        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 2}],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        order_id = response.data['id']
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, initial_stock - 2)
        self.assertTrue(Invoice.objects.filter(order_id=order_id).exists())
        self.assertTrue(Delivery.objects.filter(order_id=order_id).exists())

    def test_create_order_rollback_restores_stock_and_removes_order(self):
        """Crash creating Delivery rolls back Order, OrderItems, and stock deduction."""
        self.client.force_authenticate(self.customer)
        initial_stock = self.size.stock
        initial_order_count = Order.objects.count()

        self.client.raise_request_exception = False
        with patch('orders.serializers.Delivery.objects.create',
                   side_effect=Exception('Simulated DB failure')):
            response = self.client.post('/api/orders/create/', {
                'delivery_address': '1 Test Ave',
                'credit_card_last4': '1234',
                'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 2}],
            }, format='json')

        self.assertEqual(response.status_code, 500)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, initial_stock)
        self.assertEqual(Order.objects.count(), initial_order_count)
        self.assertEqual(Invoice.objects.count(), 0)

    # ── Cancel Order ────────────────────────────────────────────────────────

    def test_cancel_order_commits_stock_restoration_and_status(self):
        """Successful cancel: stock restored and order marked cancelled together."""
        order = self._make_order(status='pending')
        self.client.force_authenticate(self.customer)

        response = self.client.post(f'/api/orders/{order.id}/cancel/')

        self.assertEqual(response.status_code, 200)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 12)  # 10 + 2 returned
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_cancel_order_rollback_keeps_stock_and_status_unchanged(self):
        """Crash on order.save() rolls back the stock restoration."""
        order = self._make_order(status='pending')
        self.client.force_authenticate(self.customer)

        self.client.raise_request_exception = False
        with patch.object(Order, 'save', side_effect=Exception('Simulated DB failure')):
            response = self.client.post(f'/api/orders/{order.id}/cancel/')

        self.assertEqual(response.status_code, 500)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 10)  # unchanged
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')  # unchanged

    # ── Approve Refund ──────────────────────────────────────────────────────

    def test_approve_refund_commits_stock_restoration_and_order_update(self):
        """Successful refund approval: stock restored and order fully updated."""
        order = self._make_order(status='return_requested')
        self.client.force_authenticate(self.sales_manager)

        response = self.client.post(f'/api/orders/{order.id}/approve-refund/')

        self.assertEqual(response.status_code, 200)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 12)  # 10 + 2 returned
        order.refresh_from_db()
        self.assertEqual(order.status, 'returned')
        self.assertIsNotNone(order.refund_approved_at)
        self.assertEqual(str(order.refund_amount), str(order.total_price))

    def test_approve_refund_rollback_keeps_stock_and_status_unchanged(self):
        """Crash on order.save() rolls back the stock restoration."""
        order = self._make_order(status='return_requested')
        self.client.force_authenticate(self.sales_manager)

        self.client.raise_request_exception = False
        with patch.object(Order, 'save', side_effect=Exception('Simulated DB failure')):
            response = self.client.post(f'/api/orders/{order.id}/approve-refund/')

        self.assertEqual(response.status_code, 500)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 10)  # unchanged
        order.refresh_from_db()
        self.assertEqual(order.status, 'return_requested')  # unchanged

    # ── Delivery Update ─────────────────────────────────────────────────────

    def test_update_delivery_to_delivered_commits_both_saves(self):
        """Marking delivery delivered updates both the delivery and order status."""
        order = self._make_order(status='processing')
        delivery = Delivery.objects.create(
            order=order,
            status='in_transit',
            delivery_address=order.delivery_address,
        )
        self.client.force_authenticate(self.product_manager)

        response = self.client.patch(
            f'/api/orders/deliveries/{delivery.id}/',
            {'status': 'delivered'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        delivery.refresh_from_db()
        order.refresh_from_db()
        self.assertTrue(delivery.is_completed)
        self.assertEqual(order.status, 'delivered')

    def test_update_delivery_rollback_keeps_order_status_unchanged(self):
        """Crash on delivery.save() rolls back the order status update."""
        order = self._make_order(status='processing')
        delivery = Delivery.objects.create(
            order=order,
            status='in_transit',
            delivery_address=order.delivery_address,
        )
        self.client.force_authenticate(self.product_manager)

        self.client.raise_request_exception = False
        with patch.object(Delivery, 'save', side_effect=Exception('Simulated DB failure')):
            response = self.client.patch(
                f'/api/orders/deliveries/{delivery.id}/',
                {'status': 'delivered'},
                format='json',
            )

        self.assertEqual(response.status_code, 500)
        order.refresh_from_db()
        self.assertEqual(order.status, 'processing')  # rolled back, not 'delivered'

    # ── Order creation edge cases ────────────────────────────────────────────

    def test_create_order_rejects_quantity_exceeding_stock(self):
        """Ordering more than available stock returns 400 and leaves stock unchanged."""
        self.client.force_authenticate(self.customer)
        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 99}],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 10)

    def test_create_order_succeeds_at_exact_stock_boundary(self):
        """Ordering exactly the available stock succeeds and leaves stock at 0."""
        self.client.force_authenticate(self.customer)
        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 10}],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.size.refresh_from_db()
        self.assertEqual(self.size.stock, 0)

    def test_create_order_rejects_empty_items_list(self):
        """An order with no items is rejected before any DB write."""
        self.client.force_authenticate(self.customer)
        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_rejects_sneaker_without_price(self):
        """Ordering a sneaker with no price set returns 400."""
        self.sneaker.price = None
        self.sneaker.save()
        self.client.force_authenticate(self.customer)
        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_rejects_non_customer_role(self):
        """Sales managers cannot place orders."""
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_create_order_rejects_customer_missing_tax_id(self):
        """Customers must complete tax ID before order creation."""
        self.customer.tax_id = ''
        self.customer.save(update_fields=['tax_id'])
        self.client.force_authenticate(self.customer)

        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 1}],
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('tax_id', response.data)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_rejects_customer_missing_home_address(self):
        """Customers must complete home address before order creation."""
        self.customer.home_address = ''
        self.customer.save(update_fields=['home_address'])
        self.client.force_authenticate(self.customer)

        response = self.client.post('/api/orders/create/', {
            'delivery_address': '1 Test Ave',
            'credit_card_last4': '1234',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 1}],
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('home_address', response.data)
        self.assertEqual(Order.objects.count(), 0)

    # ── Cancel order edge cases ──────────────────────────────────────────────

    def test_cancel_order_rejects_non_cancellable_status(self):
        """Cancelling a delivered order returns 400 and leaves status unchanged."""
        order = self._make_order(status='delivered')
        self.client.force_authenticate(self.customer)
        response = self.client.post(f'/api/orders/{order.id}/cancel/')
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')

    def test_cancel_order_rejects_another_customers_order(self):
        """A customer cannot cancel an order that belongs to someone else."""
        User = get_user_model()
        other = User.objects.create_user(
            email='other-tx@test.com', username='other_tx',
            first_name='O', last_name='T',
            password='StrongPass123!', role='customer',
        )
        order = self._make_order(status='pending')
        other_client = self.client_class()
        other_client.force_authenticate(other)
        response = other_client.post(f'/api/orders/{order.id}/cancel/')
        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    # ── Refund request edge cases ────────────────────────────────────────────

    def test_request_refund_rejects_non_delivered_order(self):
        """Refund can only be requested on delivered orders."""
        order = self._make_order(status='processing')
        self.client.force_authenticate(self.customer)
        response = self.client.post(f'/api/orders/{order.id}/refund/')
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'processing')

    def test_request_refund_rejects_after_30_day_window(self):
        """Refund request is rejected if more than 30 days have passed since delivery."""
        order = self._make_order(status='delivered')
        Order.objects.filter(id=order.id).update(
            updated_at=timezone.now() - timedelta(days=31)
        )
        self.client.force_authenticate(self.customer)
        response = self.client.post(f'/api/orders/{order.id}/refund/')
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')

    def test_request_refund_succeeds_within_30_day_window(self):
        """Refund request within 30 days succeeds."""
        order = self._make_order(status='delivered')
        Order.objects.filter(id=order.id).update(
            updated_at=timezone.now() - timedelta(days=15)
        )
        self.client.force_authenticate(self.customer)
        response = self.client.post(f'/api/orders/{order.id}/refund/')
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'return_requested')
        self.assertIsNotNone(order.refund_requested_at)

    # ── Approve refund edge cases ────────────────────────────────────────────

    def test_approve_refund_rejects_wrong_status(self):
        """Approving a refund on a pending order returns 400."""
        order = self._make_order(status='pending')
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post(f'/api/orders/{order.id}/approve-refund/')
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_approve_refund_rejects_non_sales_manager(self):
        """Customers cannot approve refunds."""
        order = self._make_order(status='return_requested')
        self.client.force_authenticate(self.customer)
        response = self.client.post(f'/api/orders/{order.id}/approve-refund/')
        self.assertEqual(response.status_code, 403)


class OrderRaceConditionTests(TransactionTestCase):
    """
    Verifies that concurrent orders cannot oversell stock.

    Uses real threads + TransactionTestCase (data is committed, visible
    across connections) to simulate two requests racing to buy the last item.
    """

    def setUp(self):
        User = get_user_model()
        self.customer1 = User.objects.create_user(
            email='race1@test.com', username='race1',
            first_name='Race', last_name='One',
            password='StrongPass123!', role='customer',
            tax_id='RACE-001',
            home_address='1 Race One Home',
        )
        self.customer2 = User.objects.create_user(
            email='race2@test.com', username='race2',
            first_name='Race', last_name='Two',
            password='StrongPass123!', role='customer',
            tax_id='RACE-002',
            home_address='2 Race Two Home',
        )
        brand = Brand.objects.create(name='Race Brand', slug='race-brand')
        category = Category.objects.create(name='Race Cat', slug='race-cat')
        self.sneaker = Sneaker.objects.create(
            brand=brand, category=category,
            name='Race Shoe', model_number='RACE-001',
            colorway='Red', sku='SKU-RACE-001',
            serial_number='SER-RACE-001',
            description='Race test sneaker.',
            price='100.00', is_active=True,
        )
        self.size = SneakerSize.objects.create(
            sneaker=self.sneaker,
            size_system='US', size='10', stock=1,
        )
        # Barrier ensures both threads reach the API call at the same time,
        # maximising the chance of a true race.
        self.barrier = threading.Barrier(2)

    def test_concurrent_orders_cannot_oversell(self):
        """
        Two customers simultaneously ordering the last item:
        exactly one order is created, stock never goes negative.
        """
        sneaker_id = self.sneaker.id
        size_id = self.size.id
        statuses = []
        lock = threading.Lock()

        def place_order(user_id):
            User = get_user_model()
            user = User.objects.get(id=user_id)
            client = APIClient()
            client.force_authenticate(user=user)
            self.barrier.wait()  # both threads fire at the same time
            response = client.post('/api/orders/create/', {
                'delivery_address': '1 Test Ave',
                'credit_card_last4': '1234',
                'items': [{'sneaker_id': sneaker_id, 'size_id': size_id, 'quantity': 1}],
            }, format='json')
            with lock:
                statuses.append(response.status_code)

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(place_order, self.customer1.id)
            f2 = executor.submit(place_order, self.customer2.id)
            f1.result()
            f2.result()

        self.size.refresh_from_db()
        self.assertGreaterEqual(self.size.stock, 0)   # never went negative
        self.assertEqual(Order.objects.count(), 1)     # exactly one order created
        self.assertIn(201, statuses)                   # one request succeeded


class OrderCreateResponseTests(APITestCase):
    """
    Verifies that POST /api/orders/create/ returns the full order shape
    including invoice_number, as required for the on-screen invoice display.
    """

    def setUp(self):
        self.customer = get_user_model().objects.create_user(
            email='invoice-customer@test.com',
            username='invoice_customer',
            first_name='Invoice',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
            tax_id='INV-CUST-001',
            home_address='1 Invoice Customer Home',
        )
        brand    = Brand.objects.create(name='Invoice Brand', slug='invoice-brand')
        category = Category.objects.create(name='Invoice Cat',  slug='invoice-cat')
        self.sneaker = Sneaker.objects.create(
            brand=brand, category=category,
            name='Invoice Shoe', model_number='INV-001',
            colorway='Black', sku='SKU-INV-001',
            serial_number='SER-INV-001',
            description='Test.', price='99.00', is_active=True,
        )
        self.size = SneakerSize.objects.create(
            sneaker=self.sneaker, size_system='US', size='10', stock=5,
        )
        self.client.force_authenticate(self.customer)

    def _place_order(self):
        return self.client.post('/api/orders/create/', {
            'delivery_address':  '1 Invoice Ave',
            'credit_card_last4': '9999',
            'items': [{'sneaker_id': self.sneaker.id, 'size_id': self.size.id, 'quantity': 1}],
        }, format='json')

    def test_response_contains_invoice_number(self):
        """Order creation must return invoice_number for the on-screen invoice."""
        response = self._place_order()
        self.assertEqual(response.status_code, 201)
        self.assertIn('invoice_number', response.data)
        self.assertIsNotNone(response.data['invoice_number'])
        self.assertTrue(response.data['invoice_number'].startswith('INV-'))

    def test_response_contains_full_order_fields(self):
        """Response must include all fields needed to render the invoice."""
        response = self._place_order()
        self.assertEqual(response.status_code, 201)
        for field in ('id', 'total_price', 'delivery_address', 'credit_card_last4',
                      'items', 'created_at', 'status', 'invoice_number'):
            self.assertIn(field, response.data, msg=f"Missing field: {field}")

    def test_response_items_include_subtotals(self):
        """Each line item in the response must expose subtotal for invoice rendering."""
        response = self._place_order()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['items']), 1)
        item = response.data['items'][0]
        self.assertIn('subtotal', item)
        self.assertEqual(float(item['subtotal']), float(item['unit_price']) * item['quantity'])
        self.assertEqual(item['size_system'], self.size.size_system)
        self.assertEqual(item['size_value'], self.size.size)

    def test_invoice_number_is_unique_per_order(self):
        """Two separate orders must receive different invoice numbers."""
        r1 = self._place_order()
        r2 = self._place_order()
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.data['invoice_number'], r2.data['invoice_number'])

    def test_order_create_generates_pdf_and_emails_invoice(self):
        """Successful order creation emails a PDF invoice and stores its path."""
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(
                MEDIA_ROOT=media_root,
                EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                DEFAULT_FROM_EMAIL='sales@solevault.test',
            ):
                response = self._place_order()

                self.assertEqual(response.status_code, 201)
                self.assertTrue(response.data['invoice_email_sent'])
                self.assertNotIn('invoice_email_error', response.data)

                invoice = Invoice.objects.get(order_id=response.data['id'])
                self.assertTrue(invoice.pdf_path)
                self.assertTrue(invoice.pdf_path.endswith('.pdf'))
                self.assertTrue(os.path.exists(os.path.join(media_root, invoice.pdf_path)))

                self.assertEqual(len(mail.outbox), 1)
                message = mail.outbox[0]
                self.assertEqual(message.to, [self.customer.email])
                self.assertIn(response.data['invoice_number'], message.subject)
                self.assertEqual(len(message.attachments), 1)
                filename, content, mimetype = message.attachments[0]
                self.assertTrue(filename.endswith('.pdf'))
                self.assertEqual(mimetype, 'application/pdf')
                self.assertTrue(content.startswith(b'%PDF'))

    @patch('django.core.mail.message.EmailMessage.send', side_effect=RuntimeError('SMTP unavailable'))
    def test_order_create_still_succeeds_when_invoice_email_fails(self, _send):
        """Email failure must not roll back payment/order success."""
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                with self.assertLogs('orders.views', level='ERROR'):
                    response = self._place_order()

                self.assertEqual(response.status_code, 201)
                self.assertFalse(response.data['invoice_email_sent'])
                self.assertEqual(
                    response.data['invoice_email_error'],
                    'Invoice email could not be sent.',
                )
                invoice = Invoice.objects.get(order_id=response.data['id'])
                self.assertTrue(invoice.pdf_path)
