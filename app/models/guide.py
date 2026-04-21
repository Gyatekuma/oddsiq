"""Betting guide model."""
from datetime import datetime
from ..extensions import db


class Guide(db.Model):
    """Betting guide model."""

    __tablename__ = 'guides'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=True, index=True)
    published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self, include_body=True):
        """Serialize guide to dictionary."""
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'sport_id': self.sport_id,
            'sport': self.sport.name if self.sport else None,
            'published': self.published,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_body:
            data['body'] = self.body
        return data

    @staticmethod
    def generate_slug(title):
        """Generate a URL-friendly slug from title."""
        import re
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')

    def __repr__(self):
        return f'<Guide {self.title}>'
