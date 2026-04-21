"""ESPN Basketball API integration service (free, no API key required)."""
import logging
import time
from datetime import datetime, timedelta, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..extensions import db
from ..models.sport import Sport
from ..models.league import League
from ..models.team import Team
from ..models.fixture import Fixture

logger = logging.getLogger(__name__)


class BasketballService:
    """Service for fetching basketball data from ESPN's free API."""

    BASE_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball'

    # ESPN basketball league slugs
    SUPPORTED_LEAGUES = {
        'nba': {'name': 'NBA', 'country': 'USA', 'type': 'domestic'},
        'wnba': {'name': 'WNBA', 'country': 'USA', 'type': 'domestic'},
        'mens-college-basketball': {'name': 'NCAA Men', 'country': 'USA', 'type': 'domestic'},
        'womens-college-basketball': {'name': 'NCAA Women', 'country': 'USA', 'type': 'domestic'},
    }

    def _make_request(self, endpoint, params=None):
        """Make a request to ESPN API with retries."""
        try:
            url = f'{self.BASE_URL}/{endpoint}'

            # Set up retry strategy
            session = requests.Session()
            retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('https://', adapter)

            response = session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'ESPN Basketball API request failed: {e}')
            return None

    def get_or_create_sport(self):
        """Get or create the basketball sport."""
        sport = Sport.query.filter_by(name='basketball').first()
        if not sport:
            sport = Sport(name='basketball')
            db.session.add(sport)
            db.session.commit()
        return sport

    def ingest_leagues(self):
        """Ingest supported basketball leagues into the database."""
        sport = self.get_or_create_sport()
        created_count = 0

        for league_slug, league_info in self.SUPPORTED_LEAGUES.items():
            existing = League.query.filter_by(external_id=f'basketball_{league_slug}').first()
            if not existing:
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=f'basketball_{league_slug}',
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                created_count += 1

        db.session.commit()
        logger.info(f'Ingested {created_count} new basketball leagues')
        return created_count

    def ingest_fixtures(self, days_ahead=7):
        """Fetch upcoming fixtures for all supported basketball leagues."""
        total_fixtures = 0

        for league_slug, league_info in self.SUPPORTED_LEAGUES.items():
            # Get league from DB
            league = League.query.filter_by(external_id=f'basketball_{league_slug}').first()
            if not league:
                sport = self.get_or_create_sport()
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=f'basketball_{league_slug}',
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                db.session.flush()

            # Fetch fixtures for multiple days
            for day_offset in range(days_ahead):
                date = datetime.now(timezone.utc) + timedelta(days=day_offset)
                date_str = date.strftime('%Y%m%d')

                data = self._make_request(f'{league_slug}/scoreboard', {'dates': date_str})
                if not data:
                    continue

                events = data.get('events', [])
                if events:
                    logger.info(f"Found {len(events)} basketball events for {league_info['name']} on {date_str}")

                for event_data in events:
                    created = self._process_event(event_data, league)
                    total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} basketball fixtures')
        return total_fixtures

    def ingest_today_fixtures(self):
        """Fetch only today's fixtures (faster, fewer API calls)."""
        total_fixtures = 0
        today = datetime.now(timezone.utc).strftime('%Y%m%d')

        for league_slug, league_info in self.SUPPORTED_LEAGUES.items():
            league = League.query.filter_by(external_id=f'basketball_{league_slug}').first()
            if not league:
                sport = self.get_or_create_sport()
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=f'basketball_{league_slug}',
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                db.session.flush()

            data = self._make_request(f'{league_slug}/scoreboard', {'dates': today})
            if not data:
                continue

            events = data.get('events', [])
            if events:
                logger.info(f"Found {len(events)} basketball events for {league_info['name']}")

            for event_data in events:
                created = self._process_event(event_data, league)
                total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} basketball fixtures for today')
        return total_fixtures

    def _process_event(self, event_data, league):
        """Process and store a single basketball event."""
        event_id = event_data.get('id')
        external_id = f"basketball_{event_id}"

        # Check if fixture exists
        existing = Fixture.query.filter_by(external_id=external_id).first()

        # Get competition data
        competition = event_data.get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])

        if len(competitors) < 2:
            return 0

        # Determine home and away teams
        home_data = None
        away_data = None
        for comp in competitors:
            if comp.get('homeAway') == 'home':
                home_data = comp
            else:
                away_data = comp

        if not home_data or not away_data:
            home_data = competitors[0]
            away_data = competitors[1]

        # Get or create teams
        home_team = self._get_or_create_team(home_data, league.id)
        away_team = self._get_or_create_team(away_data, league.id)

        if not home_team or not away_team:
            return 0

        # Parse kickoff time
        date_str = event_data.get('date', '')
        try:
            kickoff_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            kickoff_at = datetime.now(timezone.utc)

        # Determine status
        status_data = event_data.get('status', {})
        status_type = status_data.get('type', {}).get('name', 'STATUS_SCHEDULED')
        status = self._parse_status(status_type)

        # Get scores
        home_score = home_data.get('score')
        away_score = away_data.get('score')

        # Convert scores to int if present
        try:
            home_score = int(home_score) if home_score else None
        except (ValueError, TypeError):
            home_score = None
        try:
            away_score = int(away_score) if away_score else None
        except (ValueError, TypeError):
            away_score = None

        if existing:
            # Update existing fixture
            existing.status = status
            existing.home_score = home_score
            existing.away_score = away_score
            existing.kickoff_at = kickoff_at
            return 0
        else:
            # Create new fixture
            fixture = Fixture(
                league_id=league.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                kickoff_at=kickoff_at,
                status=status,
                external_id=external_id,
                home_score=home_score,
                away_score=away_score
            )
            db.session.add(fixture)
            return 1

    def _parse_status(self, status_type):
        """Parse ESPN status to our format."""
        status_map = {
            'STATUS_SCHEDULED': 'upcoming',
            'STATUS_IN_PROGRESS': 'live',
            'STATUS_HALFTIME': 'live',
            'STATUS_END_PERIOD': 'live',
            'STATUS_FINAL': 'finished',
            'STATUS_FULL_TIME': 'finished',
            'STATUS_POSTPONED': 'upcoming',
            'STATUS_CANCELED': 'upcoming',
            'STATUS_DELAYED': 'upcoming',
        }
        return status_map.get(status_type, 'upcoming')

    def _get_or_create_team(self, team_data, league_id):
        """Get or create a team from ESPN data."""
        team_info = team_data.get('team', {})
        external_id = f"basketball_{team_info.get('id', '')}"
        name = team_info.get('displayName', team_info.get('name', 'Unknown'))
        logo_url = team_info.get('logo', '')

        if not external_id or not name:
            return None

        team = Team.query.filter_by(external_id=external_id).first()
        if not team:
            team = Team(
                league_id=league_id,
                name=name,
                external_id=external_id,
                logo_url=logo_url
            )
            db.session.add(team)
            db.session.flush()

        return team

    def update_finished_fixtures(self):
        """Update scores for finished basketball fixtures."""
        sport = Sport.query.filter_by(name='basketball').first()
        if not sport:
            return 0

        updated = 0
        leagues = League.query.filter_by(sport_id=sport.id).all()

        for league in leagues:
            # Extract the ESPN league slug
            league_slug = league.external_id.replace('basketball_', '')
            if league_slug not in self.SUPPORTED_LEAGUES:
                continue

            # Check yesterday and today for finished games
            for day_offset in range(-1, 1):
                date = datetime.now(timezone.utc) + timedelta(days=day_offset)
                date_str = date.strftime('%Y%m%d')

                data = self._make_request(f'{league_slug}/scoreboard', {'dates': date_str})
                if not data:
                    continue

                events = data.get('events', [])
                for event_data in events:
                    event_id = event_data.get('id')
                    external_id = f"basketball_{event_id}"

                    fixture = Fixture.query.filter_by(external_id=external_id).first()
                    if not fixture:
                        continue

                    status_data = event_data.get('status', {})
                    status_type = status_data.get('type', {}).get('name', '')

                    if status_type in ['STATUS_FINAL', 'STATUS_FULL_TIME']:
                        competition = event_data.get('competitions', [{}])[0]
                        competitors = competition.get('competitors', [])

                        for comp in competitors:
                            team_id = f"basketball_{comp.get('team', {}).get('id', '')}"
                            score = comp.get('score')
                            try:
                                score = int(score) if score else None
                            except (ValueError, TypeError):
                                score = None

                            if comp.get('homeAway') == 'home':
                                fixture.home_score = score
                            else:
                                fixture.away_score = score

                        fixture.status = 'finished'
                        updated += 1

        db.session.commit()
        logger.info(f'Updated {updated} finished basketball fixtures')
        return updated

    def test_connection(self):
        """Test if the ESPN Basketball API is accessible."""
        data = self._make_request('nba/scoreboard')
        if data:
            events = data.get('events', [])
            return True, f"Connected! Found {len(events)} NBA events"
        return False, "Failed to connect to ESPN Basketball API"
