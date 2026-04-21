"""Newsletter subscriber model."""
from datetime import datetime
from ..extensions import db


class Newsletter(db.Model):
    """Newsletter subscriber model."""

    __tablename__ = 'newsletters'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        """Serialize newsletter subscriber to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'subscribed_at': self.subscribed_at.isoformat(),
            'active': self.active
        }

    def unsubscribe(self):
        """Unsubscribe from newsletter."""
        self.active = False
        db.session.commit()

    def resubscribe(self):
        """Resubscribe to newsletter."""
        self.active = True
        db.session.commit()

    def __repr__(self):
        return f'<Newsletter {self.email}>'
