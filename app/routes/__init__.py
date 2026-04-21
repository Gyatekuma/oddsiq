"""API route blueprints."""
from .auth import auth_bp
from .predictions import predictions_bp
from .fixtures import fixtures_bp
from .odds import odds_bp
from .leagues import leagues_bp
from .guides import guides_bp
from .accuracy import accuracy_bp
from .newsletter import newsletter_bp
from .payments import payments_bp
from .admin import admin_bp
from .market_predictions import market_predictions_bp

__all__ = [
    'auth_bp',
    'predictions_bp',
    'fixtures_bp',
    'odds_bp',
    'leagues_bp',
    'guides_bp',
    'accuracy_bp',
    'newsletter_bp',
    'payments_bp',
    'admin_bp',
    'market_predictions_bp',
]
