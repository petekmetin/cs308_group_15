import tempfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from .models import Brand, Category, Sneaker, SneakerImage, SneakerSize, Wishlist, Review


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

    def test_list_payload_exposes_demo_product_metadata_and_review_summary(self):
        Review.objects.create(
            sneaker=self.air,
            customer=get_user_model().objects.create_user(
                email='rating@example.com',
                username='rating_user',
                first_name='Rating',
                last_name='User',
                password='StrongPass123!',
                role='customer',
            ),
            rating=5,
            comment='Visible catalog comment',
            status='approved',
        )

        response = self.client.get(f'/api/products/sneakers/?search={self.air.name}')
        self.assertEqual(response.status_code, 200)
        row = response.data['results'][0]

        self.assertEqual(row['id'], self.air.id)
        self.assertEqual(row['model_number'], self.air.model_number)
        self.assertEqual(row['category_name'], self.category_running.name)
        self.assertEqual(row['average_rating'], 5.0)
        self.assertEqual(row['rating_count'], 1)
        self.assertEqual(row['latest_approved_comment'], 'Visible catalog comment')

    def test_list_endpoint_keeps_query_count_small_for_review_summary(self):
        Review.objects.create(
            sneaker=self.air,
            customer=get_user_model().objects.create_user(
                email='query-check@example.com',
                username='query_check_user',
                first_name='Query',
                last_name='Check',
                password='StrongPass123!',
                role='customer',
            ),
            rating=4,
            comment='Query check comment',
            status='approved',
        )
        image_buffer = BytesIO()
        Image.new('RGB', (2, 2), color=(25, 90, 200)).save(image_buffer, format='PNG')
        SneakerImage.objects.create(
            sneaker=self.air,
            image=SimpleUploadedFile(
                'air-max.png',
                image_buffer.getvalue(),
                content_type='image/png',
            ),
            alt_text='Air Max image',
            is_primary=True,
            order=0,
        )

        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(f'/api/products/sneakers/?search={self.air.name}')

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(captured), 3)


class DemoFlowCommandTests(APITestCase):
    def test_prepare_demo_flow_creates_deterministic_stock_examples_idempotently(self):
        call_command('prepare_demo_flow')
        call_command('prepare_demo_flow')

        products = {
            sneaker.sku: sneaker
            for sneaker in Sneaker.objects.filter(
                sku__in=['DEMO-PRODUCT-A', 'DEMO-PRODUCT-B', 'DEMO-PRODUCT-C']
            ).prefetch_related('sizes')
        }

        self.assertEqual(set(products), {'DEMO-PRODUCT-A', 'DEMO-PRODUCT-B', 'DEMO-PRODUCT-C'})
        self.assertEqual(products['DEMO-PRODUCT-A'].total_stock, 0)
        self.assertFalse(products['DEMO-PRODUCT-A'].is_in_stock)
        self.assertEqual(products['DEMO-PRODUCT-B'].total_stock, 1)
        self.assertTrue(products['DEMO-PRODUCT-B'].is_in_stock)
        self.assertGreater(products['DEMO-PRODUCT-C'].total_stock, 1)
        self.assertTrue(products['DEMO-PRODUCT-C'].is_in_stock)

        self.assertEqual(
            SneakerSize.objects.filter(sneaker__sku__in=products.keys()).count(),
            3,
        )


