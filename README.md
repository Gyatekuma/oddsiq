# OddsIQ Backend API

A Flask REST API for sports prediction and odds aggregation. Provides predictions for football, basketball, and tennis with confidence scores and value bet detection.

## Features

- **Prediction Engine**: Weighted algorithm using team form, H2H records, and home advantage
- **Odds Aggregation**: Real-time odds from multiple bookmakers with affiliate links
- **Multi-Sport Support**: Football (EPL, La Liga), Basketball (NBA), Tennis (ATP/WTA)
- **Premium Tiers**: Free users get limited predictions; premium users get full access
- **JWT Authentication**: Secure auth with refresh token rotation and reuse detection
- **Background Jobs**: APScheduler for automated data ingestion
- **Paystack Integration**: Subscription payments for premium access

## Tech Stack

- **Framework**: Flask 3.0
- **Database**: MySQL + SQLAlchemy ORM
- **Cache**: Redis
- **Auth**: JWT with Flask-JWT-Extended
- **Scheduler**: APScheduler
- **Payments**: Paystack

## Quick Start

### 1. Clone and Install

```bash
cd oddsiq-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Set Up Database

```bash
# Create MySQL database
mysql -u root -p -e "CREATE DATABASE oddsiq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run migrations
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Seed Development Data

```bash
python -m seeds.seed
```

### 5. Run Server

```bash
python run.py
# API available at http://localhost:5000
```

## API Registration Guide

### API-Football (RapidAPI)

1. Go to [RapidAPI](https://rapidapi.com/api-sports/api/api-football)
2. Subscribe to the free tier (100 requests/day)
3. Copy your API key to `.env` as `API_FOOTBALL_KEY`

### The Odds API

1. Go to [The Odds API](https://the-odds-api.com/)
2. Sign up for free tier (500 requests/month)
3. Copy your API key to `.env` as `THE_ODDS_API_KEY`

### API-Tennis (RapidAPI)

1. Go to [RapidAPI](https://rapidapi.com/api-sports/api/api-tennis)
2. Subscribe to the free tier
3. Copy your API key to `.env` as `API_TENNIS_KEY`

### BallDontLie API

No API key needed! This is a completely free API for NBA data.

### Paystack

1. Go to [Paystack Dashboard](https://dashboard.paystack.com/)
2. Create an account and get your test/live keys
3. Add to `.env` as `PAYSTACK_SECRET_KEY` and `PAYSTACK_PUBLIC_KEY`

## Running the Scheduler Manually

```python
from app import create_app
from app.tasks.scheduler import run_job_manually

app = create_app()

# Run a specific job
run_job_manually('ingest_football_fixtures', app)
run_job_manually('generate_predictions', app)
run_job_manually('ingest_odds', app)

# Available jobs:
# - ingest_football_fixtures
# - ingest_football_form
# - ingest_odds
# - ingest_basketball
# - ingest_tennis
# - generate_predictions
# - send_newsletter_digest
# - log_accuracy
```

## API Endpoints

### Authentication

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Refresh Token
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'

# Get Current User
curl http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer your-access-token"
```

### Predictions

```bash
# Get predictions (public, limited for free users)
curl "http://localhost:5000/api/predictions?sport=football&date=today"

# Get single prediction
curl http://localhost:5000/api/predictions/1 \
  -H "Authorization: Bearer your-access-token"

# Get value bets (premium only)
curl http://localhost:5000/api/predictions/value-bets \
  -H "Authorization: Bearer your-access-token"
```

### Fixtures

```bash
# Get fixtures
curl "http://localhost:5000/api/fixtures?date=today"

# Get fixtures by league
curl "http://localhost:5000/api/fixtures?league=1"

# Get single fixture
curl http://localhost:5000/api/fixtures/1

# Get live fixtures
curl http://localhost:5000/api/fixtures/live
```

### Odds

```bash
# Get odds for a fixture
curl http://localhost:5000/api/odds/1

# Compare odds across bookmakers
curl http://localhost:5000/api/odds/compare/1
```

### Leagues

```bash
# Get all leagues
curl http://localhost:5000/api/leagues

# Get league details
curl http://localhost:5000/api/leagues/1

# Get teams in league
curl http://localhost:5000/api/leagues/1/teams

# Get fixtures in league
curl http://localhost:5000/api/leagues/1/fixtures
```

### Accuracy

```bash
# Get accuracy statistics
curl http://localhost:5000/api/accuracy

# Get sport-specific accuracy
curl http://localhost:5000/api/accuracy/football
```

### Newsletter

```bash
# Subscribe
curl -X POST http://localhost:5000/api/newsletter/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "subscriber@example.com"}'

# Unsubscribe
curl -X POST http://localhost:5000/api/newsletter/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "subscriber@example.com"}'
```

### Payments

```bash
# Initiate payment (requires auth)
curl -X POST http://localhost:5000/api/payments/initiate \
  -H "Authorization: Bearer your-access-token" \
  -H "Content-Type: application/json" \
  -d '{"plan": "monthly"}'

# Verify payment
curl http://localhost:5000/api/payments/verify/paystack-reference \
  -H "Authorization: Bearer your-access-token"
```

### Admin (requires admin role)

```bash
# List users
curl http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer admin-access-token"

# Update user role
curl -X PUT http://localhost:5000/api/admin/users/1/role \
  -H "Authorization: Bearer admin-access-token" \
  -H "Content-Type: application/json" \
  -d '{"role": "premium"}'

# Add expert note to prediction
curl -X POST http://localhost:5000/api/admin/predictions/1/annotate \
  -H "Authorization: Bearer admin-access-token" \
  -H "Content-Type: application/json" \
  -d '{"expert_note": "Strong value based on recent form"}'

# Create guide
curl -X POST http://localhost:5000/api/admin/guides \
  -H "Authorization: Bearer admin-access-token" \
  -H "Content-Type: application/json" \
  -d '{"title": "Betting Tips", "body": "Content here...", "published": true}'
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_predictions.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Project Structure

```
oddsiq-backend/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py             # Configuration
│   ├── extensions.py         # Flask extensions
│   ├── models/               # SQLAlchemy models
│   ├── routes/               # API blueprints
│   ├── services/             # Business logic
│   ├── tasks/                # Scheduled jobs
│   └── utils/                # Helpers & decorators
├── migrations/               # Database migrations
├── seeds/                    # Seed data
├── tests/                    # Test suite
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

## Prediction Algorithm

The prediction engine uses a weighted formula:

```
home_score = (home_form × 0.30) + (h2h_for_home × 0.20) + (0.6 × 0.20) + 0.15
away_score = (away_form × 0.30) + (h2h_for_away × 0.20) + (0.4 × 0.20) + 0.15
```

- **Form**: Last 5 matches (W=3pts, D=1pt, L=0pts), normalized to 0-1
- **H2H**: Last 5 head-to-head meetings, normalized to 0-1
- **Home Advantage**: 0.6 for home, 0.4 for away
- **Outcome**: Higher score wins; if difference < 0.05, predict draw
- **Confidence**: Based on score difference magnitude

### Value Bet Detection

```
bookmaker_implied_prob = 1 / best_odds
model_prob = confidence_score / 100
is_value_bet = (model_prob - bookmaker_implied_prob) > 0.05
```

## Default Users (After Seeding)

| Email | Password | Role |
|-------|----------|------|
| admin@oddsiq.com | admin123 | admin |
| premium@oddsiq.com | premium123 | premium |
| user@example.com | user123 | free |

## License

MIT
