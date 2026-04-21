"""Market prediction model for multiple betting markets."""
from datetime import datetime
from ..extensions import db


class MarketPrediction(db.Model):
    """
    Market prediction model supporting multiple betting markets.

    Market types:
    - match_winner: Traditional 1X2 (home/draw/away)
    - over_under: Over/Under goals (with line_value like 2.5)
    - double_chance: 1X, X2, 12
    - btts: Both Teams To Score (yes/no)
    - corners: Corners Over/Under
    - ht_ft: Half-time/Full-time
    """

    __tablename__ = 'market_predictions'

    id = db.Column(db.Integer, primary_key=True)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixtures.id'), nullable=False, index=True)
    market_type = db.Column(db.String(50), nullable=False, index=True)

    # Flexible outcome storage
    # Examples: 'over', 'under', 'yes', 'no', '1X', 'X2', '12', 'home_home', etc.
    predicted_outcome = db.Column(db.String(50), nullable=False)

    # Line value for Over/Under markets (e.g., 2.5, 1.5, 0.5)
    line_value = db.Column(db.Float, nullable=True)

    # Confidence and probability
    confidence_score = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    model_probability = db.Column(db.Float, nullable=True)  # Calculated probability

    # Value bet detection
    is_value_bet = db.Column(db.Boolean, default=False, nullable=False)
    value_edge = db.Column(db.Float, nullable=True)  # model_prob - implied_prob

    # Additional info
    expert_note = db.Column(db.Text, nullable=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    fixture = db.relationship('Fixture', backref=db.backref('market_predictions', lazy='dynamic'))

    # Unique constraint: one prediction per fixture/market/line/outcome combination
    # This allows storing multiple outcomes (e.g., both 'over' and 'under') for the same market
    __table_args__ = (
        db.UniqueConstraint('fixture_id', 'market_type', 'line_value', 'predicted_outcome', name='uix_fixture_market_line_outcome'),
        db.Index('ix_market_prediction_lookup', 'fixture_id', 'market_type'),
    )

    def to_dict(self, is_premium_user=False):
        """Serialize market prediction to dictionary."""
        data = {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'market_type': self.market_type,
            'predicted_outcome': self.predicted_outcome,
            'line_value': self.line_value,
            'confidence_score': round(self.confidence_score * 100, 1),  # As percentage
            'is_premium': self.is_premium,
            'created_at': self.created_at.isoformat()
        }

        # Premium-only fields
        if is_premium_user or not self.is_premium:
            data['is_value_bet'] = self.is_value_bet
            data['value_edge'] = round(self.value_edge * 100, 2) if self.value_edge else None
            data['expert_note'] = self.expert_note
            data['model_probability'] = round(self.model_probability * 100, 1) if self.model_probability else None
        else:
            # Hide premium fields for free users
            data['is_value_bet'] = None
            data['value_edge'] = None
            data['expert_note'] = None
            data['model_probability'] = None

        return data

    def to_dict_full(self):
        """Full serialization including all fields."""
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'market_type': self.market_type,
            'predicted_outcome': self.predicted_outcome,
            'line_value': self.line_value,
            'confidence_score': round(self.confidence_score * 100, 1),
            'model_probability': round(self.model_probability * 100, 1) if self.model_probability else None,
            'is_value_bet': self.is_value_bet,
            'value_edge': round(self.value_edge * 100, 2) if self.value_edge else None,
            'expert_note': self.expert_note,
            'is_premium': self.is_premium,
            'created_at': self.created_at.isoformat()
        }

    @staticmethod
    def get_market_display_name(market_type):
        """Get human-readable market name."""
        display_names = {
            'match_winner': 'Match Winner (1X2)',
            'over_under': 'Over/Under Goals',
            'double_chance': 'Double Chance',
            'btts': 'Both Teams To Score',
            'corners': 'Corners Over/Under',
            'ht_ft': 'Half-time/Full-time'
        }
        return display_names.get(market_type, market_type)

    @staticmethod
    def get_outcome_display(market_type, outcome, line_value=None):
        """Get human-readable outcome name."""
        if market_type == 'over_under':
            return f"{'Over' if outcome == 'over' else 'Under'} {line_value}"
        elif market_type == 'btts':
            return 'Yes' if outcome == 'yes' else 'No'
        elif market_type == 'double_chance':
            dc_names = {'1X': 'Home or Draw', 'X2': 'Draw or Away', '12': 'Home or Away'}
            return dc_names.get(outcome, outcome)
        elif market_type == 'corners':
            return f"{'Over' if outcome == 'over' else 'Under'} {line_value} Corners"
        elif market_type == 'ht_ft':
            ht, ft = outcome.split('_')
            names = {'home': 'Home', 'draw': 'Draw', 'away': 'Away'}
            return f"{names.get(ht, ht)}/{names.get(ft, ft)}"
        return outcome

    def __repr__(self):
        return f'<MarketPrediction {self.market_type}:{self.predicted_outcome} fixture={self.fixture_id}>'
