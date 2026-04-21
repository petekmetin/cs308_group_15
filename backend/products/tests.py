from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Brand, Category, Sneaker, SneakerSize, Review


class SneakerListApiTests(APITestCase):
    def setUp(self):
        self.brand_nike = Brand.objects.create(name='Nike', slug='nike')
        self.brand_adidas = Brand.objects.create(name='Adidas', slug='adidas')
        self.category_running = Category.objects.create(name='Running', slug='running')
        self.category_lifestyle = Category.objects.create(name='Lifestyle', slug='lifestyle')

        self.air = self._create_sneaker(
            name='Air Max 97',
            model_number='AM97-001',
            colorway='Silver/Red',
            sku='SKU-AM97-001',
            serial_number='SER-AM97-001',
            description='Iconic full-length Air cushioning.',
            brand=self.brand_nike,
            category=self.category_running,
            price='175.00',
            popularity_score=95,
        )
        SneakerSize.objects.create(
            sneaker=self.air,
            size_system='US',
            size='10',
            stock=4,
        )

        self.ultra = self._create_sneaker(
            name='Ultraboost 23',
            model_number='UB23-001',
            colorway='Black',
            sku='SKU-UB23-001',
            serial_number='SER-UB23-001',
            description='Responsive runner for city miles.',
            brand=self.brand_adidas,
            category=self.category_running,
            price='190.00',
            popularity_score=88,
        )
        SneakerSize.objects.create(
            sneaker=self.ultra,
            size_system='US',
            size='10',
            stock=0,
        )

        self.classic = self._create_sneaker(
            name='City Classic',
            model_number='CC-001',
            colorway='White/Green',
            sku='SKU-CC-001',
            serial_number='SER-CC-001',
            description='Everyday lifestyle comfort.',
            brand=self.brand_nike,
            category=self.category_lifestyle,
            price='110.00',
            popularity_score=70,
        )
        SneakerSize.objects.create(
            sneaker=self.classic,
            size_system='US',
            size='9',
            stock=5,
        )

    def _create_sneaker(self, **kwargs):
        defaults = {
            'is_active': True,
        }
        defaults.update(kwargs)
        return Sneaker.objects.create(**defaults)

    def test_search_matches_name_and_description(self):
        by_name = self.client.get('/api/products/sneakers/?search=air')
        self.assertEqual(by_name.status_code, 200)
        by_name_ids = {row['id'] for row in by_name.data['results']}
        self.assertIn(self.air.id, by_name_ids)

        by_description = self.client.get('/api/products/sneakers/?search=everyday')
        self.assertEqual(by_description.status_code, 200)
        by_description_ids = {row['id'] for row in by_description.data['results']}
        self.assertIn(self.classic.id, by_description_ids)

    def test_brand_and_category_support_multi_select_or(self):
        response = self.client.get(
            f'/api/products/sneakers/?brand={self.brand_nike.id}'
            f'&brand={self.brand_adidas.id}&category={self.category_running.id}'
            f'&category={self.category_lifestyle.id}'
        )
        self.assertEqual(response.status_code, 200)

        result_ids = {row['id'] for row in response.data['results']}
        self.assertTrue({self.air.id, self.ultra.id, self.classic.id}.issubset(result_ids))

    def test_size_filter_uses_repeated_params_and_includes_zero_stock_sizes(self):
        response = self.client.get('/api/products/sneakers/?size=US:10')
        self.assertEqual(response.status_code, 200)

        result_ids = {row['id'] for row in response.data['results']}
        self.assertIn(self.air.id, result_ids)
        self.assertIn(self.ultra.id, result_ids)

    def test_price_filters_and_ordering(self):
        response = self.client.get('/api/products/sneakers/?min_price=120&max_price=200&ordering=price')
        self.assertEqual(response.status_code, 200)

        prices = [float(row['price']) for row in response.data['results']]
        self.assertEqual(prices, sorted(prices))
        self.assertTrue(all(120 <= price <= 200 for price in prices))

        popularity_response = self.client.get('/api/products/sneakers/?ordering=-popularity_score')
        self.assertEqual(popularity_response.status_code, 200)
        self.assertEqual(popularity_response.data['results'][0]['id'], self.air.id)

    def test_pagination_with_filters(self):
        for index in range(25):
            sneaker = self._create_sneaker(
                name=f'Runner {index}',
                model_number=f'R-{index}',
                colorway='Black',
                sku=f'SKU-R-{index}',
                serial_number=f'SER-R-{index}',
                description='High mileage trainer.',
                brand=self.brand_nike,
                category=self.category_running,
                price='130.00',
                popularity_score=20,
            )
            SneakerSize.objects.create(sneaker=sneaker, size_system='US', size='10', stock=3)

        response = self.client.get(f'/api/products/sneakers/?brand={self.brand_nike.id}&page=2')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertGreater(response.data['count'], 20)
        self.assertLessEqual(len(response.data['results']), 20)

    def test_size_options_endpoint_returns_distinct_sizes(self):
        response = self.client.get('/api/products/sizes/options/')
        self.assertEqual(response.status_code, 200)
        self.assertIn({'size_system': 'US', 'size': '10'}, response.data)
        self.assertIn({'size_system': 'US', 'size': '9'}, response.data)


class ProductManagerWorkflowApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.pm_user = user_model.objects.create_user(
            email='pm@example.com',
            username='pm_user',
            first_name='Product',
            last_name='Manager',
            password='StrongPass123!',
            role='product_manager',
        )
        self.customer_user = user_model.objects.create_user(
            email='customer@example.com',
            username='customer_user',
            first_name='Alice',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
        )

        self.brand = Brand.objects.create(name='Jordan', slug='jordan')
        self.category = Category.objects.create(name='Basketball', slug='basketball')

        self.active_sneaker = Sneaker.objects.create(
            brand=self.brand,
            category=self.category,
            name='Court Pro',
            model_number='CP-001',
            colorway='White/Black',
            sku='SKU-CP-001',
            serial_number='SER-CP-001',
            description='Responsive indoor sneaker.',
            price='150.00',
            is_active=True,
        )
        self.inactive_sneaker = Sneaker.objects.create(
            brand=self.brand,
            category=self.category,
            name='Archive Pair',
            model_number='AP-001',
            colorway='Grey',
            sku='SKU-AP-001',
            serial_number='SER-AP-001',
            description='Archived release.',
            price='130.00',
            is_active=False,
        )
        self.sneaker_size = SneakerSize.objects.create(
            sneaker=self.active_sneaker,
            size_system='US',
            size='10',
            stock=6,
        )

        self.pending_review = Review.objects.create(
            sneaker=self.active_sneaker,
            customer=self.customer_user,
            rating=5,
            comment='Great cushioning',
            status='pending',
        )
        self.approved_review = Review.objects.create(
            sneaker=self.inactive_sneaker,
            customer=self.pm_user,
            rating=4,
            comment='Solid pickup',
            status='approved',
        )

    def test_pending_reviews_endpoint_permissions_and_payload(self):
        customer_client = self.client_class()
        customer_client.force_authenticate(self.customer_user)
        customer_response = customer_client.get('/api/products/reviews/pending/')
        self.assertEqual(customer_response.status_code, 403)

        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        response = pm_client.get('/api/products/reviews/pending/')
        self.assertEqual(response.status_code, 200)

        rows = response.data.get('results', response.data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], self.pending_review.id)
        self.assertEqual(rows[0]['status'], 'pending')
        self.assertEqual(rows[0]['sneaker_name'], self.active_sneaker.name)
        self.assertTrue(rows[0]['customer_name'])

    def test_sneaker_size_stock_patch_permissions_and_validation(self):
        customer_client = self.client_class()
        customer_client.force_authenticate(self.customer_user)
        denied = customer_client.patch(
            f'/api/products/sneaker-sizes/{self.sneaker_size.id}/',
            {'stock': 9},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        invalid = pm_client.patch(
            f'/api/products/sneaker-sizes/{self.sneaker_size.id}/',
            {'stock': -1},
            format='json',
        )
        self.assertEqual(invalid.status_code, 400)

        updated = pm_client.patch(
            f'/api/products/sneaker-sizes/{self.sneaker_size.id}/',
            {'stock': 9},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.sneaker_size.refresh_from_db()
        self.assertEqual(self.sneaker_size.stock, 9)

    def test_soft_delete_and_include_inactive_inventory(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        delete_response = pm_client.delete(f'/api/products/sneakers/{self.active_sneaker.id}/')
        self.assertEqual(delete_response.status_code, 204)

        self.active_sneaker.refresh_from_db()
        self.assertFalse(self.active_sneaker.is_active)

        public_response = self.client.get('/api/products/sneakers/')
        self.assertEqual(public_response.status_code, 200)
        public_ids = {row['id'] for row in public_response.data['results']}
        self.assertNotIn(self.active_sneaker.id, public_ids)
        self.assertNotIn(self.inactive_sneaker.id, public_ids)

        pm_inventory = pm_client.get('/api/products/sneakers/?include_inactive=true')
        self.assertEqual(pm_inventory.status_code, 200)
        inventory_ids = {row['id'] for row in pm_inventory.data['results']}
        self.assertIn(self.active_sneaker.id, inventory_ids)
        self.assertIn(self.inactive_sneaker.id, inventory_ids)

    def test_review_create_and_moderation_regression(self):
        review_sneaker = Sneaker.objects.create(
            brand=self.brand,
            category=self.category,
            name='Daily Trainer',
            model_number='DT-001',
            colorway='Blue/White',
            sku='SKU-DT-001',
            serial_number='SER-DT-001',
            description='Versatile running shoe.',
            price='120.00',
            is_active=True,
        )
        SneakerSize.objects.create(
            sneaker=review_sneaker,
            size_system='US',
            size='9',
            stock=3,
        )

        customer_client = self.client_class()
        customer_client.force_authenticate(self.customer_user)
        create_response = customer_client.post(
            f'/api/products/sneakers/{review_sneaker.id}/reviews/create/',
            {'rating': 4, 'comment': 'Good comfort'},
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data['status'], 'pending')

        review_id = create_response.data['id']
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        moderate_response = pm_client.patch(
            f'/api/products/reviews/{review_id}/moderate/',
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(moderate_response.status_code, 200)
        self.assertEqual(moderate_response.data['status'], 'approved')

        public_reviews = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/reviews/')
        self.assertEqual(public_reviews.status_code, 200)
        public_review_ids = {row['id'] for row in public_reviews.data.get('results', public_reviews.data)}
        self.assertIn(review_id, public_review_ids)
