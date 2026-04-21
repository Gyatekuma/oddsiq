"""Shared utility functions."""
import re
from datetime import datetime, timedelta
from flask import jsonify


def json_error(message, code=400):
    """Return a standardized JSON error response."""
    return jsonify({
        'error': message,
        'code': code
    }), code


def json_success(data=None, message=None, code=200):
    """Return a standardized JSON success response."""
    response = {}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    return jsonify(response), code


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def get_date_range(date_str):
    """
    Parse date string and return start/end datetime range.
    Supports: 'today', 'tomorrow', 'YYYY-MM-DD'
    Returns tuple of (start_datetime, end_datetime)
    """
    if date_str == 'today':
        date = datetime.utcnow().date()
    elif date_str == 'tomorrow':
        date = (datetime.utcnow() + timedelta(days=1)).date()
    else:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, None

    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    return start, end


def parse_sport_filter(sport_str):
    """Parse and validate sport filter."""
    valid_sports = ['football', 'basketball', 'tennis']
    if sport_str and sport_str.lower() in valid_sports:
        return sport_str.lower()
    return None


def calculate_pagination(page, per_page, total):
    """Calculate pagination metadata."""
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1
    }


def format_currency(amount_pesewas, currency='GHS'):
    """Format amount from pesewas to currency string."""
    amount = amount_pesewas / 100
    return f'{currency} {amount:.2f}'
