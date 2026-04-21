"""League model."""
from ..extensions import db


# League type constants
LEAGUE_TYPE_DOMESTIC = 'domestic'
LEAGUE_TYPE_INTERNATIONAL_CLUB = 'international_club'
LEAGUE_TYPE_INTERNATIONAL_NATIONAL = 'international_national'


class League(db.Model):
    """League model."""

    __tablename__ = 'leagues'

    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    country = db.Column(db.String(100), nullable=True)
    external_id = db.Column(db.String(100), nullable=True, index=True)
    logo_url = db.Column(db.String(500), nullable=True)
    # League type: 'domestic', 'international_club', 'international_national'
    league_type = db.Column(db.String(50), nullable=False, default='domestic', index=True)

    # Relationships
    teams = db.relationship('Team', backref='league', lazy='dynamic', cascade='all, delete-orphan')
    fixtures = db.relationship('Fixture', backref='league', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_teams=False):
        """Serialize league to dictionary."""
        data = {
            'id': self.id,
            'sport_id': self.sport_id,
            'sport': self.sport.name if self.sport else None,
            'name': self.name,
            'country': self.country,
            'logo_url': self.logo_url,
            'league_type': self.league_type
        }
        if include_teams:
            data['teams'] = [team.to_dict() for team in self.teams]
        return data

    def __repr__(self):
        return f'<League {self.name}>'
