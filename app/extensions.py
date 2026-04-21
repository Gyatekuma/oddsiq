"""Flask extension instances."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from flask_mail import Mail
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from apscheduler.schedulers.background import BackgroundScheduler

# Database ORM
db = SQLAlchemy()

# Database migrations
migrate = Migrate()

# JWT authentication
jwt = JWTManager()

# Redis cache
cache = Cache()

# Email
mail = Mail()

# CORS
cors = CORS()

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['100 per minute']
)

# Task scheduler
scheduler = BackgroundScheduler()
