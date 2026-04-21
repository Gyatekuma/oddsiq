"""Custom decorators for route protection."""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def premium_required(fn):
    """
    Decorator that requires user to have premium access.
    Must be used after @jwt_required() decorator.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get('role', 'free')

        if role not in ['premium', 'admin']:
            return jsonify({
                'error': 'Premium subscription required',
                'code': 403
            }), 403

        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    """
    Decorator that requires user to be an admin.
    Must be used after @jwt_required() decorator.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get('role', 'free')

        if role != 'admin':
            return jsonify({
                'error': 'Admin access required',
                'code': 403
            }), 403

        return fn(*args, **kwargs)
    return wrapper
