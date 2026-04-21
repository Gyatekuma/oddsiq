"""Market odds model for multiple betting markets."""
from datetime import datetime
from ..extensions import db


class MarketOdds(db.Model):
    """
    Market odds model supporting multiple betting markets.

    Uses JSON odds_data for flexible storage:
    - Over/Under: {"over": 1.85, "under": 2.05}
    - BTTS: {"yes": 1.90, "no": 1.95}
    - Double Chance: {"1X": 1.25, "X2": 1.45, "12": 1.35}
    - Match Winner: {"home": 2.10, "draw": 3.40, "away": 3.20}
    - Corners: {"over": 1.90, "under": 1.90}
    - HT/FT: {"home_home": 2.5, "home_draw": 15.0, ...}
    """

    __tablename__ = 'market_odds'

    id = db.Column(db.Integer, primary_key=True)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixtures.id'), nullable=False, index=True)
    bookmaker_name = db.Column(db.String(100), nullable=False)
    affiliate_url = db.Column(db.String(500), nullable=True)

    market_type = db.Column(db.String(50), nullable=False, index=True)
    line_value = db.Column(db.Float, nullable=True)  # For O/U markets

    # Flexible JSON storage for odds
    odds_data = db.Column(db.JSON, nullable=False)

    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    fixture = db.relationship('Fixture', backref=db.backref('market_odds', lazy='dynamic'))

    # Unique constraint: one set of odds per fixture/bookmaker/market/line
    __table_args__ = (
        db.UniqueConstraint('fixture_id', 'bookmaker_name', 'market_type', 'line_value',
                            name='uix_fixture_bookmaker_market_line'),
        db.Index('ix_market_odds_lookup', 'fixture_id', 'market_type'),
    )

    def get_odds_for_outcome(self, outcome):
        """Get odds for a specific outcome."""
        if self.odds_data and isinstance(self.odds_data, dict):
            return self.odds_data.get(outcome)
        return None

    def get_implied_probability(self, outcome):
        """Calculate implied probability for an outcome."""
        odds = self.get_odds_for_outcome(outcome)
        if odds and odds > 0:
            return 1 / odds
        return None

    def get_best_odds_outcome(self):
        """Get the outcome with the best odds (highest)."""
        if not self.odds_data or not isinstance(self.odds_data, dict):
            return None, None

        best_outcome = None
        best_odds = 0

        for outcome, odds in self.odds_data.items():
            if odds and odds > best_odds:
                best_odds = odds
                best_outcome = outcome

        return best_outcome, best_odds

    def to_dict(self):
        """Serialize market odds to dictionary."""
        return {
            'id': self.id,
            'fixture_id': self.fixture_id,
            'bookmaker_name': self.bookmaker_name,
            'affiliate_url': self.affiliate_url,
            'market_type': self.market_type,
            'line_value': self.line_value,
            'odds_data': self.odds_data,
            'fetched_at': self.fetched_at.isoformat()
        }

    @staticmethod
    def get_best_odds_for_market(fixture_id, market_type, outcome, line_value=None):
        """
        Find the best odds across all bookmakers for a specific market and outcome.

        Returns: (best_odds, bookmaker_name, affiliate_url)
        """
        query = MarketOdds.query.filter_by(
            fixture_id=fixture_id,
            market_type=market_type
        )

        if line_value is not None:
            query = query.filter_by(line_value=line_value)

        all_odds = query.all()

        best_odds = 0
        best_bookmaker = None
        best_url = None

        for odds_record in all_odds:
            outcome_odds = odds_record.get_odds_for_outcome(outcome)
            if outcome_odds and outcome_odds > best_odds:
                best_odds = outcome_odds
                best_bookmaker = odds_record.bookmaker_name
                best_url = odds_record.affiliate_url

        return best_odds, best_bookmaker, best_url

    @staticmethod
    def get_odds_comparison(fixture_id, market_type, line_value=None):
        """
        Get odds comparison across all bookmakers for a market.

        Returns list of dicts with bookmaker and odds for each outcome.
        """
        query = MarketOdds.query.filter_by(
            fixture_id=fixture_id,
            market_type=market_type
        )

        if line_value is not None:
            query = query.filter_by(line_value=line_value)

        all_odds = query.order_by(MarketOdds.bookmaker_name).all()

        comparison = []
        for odds_record in all_odds:
            comparison.append({
                'bookmaker': odds_record.bookmaker_name,
                'affiliate_url': odds_record.affiliate_url,
                'odds': odds_record.odds_data
            })

        return comparison

    def __repr__(self):
        return f'<MarketOdds {self.market_type} {self.bookmaker_name} fixture={self.fixture_id}>'
