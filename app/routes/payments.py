"""Payment routes with Paystack integration."""
from datetime import datetime, timedelta
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.user import User
from ..models.subscription import Subscription
from ..services.paystack_service import PaystackService
from ..utils.helpers import json_error, json_success

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get available subscription plans."""
    monthly_amount = current_app.config['MONTHLY_PLAN_AMOUNT']
    annual_amount = current_app.config['ANNUAL_PLAN_AMOUNT']

    return json_success(data={
        'plans': [
            {
                'id': 'monthly',
                'name': 'Monthly',
                'amount': monthly_amount / 100,
                'currency': 'GHS',
                'interval': 'month',
                'features': [
                    'Unlimited predictions',
                    'Value bet alerts',
                    'Expert analysis',
                    'Priority support'
                ]
            },
            {
                'id': 'annual',
                'name': 'Annual',
                'amount': annual_amount / 100,
                'currency': 'GHS',
                'interval': 'year',
                'features': [
                    'Unlimited predictions',
                    'Value bet alerts',
                    'Expert analysis',
                    'Priority support',
                    '2 months free'
                ]
            }
        ]
    })


@payments_bp.route('/initiate', methods=['POST'])
@jwt_required()
def initiate_payment():
    """Initiate a Paystack payment session."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return json_error('User not found', 404)

    data = request.get_json() or {}
    plan = data.get('plan', 'monthly')

    if plan not in ['monthly', 'annual']:
        return json_error('Invalid plan. Choose monthly or annual.', 400)

    # Get amount based on plan
    if plan == 'monthly':
        amount = current_app.config['MONTHLY_PLAN_AMOUNT']
    else:
        amount = current_app.config['ANNUAL_PLAN_AMOUNT']

    # Initialize Paystack payment
    paystack = PaystackService()
    result = paystack.initialize_transaction(
        email=user.email,
        amount=amount,
        metadata={
            'user_id': user.id,
            'plan': plan
        }
    )

    if not result['success']:
        return json_error(result.get('message', 'Payment initialization failed'), 500)

    return json_success(data={
        'authorization_url': result['authorization_url'],
        'access_code': result['access_code'],
        'reference': result['reference'],
        'plan': plan,
        'amount': amount / 100  # Convert from pesewas to GHS
    })


@payments_bp.route('/verify/<reference>', methods=['GET'])
@jwt_required()
def verify_payment(reference):
    """Verify a Paystack payment and upgrade user to premium."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return json_error('User not found', 404)

    # Verify with Paystack
    paystack = PaystackService()
    result = paystack.verify_transaction(reference)

    if not result['success']:
        return json_error(result.get('message', 'Payment verification failed'), 400)

    # Check if already processed
    existing_sub = Subscription.query.filter_by(paystack_ref=reference).first()
    if existing_sub:
        return json_error('This payment has already been processed', 400)

    # Get plan from metadata
    metadata = result.get('metadata', {})
    plan = metadata.get('plan', 'monthly')

    # Calculate subscription dates
    now = datetime.utcnow()
    if plan == 'monthly':
        ends_at = now + timedelta(days=30)
    else:
        ends_at = now + timedelta(days=365)

    # Create subscription record
    subscription = Subscription(
        user_id=user.id,
        plan=plan,
        paystack_ref=reference,
        starts_at=now,
        ends_at=ends_at
    )
    db.session.add(subscription)

    # Update user role and subscription expiry
    user.role = 'premium'
    user.subscription_expires_at = ends_at
    db.session.commit()

    return json_success(
        data={
            'subscription': subscription.to_dict(),
            'user': user.to_dict(include_email=True)
        },
        message='Payment successful! You are now a premium member.'
    )


@payments_bp.route('/history', methods=['GET'])
@jwt_required()
def payment_history():
    """Get user's payment/subscription history."""
    user_id = get_jwt_identity()

    subscriptions = Subscription.query.filter_by(user_id=user_id).order_by(
        Subscription.created_at.desc()
    ).all()

    return json_success(data={
        'subscriptions': [sub.to_dict() for sub in subscriptions]
    })
