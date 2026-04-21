from rest_framework.test import APITestCase

from .models import Brand, Category, Sneaker, SneakerSize


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
