"""Odds model with affiliate URLs."""
from datetime import datetime
from ..extensions import db


class Odds(db.Model):
    """Odds model for bookmaker odds."""

    __tablename__ = 'odds'

    id = db.Column(db.Integer, primary_key=True)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixtures.id'), nullable=False, index=True)
    bookmaker_name = db.Column(db.String(100), nullable=False)
    affiliate_url = db.Column(db.String(500), nullable=True)
    home_win_odds = db.Column(db.Float, nullable=False)
    draw_odds = db.Column(db.Float, nullable=True)  # Nullable for sports without draws
    away_win_odds = db.Column(db.Float, nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint on fixture + bookmaker
    __table_args__ = (
        db.UniqueConstraint('fixture_id', 'bookmaker_name', name='uix_fixture_bookmaker'),
    )

    def to_dict(self):
        """Serialize odds to dictionary."""
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'bookmaker_name': self.bookmaker_name,
            'affiliate_url': self.affiliate_url,
            'home_win_odds': self.home_win_odds,
            'draw_odds': self.draw_odds,
            'away_win_odds': self.away_win_odds,
            'fetched_at': self.fetched_at.isoformat()
        }

    def get_implied_probability(self, outcome):
        """Calculate implied probability from odds for a given outcome."""
        odds_map = {
            'home': self.home_win_odds,
            'draw': self.draw_odds,
            'away': self.away_win_odds
        }
        odds = odds_map.get(outcome)
        if odds and odds > 0:
            return 1 / odds
        return None

    def __repr__(self):
        return f'<Odds {self.bookmaker_name} fixture_id={self.fixture_id}>'
