"""Prediction model with confidence scores."""
from datetime import datetime
from ..extensions import db


class Prediction(db.Model):
    """Prediction model."""

    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixtures.id'), nullable=False, unique=True, index=True)
    predicted_outcome = db.Column(
        db.Enum('home', 'draw', 'away', name='outcome_type'),
        nullable=False
    )
    confidence_score = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    is_value_bet = db.Column(db.Boolean, default=False, nullable=False)
    expert_note = db.Column(db.Text, nullable=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    accuracy_logs = db.relationship('AccuracyLog', backref='prediction', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, is_premium_user=False):
        """Serialize prediction to dictionary."""
        data = {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'predicted_outcome': self.predicted_outcome,
            'confidence_score': round(self.confidence_score * 100, 1),  # Convert to percentage
            'is_premium': self.is_premium,
            'created_at': self.created_at.isoformat()
        }

        # Premium fields - only include if user has premium access or prediction is not premium
        if is_premium_user or not self.is_premium:
            data['is_value_bet'] = self.is_value_bet
            data['expert_note'] = self.expert_note
        else:
            data['is_value_bet'] = None  # Hidden for free users
            data['expert_note'] = None  # Hidden for free users

        return data

    def to_dict_full(self):
        """Serialize prediction with all fields (for admin)."""
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'predicted_outcome': self.predicted_outcome,
            'confidence_score': round(self.confidence_score * 100, 1),
            'is_value_bet': self.is_value_bet,
            'expert_note': self.expert_note,
            'is_premium': self.is_premium,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Prediction fixture_id={self.fixture_id} outcome={self.predicted_outcome}>'
