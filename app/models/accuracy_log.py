"""Accuracy log model for prediction tracking."""
from datetime import datetime
from ..extensions import db


class AccuracyLog(db.Model):
    """Accuracy log model for tracking prediction accuracy."""

    __tablename__ = 'accuracy_log'

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=False, unique=True, index=True)
    actual_outcome = db.Column(
        db.Enum('home', 'draw', 'away', name='actual_outcome_type'),
        nullable=False
    )
    was_correct = db.Column(db.Boolean, nullable=False)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Serialize accuracy log to dictionary."""
        return {
            'id': self.id,
            'prediction_id': self.prediction_id,
            'actual_outcome': self.actual_outcome,
            'was_correct': self.was_correct,
            'logged_at': self.logged_at.isoformat()
        }

    @staticmethod
    def get_accuracy_stats(sport_id=None):
        """
        Calculate accuracy statistics.
        Returns overall and per-sport accuracy.
        """
        from .prediction import Prediction
        from .fixture import Fixture
        from .league import League

        query = db.session.query(AccuracyLog)

        if sport_id:
            query = query.join(Prediction).join(Fixture).join(League).filter(
                League.sport_id == sport_id
            )

        total = query.count()
        correct = query.filter(AccuracyLog.was_correct == True).count()

        return {
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy_percentage': round((correct / total * 100), 2) if total > 0 else 0
        }

    def __repr__(self):
        return f'<AccuracyLog prediction_id={self.prediction_id} correct={self.was_correct}>'
