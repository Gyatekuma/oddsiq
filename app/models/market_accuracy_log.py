"""Market accuracy log model for tracking market prediction accuracy."""
from datetime import datetime
from sqlalchemy import func
from ..extensions import db


class MarketAccuracyLog(db.Model):
    """Accuracy log model for tracking market prediction accuracy."""

    __tablename__ = 'market_accuracy_log'

    id = db.Column(db.Integer, primary_key=True)
    market_prediction_id = db.Column(
        db.Integer,
        db.ForeignKey('market_predictions.id'),
        nullable=False,
        unique=True,
        index=True
    )
    actual_outcome = db.Column(db.String(50), nullable=False)
    was_correct = db.Column(db.Boolean, nullable=False)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    prediction = db.relationship('MarketPrediction', backref=db.backref('accuracy_log', uselist=False))

    def to_dict(self):
        """Serialize accuracy log to dictionary."""
        return {
            'id': self.id,
            'market_prediction_id': self.market_prediction_id,
            'actual_outcome': self.actual_outcome,
            'was_correct': self.was_correct,
            'logged_at': self.logged_at.isoformat()
        }

    @staticmethod
    def get_accuracy_stats(market_type=None, sport_id=None):
        """
        Calculate accuracy statistics for market predictions.

        Args:
            market_type: Filter by market type (optional)
            sport_id: Filter by sport (optional)

        Returns dict with total, correct, and percentage.
        """
        from .market_prediction import MarketPrediction
        from .fixture import Fixture
        from .league import League

        query = db.session.query(MarketAccuracyLog)

        if market_type:
            query = query.join(MarketPrediction).filter(
                MarketPrediction.market_type == market_type
            )

        if sport_id:
            query = query.join(MarketPrediction).join(Fixture).join(League).filter(
                League.sport_id == sport_id
            )

        total = query.count()
        correct = query.filter(MarketAccuracyLog.was_correct == True).count()

        return {
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy_percentage': round((correct / total * 100), 2) if total > 0 else 0
        }

    @staticmethod
    def get_accuracy_by_market():
        """Get accuracy breakdown by market type."""
        from .market_prediction import MarketPrediction

        results = db.session.query(
            MarketPrediction.market_type,
            func.count(MarketAccuracyLog.id).label('total'),
            func.sum(
                db.case((MarketAccuracyLog.was_correct == True, 1), else_=0)
            ).label('correct')
        ).join(MarketPrediction).group_by(
            MarketPrediction.market_type
        ).all()

        accuracy_by_market = {}
        for market_type, total, correct in results:
            if total > 0:
                accuracy_by_market[market_type] = {
                    'total': total,
                    'correct': correct,
                    'accuracy': round((correct / total * 100), 1)
                }

        return accuracy_by_market

    @staticmethod
    def get_accuracy_by_confidence_range(market_type=None):
        """Get accuracy breakdown by confidence level."""
        from .market_prediction import MarketPrediction

        ranges = [
            ('high', 0.75, 1.0),
            ('medium', 0.60, 0.75),
            ('low', 0.0, 0.60)
        ]

        results = []
        for label, min_conf, max_conf in ranges:
            query = db.session.query(MarketAccuracyLog).join(MarketPrediction).filter(
                MarketPrediction.confidence_score >= min_conf,
                MarketPrediction.confidence_score < max_conf
            )

            if market_type:
                query = query.filter(MarketPrediction.market_type == market_type)

            total = query.count()
            correct = query.filter(MarketAccuracyLog.was_correct == True).count()

            if total > 0:
                results.append({
                    'level': label,
                    'range': f'{int(min_conf * 100)}-{int(max_conf * 100)}%',
                    'total': total,
                    'correct': correct,
                    'accuracy': round((correct / total * 100), 1)
                })

        return results

    def __repr__(self):
        return f'<MarketAccuracyLog prediction={self.market_prediction_id} correct={self.was_correct}>'
