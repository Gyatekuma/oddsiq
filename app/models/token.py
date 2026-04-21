"""Refresh token model with hash storage."""
from datetime import datetime
import hashlib
import secrets
from ..extensions import db


class RefreshToken(db.Model):
    """Refresh token model with secure hash storage."""

    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def generate_token():
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token):
        """Create SHA-256 hash of the token."""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @classmethod
    def create_for_user(cls, user_id, expires_at):
        """Create a new refresh token for a user."""
        token = cls.generate_token()
        token_hash = cls.hash_token(token)

        refresh_token = cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.session.add(refresh_token)
        db.session.commit()

        return token, refresh_token

    @classmethod
    def find_by_token(cls, token):
        """Find a refresh token by its plaintext value."""
        token_hash = cls.hash_token(token)
        return cls.query.filter_by(token_hash=token_hash).first()

    @classmethod
    def revoke_all_for_user(cls, user_id):
        """Revoke all refresh tokens for a user (for reuse detection)."""
        cls.query.filter_by(user_id=user_id).update({'revoked': True})
        db.session.commit()

    def is_valid(self):
        """Check if the token is still valid (not revoked and not expired)."""
        return not self.revoked and self.expires_at > datetime.utcnow()

    def revoke(self):
        """Revoke this token."""
        self.revoked = True
        db.session.commit()

    def __repr__(self):
        return f'<RefreshToken user_id={self.user_id} revoked={self.revoked}>'
