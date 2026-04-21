"""Pytest configuration and fixtures."""
import pytest
from app import create_app
from app.extensions import db


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        yield db.session

        transaction.rollback()
        connection.close()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    from app.models.user import User

    with app.app_context():
        user = User(email='test@example.com', role='free')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        yield user

        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def auth_headers(app, sample_user):
    """Get JWT auth headers for a sample user."""
    from flask_jwt_extended import create_access_token

    with app.app_context():
        access_token = create_access_token(identity=sample_user.id)
        return {'Authorization': f'Bearer {access_token}'}