class ProductManagerWorkflowApiTests(APITestCase):
    def setUp(self):
        self._media_dir = tempfile.TemporaryDirectory()
        self._media_override = override_settings(MEDIA_ROOT=self._media_dir.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(self._media_dir.cleanup)

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
        self.second_customer_user = user_model.objects.create_user(
            email='customer2@example.com',
            username='customer_user_2',
            first_name='Bob',
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
        self.rejected_review = Review.objects.create(
            sneaker=self.active_sneaker,
            customer=self.second_customer_user,
            rating=2,
            comment='Not for me',
            status='rejected',
        )

    def _sample_png(self, name='sample.png'):
        buffer = BytesIO()
        Image.new('RGB', (2, 2), color=(12, 120, 210)).save(buffer, format='PNG')
        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type='image/png',
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

    def test_review_management_list_filter_delete_and_clear_rejected(self):
        customer_client = self.client_class()
        customer_client.force_authenticate(self.customer_user)
        customer_denied = customer_client.get('/api/products/reviews/')
        self.assertEqual(customer_denied.status_code, 403)

        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        all_reviews = pm_client.get('/api/products/reviews/')
        self.assertEqual(all_reviews.status_code, 200)
        rows = all_reviews.data.get('results', all_reviews.data)
        self.assertEqual(len(rows), 3)

        pending_reviews = pm_client.get('/api/products/reviews/?status=pending')
        self.assertEqual(pending_reviews.status_code, 200)
        pending_rows = pending_reviews.data.get('results', pending_reviews.data)
        self.assertEqual({row['status'] for row in pending_rows}, {'pending'})
        self.assertEqual({row['id'] for row in pending_rows}, {self.pending_review.id})

        rejected_reviews = pm_client.get('/api/products/reviews/?status=rejected')
        self.assertEqual(rejected_reviews.status_code, 200)
        rejected_rows = rejected_reviews.data.get('results', rejected_reviews.data)
        self.assertEqual({row['id'] for row in rejected_rows}, {self.rejected_review.id})

        deleted = pm_client.delete(f'/api/products/reviews/{self.approved_review.id}/')
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Review.objects.filter(id=self.approved_review.id).exists())

        cleared = pm_client.delete('/api/products/reviews/rejected/clear/')
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(cleared.data['deleted_count'], 1)
        self.assertFalse(Review.objects.filter(id=self.rejected_review.id).exists())

    def test_category_and_brand_patch_editing_and_unique_validation(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        category_update = pm_client.patch(
            f'/api/products/categories/{self.category.id}/',
            {'name': 'Basketball Updated', 'slug': 'basketball-updated', 'description': 'Updated'},
            format='json',
        )
        self.assertEqual(category_update.status_code, 200)
        self.category.refresh_from_db()
        self.assertEqual(self.category.slug, 'basketball-updated')

        second_category = Category.objects.create(name='Running', slug='running')
        duplicate_category = pm_client.patch(
            f'/api/products/categories/{second_category.id}/',
            {'slug': 'basketball-updated'},
            format='json',
        )
        self.assertEqual(duplicate_category.status_code, 400)

        brand_update = pm_client.patch(
            f'/api/products/brands/{self.brand.id}/',
            {'name': 'Jordan Updated', 'slug': 'jordan-updated', 'description': 'Updated brand'},
            format='json',
        )
        self.assertEqual(brand_update.status_code, 200)
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.slug, 'jordan-updated')

        second_brand = Brand.objects.create(name='Nike', slug='nike')
        duplicate_brand = pm_client.patch(
            f'/api/products/brands/{second_brand.id}/',
            {'slug': 'jordan-updated'},
            format='json',
        )
        self.assertEqual(duplicate_brand.status_code, 400)

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

    def test_sneaker_size_create_and_duplicate_validation(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        created = pm_client.post(
            '/api/products/sneaker-sizes/',
            {
                'sneaker_id': self.active_sneaker.id,
                'size_system': 'EU',
                'size': '42',
                'stock': 5,
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['size_system'], 'EU')
        self.assertEqual(created.data['size'], '42')

        duplicate = pm_client.post(
            '/api/products/sneaker-sizes/',
            {
                'sneaker_id': self.active_sneaker.id,
                'size_system': 'EU',
                'size': '42',
                'stock': 7,
            },
            format='json',
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_product_manager_can_toggle_active_state_via_patch(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        deactivated = pm_client.patch(
            f'/api/products/sneakers/{self.active_sneaker.id}/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(deactivated.status_code, 200)
        self.active_sneaker.refresh_from_db()
        self.assertFalse(self.active_sneaker.is_active)

        activated = pm_client.patch(
            f'/api/products/sneakers/{self.active_sneaker.id}/',
            {'is_active': True},
            format='json',
        )
        self.assertEqual(activated.status_code, 200)
        self.active_sneaker.refresh_from_db()
        self.assertTrue(self.active_sneaker.is_active)

    def test_product_manager_cannot_patch_pricing_fields(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        denied = pm_client.patch(
            f'/api/products/sneakers/{self.active_sneaker.id}/',
            {'discount_percentage': '15.00', 'price': '200.00'},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)
        self.active_sneaker.refresh_from_db()
        self.assertEqual(str(self.active_sneaker.price), '150.00')
        self.assertEqual(str(self.active_sneaker.discount_percentage), '0.00')

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

    def test_image_upload_primary_switch_and_delete_fallback(self):
        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)

        first = pm_client.post(
            f'/api/products/sneakers/{self.active_sneaker.id}/images/',
            {'image': self._sample_png('first.png'), 'is_primary': True, 'order': 0},
            format='multipart',
        )
        self.assertEqual(first.status_code, 201)

        second = pm_client.post(
            f'/api/products/sneakers/{self.active_sneaker.id}/images/',
            {'image': self._sample_png('second.png'), 'is_primary': False, 'order': 1},
            format='multipart',
        )
        self.assertEqual(second.status_code, 201)

        first_image = SneakerImage.objects.get(pk=first.data['id'])
        second_image = SneakerImage.objects.get(pk=second.data['id'])
        self.assertTrue(first_image.is_primary)
        self.assertFalse(second_image.is_primary)

        promote = pm_client.patch(
            f'/api/products/sneaker-images/{second_image.id}/',
            {'is_primary': True},
            format='json',
        )
        self.assertEqual(promote.status_code, 200)
        first_image.refresh_from_db()
        second_image.refresh_from_db()
        self.assertFalse(first_image.is_primary)
        self.assertTrue(second_image.is_primary)

        removed = pm_client.delete(f'/api/products/sneaker-images/{second_image.id}/')
        self.assertEqual(removed.status_code, 204)
        first_image.refresh_from_db()
        self.assertTrue(first_image.is_primary)

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

    def test_rating_is_immediate_but_comments_require_moderation(self):
        review_sneaker = Sneaker.objects.create(
            brand=self.brand,
            category=self.category,
            name='Review Flow Trainer',
            model_number='RFT-001',
            colorway='Blue/White',
            sku='SKU-RFT-001',
            serial_number='SER-RFT-001',
            description='Review flow test shoe.',
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

        rating_response = customer_client.post(
            f'/api/products/sneakers/{review_sneaker.id}/reviews/create/',
            {'rating': 5},
            format='json',
        )
        self.assertEqual(rating_response.status_code, 201)

        detail_after_rating = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/')
        self.assertEqual(detail_after_rating.status_code, 200)
        self.assertEqual(detail_after_rating.data['average_rating'], 5.0)
        self.assertEqual(detail_after_rating.data['rating_count'], 1)

        public_reviews = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/reviews/')
        self.assertEqual(public_reviews.status_code, 200)
        self.assertEqual(public_reviews.data.get('results', public_reviews.data), [])

        comment_response = customer_client.post(
            f'/api/products/sneakers/{review_sneaker.id}/reviews/create/',
            {'rating': 4, 'comment': 'Needs moderation first'},
            format='json',
        )
        self.assertEqual(comment_response.status_code, 200)
        self.assertEqual(comment_response.data['status'], 'pending')

        detail_after_update = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/')
        self.assertEqual(detail_after_update.data['average_rating'], 4.0)
        self.assertEqual(detail_after_update.data['rating_count'], 1)

        public_reviews = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/reviews/')
        self.assertEqual(public_reviews.status_code, 200)
        self.assertEqual(public_reviews.data.get('results', public_reviews.data), [])

        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        approve_response = pm_client.patch(
            f'/api/products/reviews/{comment_response.data["id"]}/moderate/',
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(approve_response.status_code, 200)

        public_reviews = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/reviews/')
        self.assertEqual(public_reviews.status_code, 200)
        rows = public_reviews.data.get('results', public_reviews.data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['comment'], 'Needs moderation first')

    def test_rejected_comment_stays_hidden_while_rating_remains_counted(self):
        review_sneaker = Sneaker.objects.create(
            brand=self.brand,
            category=self.category,
            name='Rejected Comment Trainer',
            model_number='RCT-001',
            colorway='Grey',
            sku='SKU-RCT-001',
            serial_number='SER-RCT-001',
            description='Rejected comment flow test shoe.',
            price='125.00',
            is_active=True,
        )

        customer_client = self.client_class()
        customer_client.force_authenticate(self.customer_user)
        create_response = customer_client.post(
            f'/api/products/sneakers/{review_sneaker.id}/reviews/create/',
            {'rating': 3, 'comment': 'Do not publish this'},
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)

        pm_client = self.client_class()
        pm_client.force_authenticate(self.pm_user)
        reject_response = pm_client.patch(
            f'/api/products/reviews/{create_response.data["id"]}/moderate/',
            {'status': 'rejected'},
            format='json',
        )
        self.assertEqual(reject_response.status_code, 200)

        detail = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/')
        self.assertEqual(detail.data['average_rating'], 3.0)
        self.assertEqual(detail.data['rating_count'], 1)

        public_reviews = self.client.get(f'/api/products/sneakers/{review_sneaker.id}/reviews/')
        self.assertEqual(public_reviews.status_code, 200)
        self.assertEqual(public_reviews.data.get('results', public_reviews.data), [])


class SalesManagerPricingApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.sales_manager = user_model.objects.create_user(
            email='sales@example.com',
            username='sales_user',
            first_name='Sales',
            last_name='Manager',
            password='StrongPass123!',
            role='sales_manager',
        )
        self.product_manager = user_model.objects.create_user(
            email='product-pricing@example.com',
            username='product_pricing',
            first_name='Product',
            last_name='Manager',
            password='StrongPass123!',
            role='product_manager',
        )
        self.customer = user_model.objects.create_user(
            email='wishlist-customer@example.com',
            username='wishlist_customer',
            first_name='Wishlist',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
        )

        brand = Brand.objects.create(name='Puma', slug='puma')
        category = Category.objects.create(name='Training', slug='training')
        self.sneaker = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Velocity Pro',
            model_number='VP-001',
            colorway='White/Blue',
            sku='SKU-VP-001',
            serial_number='SER-VP-001',
            description='Versatile training pair.',
            price='120.00',
            discount_percentage='5.00',
            is_active=True,
        )
        self.second_sneaker = Sneaker.objects.create(
            brand=brand,
            category=category,
            name='Velocity Max',
            model_number='VM-002',
            colorway='Black/Blue',
            sku='SKU-VM-002',
            serial_number='SER-VM-002',
            description='Stable training pair.',
            price='150.00',
            discount_percentage='0.00',
            is_active=True,
        )
        Wishlist.objects.create(customer=self.customer, sneaker=self.sneaker)
        Wishlist.objects.create(customer=self.customer, sneaker=self.second_sneaker)

        self.client.force_authenticate(self.sales_manager)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='sales@solevault.test',
    )
    def test_sales_manager_set_price_sends_discount_email_to_wishlist_customers(self):
        response = self.client.patch(
            f'/api/products/sneakers/{self.sneaker.id}/set-price/',
            {'price': '120.00', 'discount_percentage': '20.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['notification_count'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.customer.email])
        self.assertIn(self.sneaker.name, mail.outbox[0].subject)
        self.sneaker.refresh_from_db()
        self.assertEqual(str(self.sneaker.discount_percentage), '20.00')

    def test_set_price_rejects_non_sales_manager(self):
        self.client.force_authenticate(self.product_manager)
        response = self.client.patch(
            f'/api/products/sneakers/{self.sneaker.id}/set-price/',
            {'price': '99.00', 'discount_percentage': '10.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(self.customer)
        customer_response = self.client.patch(
            f'/api/products/sneakers/{self.sneaker.id}/set-price/',
            {'price': '99.00', 'discount_percentage': '10.00'},
            format='json',
        )
        self.assertEqual(customer_response.status_code, 403)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='sales@solevault.test',
    )
    def test_batch_discount_updates_products_and_reports_notification_count(self):
        response = self.client.patch(
            '/api/products/sneakers/batch-discount/',
            {
                'product_ids': [self.sneaker.id, self.second_sneaker.id],
                'discount_percentage': '15.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(response.data['notification_count'], 2)
        self.assertEqual(len(mail.outbox), 2)
        self.sneaker.refresh_from_db()
        self.second_sneaker.refresh_from_db()
        self.assertEqual(str(self.sneaker.discount_percentage), '15.00')
        self.assertEqual(str(self.second_sneaker.discount_percentage), '15.00')

    def test_batch_discount_validates_empty_product_list(self):
        response = self.client.patch(
            '/api/products/sneakers/batch-discount/',
            {'product_ids': [], 'discount_percentage': '15.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('product_ids', response.data)

    def test_batch_discount_rejects_invalid_ids(self):
        response = self.client.patch(
            '/api/products/sneakers/batch-discount/',
            {'product_ids': [self.sneaker.id, 999999], 'discount_percentage': '15.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('product_ids', response.data)

    def test_batch_discount_rejects_discount_above_hundred(self):
        response = self.client.patch(
            '/api/products/sneakers/batch-discount/',
            {'product_ids': [self.sneaker.id], 'discount_percentage': '101'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('discount_percentage', response.data)

    @patch('products.views.send_discount_email', side_effect=RuntimeError('SMTP unavailable'))
    def test_batch_discount_keeps_price_changes_when_notification_fails(self, _send):
        with self.assertLogs('products.views', level='ERROR'):
            response = self.client.patch(
                '/api/products/sneakers/batch-discount/',
                {'product_ids': [self.sneaker.id], 'discount_percentage': '25.00'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated_count'], 1)
        self.assertEqual(response.data['notification_count'], 0)
        self.assertEqual(response.data['failed_notification_count'], 1)
        self.sneaker.refresh_from_db()
        self.assertEqual(str(self.sneaker.discount_percentage), '25.00')

    def test_set_price_rejects_non_numeric_discount(self):
        response = self.client.patch(
            f'/api/products/sneakers/{self.sneaker.id}/set-price/',
            {'discount_percentage': 'abc'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('discount_percentage', response.data)

    def test_set_price_rejects_discount_above_hundred(self):
        response = self.client.patch(
            f'/api/products/sneakers/{self.sneaker.id}/set-price/',
            {'discount_percentage': '101'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('discount_percentage', response.data)

    def test_set_price_rejects_negative_price(self):
        response = self.client.patch(
            f'/api/products/sneakers/{self.sneaker.id}/set-price/',
            {'price': '-1.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.data)
