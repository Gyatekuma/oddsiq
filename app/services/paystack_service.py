"""Paystack payment integration service."""
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class PaystackService:
    """Service for Paystack payment operations."""

    def __init__(self):
        self.secret_key = current_app.config['PAYSTACK_SECRET_KEY']
        self.base_url = current_app.config['PAYSTACK_BASE_URL']
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method, endpoint, data=None):
        """Make a request to the Paystack API."""
        if not self.secret_key:
            logger.warning('Paystack secret key not configured')
            return {'success': False, 'message': 'Payment service not configured'}

        try:
            url = f'{self.base_url}/{endpoint}'

            if method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            else:
                return {'success': False, 'message': 'Invalid HTTP method'}

            response.raise_for_status()
            result = response.json()

            if result.get('status'):
                return {
                    'success': True,
                    **result.get('data', {})
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Unknown error')
                }

        except requests.RequestException as e:
            logger.error(f'Paystack request failed: {e}')
            return {'success': False, 'message': str(e)}

    def initialize_transaction(self, email, amount, metadata=None, callback_url=None):
        """
        Initialize a Paystack transaction.

        Args:
            email: Customer email
            amount: Amount in pesewas (GHS * 100)
            metadata: Additional data to attach to transaction
            callback_url: URL to redirect after payment

        Returns:
            dict: {
                'success': bool,
                'authorization_url': str (redirect URL),
                'access_code': str,
                'reference': str
            }
        """
        data = {
            'email': email,
            'amount': amount,  # Amount in pesewas
            'currency': 'GHS',
            'metadata': metadata or {}
        }

        if callback_url:
            data['callback_url'] = callback_url

        result = self._make_request('POST', 'transaction/initialize', data)

        if result.get('success'):
            logger.info(f'Initialized transaction for {email}, reference: {result.get("reference")}')
        else:
            logger.error(f'Failed to initialize transaction: {result.get("message")}')

        return result

    def verify_transaction(self, reference):
        """
        Verify a Paystack transaction.

        Args:
            reference: Transaction reference from initialization

        Returns:
            dict: {
                'success': bool,
                'status': str (success, failed, etc.),
                'amount': int,
                'metadata': dict,
                'customer': dict
            }
        """
        result = self._make_request('GET', f'transaction/verify/{reference}')

        if result.get('success'):
            # Check transaction status
            status = result.get('status')
            if status == 'success':
                logger.info(f'Transaction {reference} verified successfully')
                return {
                    'success': True,
                    'status': status,
                    'amount': result.get('amount'),
                    'metadata': result.get('metadata', {}),
                    'customer': result.get('customer', {})
                }
            else:
                logger.warning(f'Transaction {reference} status: {status}')
                return {
                    'success': False,
                    'message': f'Transaction status: {status}'
                }

        return result

    def get_transaction(self, transaction_id):
        """Get details of a specific transaction."""
        return self._make_request('GET', f'transaction/{transaction_id}')

    def list_transactions(self, per_page=50, page=1):
        """List all transactions."""
        return self._make_request('GET', f'transaction?perPage={per_page}&page={page}')

    def create_subscription_plan(self, name, amount, interval='monthly'):
        """
        Create a subscription plan.

        Args:
            name: Plan name
            amount: Amount in pesewas
            interval: 'daily', 'weekly', 'monthly', 'annually'

        Returns:
            dict with plan details
        """
        data = {
            'name': name,
            'amount': amount,
            'interval': interval,
            'currency': 'GHS'
        }

        return self._make_request('POST', 'plan', data)

    def charge_authorization(self, email, amount, authorization_code, metadata=None):
        """
        Charge a previously authorized card.

        Args:
            email: Customer email
            amount: Amount in pesewas
            authorization_code: From previous successful transaction
            metadata: Additional data

        Returns:
            dict with transaction result
        """
        data = {
            'email': email,
            'amount': amount,
            'authorization_code': authorization_code,
            'currency': 'GHS',
            'metadata': metadata or {}
        }

        return self._make_request('POST', 'transaction/charge_authorization', data)
