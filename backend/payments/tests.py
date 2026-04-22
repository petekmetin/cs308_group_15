from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class PaymentVerifyTests(APITestCase):
    """
    Tests for POST /api/payments/verify/ (mock banking endpoint).
    """

    def setUp(self):
        self.customer = get_user_model().objects.create_user(
            email='pay-customer@test.com',
            username='pay_customer',
            first_name='Pay',
            last_name='Customer',
            password='StrongPass123!',
            role='customer',
        )
        self.client.force_authenticate(self.customer)

        self.valid_payload = {
            'card_number':  '4111111111111111',
            'expiry_month': '12',
            'expiry_year':  '28',
            'cvv':          '123',
            'amount':       '150.00',
        }

    # ── Authentication ──────────────────────────────────────────────────

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/payments/verify/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, 401)

    # ── Happy path ──────────────────────────────────────────────────────

    def test_valid_card_returns_approved_true(self):
        response = self.client.post('/api/payments/verify/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['approved'])

    def test_valid_card_response_includes_transaction_id(self):
        response = self.client.post('/api/payments/verify/', self.valid_payload, format='json')
        self.assertIn('transaction_id', response.data)
        self.assertTrue(response.data['transaction_id'].startswith('TXN-'))

    def test_each_call_returns_unique_transaction_id(self):
        r1 = self.client.post('/api/payments/verify/', self.valid_payload, format='json')
        r2 = self.client.post('/api/payments/verify/', self.valid_payload, format='json')
        self.assertNotEqual(r1.data['transaction_id'], r2.data['transaction_id'])

    def test_response_includes_correct_last4(self):
        response = self.client.post('/api/payments/verify/', self.valid_payload, format='json')
        self.assertEqual(response.data['last4'], '1111')

    def test_card_number_with_spaces_is_accepted(self):
        """Spaces in the card number should be stripped before validation."""
        payload = {**self.valid_payload, 'card_number': '4111 1111 1111 1111'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['approved'])
        self.assertEqual(response.data['last4'], '1111')

    def test_minimum_length_card_accepted(self):
        """13-digit card (minimum valid length) should be accepted."""
        payload = {**self.valid_payload, 'card_number': '4111111111111'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['approved'])

    def test_minimum_length_cvv_accepted(self):
        """3-digit CVV (standard) should be accepted."""
        payload = {**self.valid_payload, 'cvv': '123'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 200)

    def test_four_digit_cvv_accepted(self):
        """4-digit CVV (Amex style) should also be accepted."""
        payload = {**self.valid_payload, 'cvv': '1234'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 200)

    # ── Card number edge cases ──────────────────────────────────────────

    def test_card_number_too_short_rejected(self):
        """Card numbers shorter than 13 digits are rejected."""
        payload = {**self.valid_payload, 'card_number': '411111111111'}  # 12 digits
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['approved'])
        self.assertIn('reason', response.data)

    def test_empty_card_number_rejected(self):
        payload = {**self.valid_payload, 'card_number': ''}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['approved'])

    def test_missing_card_number_rejected(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != 'card_number'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    # ── Expiry edge cases ───────────────────────────────────────────────

    def test_missing_expiry_month_rejected(self):
        payload = {**self.valid_payload, 'expiry_month': ''}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['approved'])

    def test_missing_expiry_year_rejected(self):
        payload = {**self.valid_payload, 'expiry_year': ''}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['approved'])

    def test_missing_both_expiry_fields_rejected(self):
        payload = {k: v for k, v in self.valid_payload.items()
                   if k not in ('expiry_month', 'expiry_year')}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    # ── CVV edge cases ──────────────────────────────────────────────────

    def test_cvv_too_short_rejected(self):
        """CVV shorter than 3 characters is rejected."""
        payload = {**self.valid_payload, 'cvv': '12'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['approved'])

    def test_empty_cvv_rejected(self):
        payload = {**self.valid_payload, 'cvv': ''}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_missing_cvv_rejected(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != 'cvv'}
        response = self.client.post('/api/payments/verify/', payload, format='json')
        self.assertEqual(response.status_code, 400)
