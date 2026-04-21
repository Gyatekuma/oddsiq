"""Team model."""
from ..extensions import db


class Team(db.Model):
    """Team model."""

    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    external_id = db.Column(db.String(100), nullable=True, index=True)
    logo_url = db.Column(db.String(500), nullable=True)

    # Relationships
    home_fixtures = db.relationship('Fixture', foreign_keys='Fixture.home_team_id', backref='home_team', lazy='dynamic')
    away_fixtures = db.relationship('Fixture', foreign_keys='Fixture.away_team_id', backref='away_team', lazy='dynamic')
    form_records = db.relationship('FormRecord', backref='team', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        """Serialize team to dictionary."""
        return {
            'id': self.id,
            'league_id': self.league_id,
            'name': self.name,
            'logo_url': self.logo_url
        }

    def get_recent_form(self, limit=5):
        """Get the team's recent form records."""
        return self.form_records.order_by(
            db.desc('match_date')
        ).limit(limit).all()

    def __repr__(self):
        return f'<Team {self.name}>'
