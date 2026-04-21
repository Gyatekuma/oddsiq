"""Fixture model."""
from datetime import datetime
from ..extensions import db


class Fixture(db.Model):
    """Fixture model."""

    __tablename__ = 'fixtures'

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False, index=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    kickoff_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(
        db.Enum('upcoming', 'live', 'finished', name='fixture_status'),
        default='upcoming',
        nullable=False,
        index=True
    )
    external_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)

    # Relationships
    predictions = db.relationship('Prediction', backref='fixture', lazy='dynamic', cascade='all, delete-orphan')
    odds = db.relationship('Odds', backref='fixture', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_odds=False, include_prediction=False):
        """Serialize fixture to dictionary."""
        data = {
            'id': self.id,
            'league_id': self.league_id,
            'league': self.league.to_dict() if self.league else None,
            'home_team': self.home_team.to_dict() if self.home_team else None,
            'away_team': self.away_team.to_dict() if self.away_team else None,
            'kickoff_at': self.kickoff_at.isoformat(),
            'status': self.status,
            'home_score': self.home_score,
            'away_score': self.away_score
        }
        if include_odds:
            data['odds'] = [odd.to_dict() for odd in self.odds]
        if include_prediction:
            prediction = self.predictions.first()
            data['prediction'] = prediction.to_dict() if prediction else None
        return data

    def get_actual_outcome(self):
        """Determine the actual outcome of the fixture."""
        if self.status != 'finished' or self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return 'home'
        elif self.away_score > self.home_score:
            return 'away'
        else:
            return 'draw'

    def __repr__(self):
        return f'<Fixture {self.home_team.name if self.home_team else "?"} vs {self.away_team.name if self.away_team else "?"}>'
