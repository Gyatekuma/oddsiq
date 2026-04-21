"""Service layer for external API integrations and business logic."""
from .football_service import FootballService
from .odds_service import OddsService
from .basketball_service import BasketballService
from .tennis_service import TennisService
from .prediction_service import PredictionService
from .paystack_service import PaystackService
from .mail_service import MailService

__all__ = [
    'FootballService',
    'OddsService',
    'BasketballService',
    'TennisService',
    'PredictionService',
    'PaystackService',
    'MailService',
]
