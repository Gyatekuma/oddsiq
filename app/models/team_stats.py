"""Team statistics model for market predictions."""
from datetime import datetime
from ..extensions import db


class TeamStats(db.Model):
    """
    Aggregated team statistics for market-specific predictions.

    Stores calculated stats from match history for:
    - Over/Under predictions (avg goals scored/conceded)
    - BTTS predictions (scoring rates, clean sheets)
    - Corners predictions (avg corners for/against)
    """

    __tablename__ = 'team_stats'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    season = db.Column(db.String(20), nullable=False)  # e.g., "2024-25"

    # Match count
    matches_played = db.Column(db.Integer, default=0, nullable=False)

    # Goals statistics (for Over/Under, BTTS)
    goals_scored = db.Column(db.Integer, default=0, nullable=False)
    goals_conceded = db.Column(db.Integer, default=0, nullable=False)
    avg_goals_scored = db.Column(db.Float, default=0.0, nullable=False)
    avg_goals_conceded = db.Column(db.Float, default=0.0, nullable=False)

    # BTTS statistics
    btts_yes_count = db.Column(db.Integer, default=0, nullable=False)  # Matches where both teams scored
    btts_percentage = db.Column(db.Float, default=0.0, nullable=False)
    clean_sheets = db.Column(db.Integer, default=0, nullable=False)
    failed_to_score = db.Column(db.Integer, default=0, nullable=False)

    # Over/Under statistics
    over_2_5_count = db.Column(db.Integer, default=0, nullable=False)
    over_1_5_count = db.Column(db.Integer, default=0, nullable=False)
    over_0_5_count = db.Column(db.Integer, default=0, nullable=False)

    # Corners statistics
    total_corners_for = db.Column(db.Integer, default=0, nullable=False)
    total_corners_against = db.Column(db.Integer, default=0, nullable=False)
    avg_corners_for = db.Column(db.Float, default=0.0, nullable=False)
    avg_corners_against = db.Column(db.Float, default=0.0, nullable=False)

    # HT/FT statistics
    ht_winning_count = db.Column(db.Integer, default=0, nullable=False)
    ht_drawing_count = db.Column(db.Integer, default=0, nullable=False)
    ht_losing_count = db.Column(db.Integer, default=0, nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team = db.relationship('Team', backref=db.backref('stats', lazy='dynamic'))

    # Unique constraint: one stats record per team per season
    __table_args__ = (
        db.UniqueConstraint('team_id', 'season', name='uix_team_season'),
    )

    def calculate_averages(self):
        """Recalculate averages based on totals."""
        if self.matches_played > 0:
            self.avg_goals_scored = self.goals_scored / self.matches_played
            self.avg_goals_conceded = self.goals_conceded / self.matches_played
            self.btts_percentage = (self.btts_yes_count / self.matches_played) * 100
            self.avg_corners_for = self.total_corners_for / self.matches_played
            self.avg_corners_against = self.total_corners_against / self.matches_played

    def get_over_percentage(self, line):
        """Get percentage of matches with total goals over the given line."""
        if self.matches_played == 0:
            return 0.0

        if line == 2.5:
            return (self.over_2_5_count / self.matches_played) * 100
        elif line == 1.5:
            return (self.over_1_5_count / self.matches_played) * 100
        elif line == 0.5:
            return (self.over_0_5_count / self.matches_played) * 100
        return 0.0

    def get_scoring_rate(self):
        """Get percentage of matches where team scored."""
        if self.matches_played == 0:
            return 0.0
        return ((self.matches_played - self.failed_to_score) / self.matches_played) * 100

    def get_clean_sheet_rate(self):
        """Get percentage of matches with clean sheets."""
        if self.matches_played == 0:
            return 0.0
        return (self.clean_sheets / self.matches_played) * 100

    def get_ht_lead_rate(self):
        """Get percentage of matches leading at half-time."""
        if self.matches_played == 0:
            return 0.0
        return (self.ht_winning_count / self.matches_played) * 100

    def to_dict(self):
        """Serialize team stats to dictionary."""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'season': self.season,
            'matches_played': self.matches_played,
            'goals': {
                'scored': self.goals_scored,
                'conceded': self.goals_conceded,
                'avg_scored': round(self.avg_goals_scored, 2),
                'avg_conceded': round(self.avg_goals_conceded, 2)
            },
            'btts': {
                'yes_count': self.btts_yes_count,
                'percentage': round(self.btts_percentage, 1)
            },
            'clean_sheets': self.clean_sheets,
            'failed_to_score': self.failed_to_score,
            'over_under': {
                'over_2_5_count': self.over_2_5_count,
                'over_1_5_count': self.over_1_5_count,
                'over_0_5_count': self.over_0_5_count,
                'over_2_5_pct': round(self.get_over_percentage(2.5), 1),
                'over_1_5_pct': round(self.get_over_percentage(1.5), 1)
            },
            'corners': {
                'avg_for': round(self.avg_corners_for, 2),
                'avg_against': round(self.avg_corners_against, 2)
            },
            'half_time': {
                'winning': self.ht_winning_count,
                'drawing': self.ht_drawing_count,
                'losing': self.ht_losing_count,
                'lead_rate': round(self.get_ht_lead_rate(), 1)
            },
            'updated_at': self.updated_at.isoformat()
        }

    @staticmethod
    def get_or_create(team_id, season='2024-25'):
        """Get existing stats or create new record."""
        stats = TeamStats.query.filter_by(team_id=team_id, season=season).first()
        if not stats:
            stats = TeamStats(team_id=team_id, season=season)
            db.session.add(stats)
            db.session.flush()
        return stats

    def __repr__(self):
        return f'<TeamStats team={self.team_id} season={self.season} GP={self.matches_played}>'
