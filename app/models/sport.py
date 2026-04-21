"""Sport model."""
from ..extensions import db


class Sport(db.Model):
    """Sport model."""

    __tablename__ = 'sports'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum('football', 'basketball', 'tennis', name='sport_name'), unique=True, nullable=False)

    # Relationships
    leagues = db.relationship('League', backref='sport', lazy='dynamic', cascade='all, delete-orphan')
    guides = db.relationship('Guide', backref='sport', lazy='dynamic')

    def to_dict(self):
        """Serialize sport to dictionary."""
        return {
            'id': self.id,
            'name': self.name
        }

    def __repr__(self):
        return f'<Sport {self.name}>'
