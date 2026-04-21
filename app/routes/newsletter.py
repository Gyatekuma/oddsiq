"""Newsletter subscription routes."""
from flask import Blueprint, request
from ..extensions import db, limiter
from ..models.newsletter import Newsletter
from ..utils.helpers import json_error, json_success, validate_email

newsletter_bp = Blueprint('newsletter', __name__)


@newsletter_bp.route('/subscribe', methods=['POST'])
@limiter.limit('5 per minute')
def subscribe():
    """Subscribe to the newsletter."""
    data = request.get_json()

    if not data:
        return json_error('No data provided', 400)

    email = data.get('email', '').strip().lower()

    if not email or not validate_email(email):
        return json_error('Invalid email address', 400)

    # Check if already subscribed
    existing = Newsletter.query.filter_by(email=email).first()

    if existing:
        if existing.active:
            return json_error('Email already subscribed', 409)
        else:
            # Reactivate subscription
            existing.resubscribe()
            return json_success(message='Successfully resubscribed to newsletter')

    # Create new subscription
    subscriber = Newsletter(email=email)
    db.session.add(subscriber)
    db.session.commit()

    return json_success(
        message='Successfully subscribed to newsletter',
        code=201
    )


@newsletter_bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe from the newsletter."""
    data = request.get_json()

    if not data:
        return json_error('No data provided', 400)

    email = data.get('email', '').strip().lower()

    if not email:
        return json_error('Email required', 400)

    subscriber = Newsletter.query.filter_by(email=email).first()

    if not subscriber:
        return json_error('Email not found', 404)

    if not subscriber.active:
        return json_error('Already unsubscribed', 400)

    subscriber.unsubscribe()

    return json_success(message='Successfully unsubscribed from newsletter')
