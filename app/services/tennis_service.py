"""ESPN Tennis API integration service (free, no API key required)."""
import logging
import time
from datetime import datetime, timedelta, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..extensions import db
from ..models.sport import Sport
from ..models.league import League
from ..models.team import Team  # Using Team model for players
from ..models.fixture import Fixture

logger = logging.getLogger(__name__)


class TennisService:
    """Service for fetching tennis data from ESPN's free API."""

    BASE_URL = 'https://site.api.espn.com/apis/site/v2/sports/tennis'

    # ESPN tennis tournament slugs
    SUPPORTED_LEAGUES = {
        'atp': {'name': 'ATP Tour', 'country': 'International', 'type': 'domestic'},
        'wta': {'name': 'WTA Tour', 'country': 'International', 'type': 'domestic'},
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
            logger.error(f'ESPN Tennis API request failed: {e}')
            return None

    def get_or_create_sport(self):
        """Get or create the tennis sport."""
        sport = Sport.query.filter_by(name='tennis').first()
        if not sport:
            sport = Sport(name='tennis')
            db.session.add(sport)
            db.session.commit()
        return sport

    def ingest_leagues(self):
        """Ingest supported tennis tours into the database."""
        sport = self.get_or_create_sport()
        created_count = 0

        for tour_slug, tour_info in self.SUPPORTED_LEAGUES.items():
            existing = League.query.filter_by(external_id=f'tennis_{tour_slug}').first()
            if not existing:
                league = League(
                    sport_id=sport.id,
                    name=tour_info['name'],
                    country=tour_info['country'],
                    external_id=f'tennis_{tour_slug}',
                    league_type=tour_info.get('type', 'domestic')
                )
                db.session.add(league)
                created_count += 1

        db.session.commit()
        logger.info(f'Ingested {created_count} new tennis tours')
        return created_count

    def ingest_fixtures(self, days_ahead=7):
        """Fetch upcoming matches for all supported tennis tours."""
        total_fixtures = 0

        for tour_slug, tour_info in self.SUPPORTED_LEAGUES.items():
            # Get league from DB
            league = League.query.filter_by(external_id=f'tennis_{tour_slug}').first()
            if not league:
                sport = self.get_or_create_sport()
                league = League(
                    sport_id=sport.id,
                    name=tour_info['name'],
                    country=tour_info['country'],
                    external_id=f'tennis_{tour_slug}',
                    league_type=tour_info.get('type', 'domestic')
                )
                db.session.add(league)
                db.session.flush()

            # Fetch fixtures for multiple days
            for day_offset in range(days_ahead):
                date = datetime.now(timezone.utc) + timedelta(days=day_offset)
                date_str = date.strftime('%Y%m%d')

                data = self._make_request(f'{tour_slug}/scoreboard', {'dates': date_str})
                if not data:
                    continue

                events = data.get('events', [])
                if events:
                    logger.info(f"Found {len(events)} tennis events for {tour_info['name']} on {date_str}")

                for event_data in events:
                    created = self._process_event(event_data, league)
                    total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} tennis fixtures')
        return total_fixtures

    def ingest_today_fixtures(self):
        """Fetch only today's fixtures (faster, fewer API calls)."""
        total_fixtures = 0
        today = datetime.now(timezone.utc).strftime('%Y%m%d')

        for tour_slug, tour_info in self.SUPPORTED_LEAGUES.items():
            league = League.query.filter_by(external_id=f'tennis_{tour_slug}').first()
            if not league:
                sport = self.get_or_create_sport()
                league = League(
                    sport_id=sport.id,
                    name=tour_info['name'],
                    country=tour_info['country'],
                    external_id=f'tennis_{tour_slug}',
                    league_type=tour_info.get('type', 'domestic')
                )
                db.session.add(league)
                db.session.flush()

            data = self._make_request(f'{tour_slug}/scoreboard', {'dates': today})
            if not data:
                continue

            events = data.get('events', [])
            if events:
                logger.info(f"Found {len(events)} tennis events for {tour_info['name']}")

            for event_data in events:
                created = self._process_event(event_data, league)
                total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} tennis fixtures for today')
        return total_fixtures

    def _process_event(self, event_data, league):
        """Process and store a single tennis match."""
        event_id = event_data.get('id')
        external_id = f"tennis_{event_id}"

        # Check if fixture exists
        existing = Fixture.query.filter_by(external_id=external_id).first()

        # Get competition data
        competition = event_data.get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])

        if len(competitors) < 2:
            return 0

        # In tennis, we'll treat first player as "home" and second as "away"
        player1_data = competitors[0]
        player2_data = competitors[1]

        # Get or create players (as teams)
        player1 = self._get_or_create_player(player1_data, league.id)
        player2 = self._get_or_create_player(player2_data, league.id)

        if not player1 or not player2:
            return 0

        # Parse match time
        date_str = event_data.get('date', '')
        try:
            kickoff_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            kickoff_at = datetime.now(timezone.utc)

        # Determine status
        status_data = event_data.get('status', {})
        status_type = status_data.get('type', {}).get('name', 'STATUS_SCHEDULED')
        status = self._parse_status(status_type)

        # Get scores (sets won)
        player1_score = player1_data.get('score')
        player2_score = player2_data.get('score')

        # Convert to int if present
        try:
            player1_score = int(player1_score) if player1_score else None
        except (ValueError, TypeError):
            player1_score = None
        try:
            player2_score = int(player2_score) if player2_score else None
        except (ValueError, TypeError):
            player2_score = None

        if existing:
            # Update existing fixture
            existing.status = status
            existing.home_score = player1_score
            existing.away_score = player2_score
            existing.kickoff_at = kickoff_at
            return 0
        else:
            # Create new fixture
            fixture = Fixture(
                league_id=league.id,
                home_team_id=player1.id,  # Player 1
                away_team_id=player2.id,  # Player 2
                kickoff_at=kickoff_at,
                status=status,
                external_id=external_id,
                home_score=player1_score,
                away_score=player2_score
            )
            db.session.add(fixture)
            return 1

    def _parse_status(self, status_type):
        """Parse ESPN status to our format."""
        status_map = {
            'STATUS_SCHEDULED': 'upcoming',
            'STATUS_IN_PROGRESS': 'live',
            'STATUS_FIRST_SET': 'live',
            'STATUS_SECOND_SET': 'live',
            'STATUS_THIRD_SET': 'live',
            'STATUS_FOURTH_SET': 'live',
            'STATUS_FIFTH_SET': 'live',
            'STATUS_FINAL': 'finished',
            'STATUS_RETIRED': 'finished',
            'STATUS_WALKOVER': 'finished',
            'STATUS_POSTPONED': 'upcoming',
            'STATUS_CANCELED': 'upcoming',
            'STATUS_DELAYED': 'upcoming',
            'STATUS_SUSPENDED': 'upcoming',
        }
        return status_map.get(status_type, 'upcoming')

    def _get_or_create_player(self, player_data, league_id):
        """Get or create a player (stored as Team entity)."""
        # ESPN tennis uses 'athlete' for individual players
        athlete_info = player_data.get('athlete', player_data.get('team', {}))
        if not athlete_info:
            # Try to get name directly
            name = player_data.get('name', player_data.get('displayName', ''))
            player_id = player_data.get('id', '')
        else:
            player_id = athlete_info.get('id', '')
            name = athlete_info.get('displayName', athlete_info.get('name', 'Unknown'))

        external_id = f"tennis_player_{player_id}"

        if not player_id or not name or name == 'Unknown':
            return None

        player = Team.query.filter_by(external_id=external_id).first()
        if not player:
            # Get country flag if available
            flag = ''
            if 'flag' in athlete_info:
                flag = athlete_info.get('flag', {}).get('href', '')

            player = Team(
                league_id=league_id,
                name=name,
                external_id=external_id,
                logo_url=flag
            )
            db.session.add(player)
            db.session.flush()

        return player

    def update_finished_fixtures(self):
        """Update scores for finished tennis matches."""
        sport = Sport.query.filter_by(name='tennis').first()
        if not sport:
            return 0

        updated = 0
        leagues = League.query.filter_by(sport_id=sport.id).all()

        for league in leagues:
            # Extract the ESPN tour slug
            tour_slug = league.external_id.replace('tennis_', '')
            if tour_slug not in self.SUPPORTED_LEAGUES:
                continue

            # Check yesterday and today for finished matches
            for day_offset in range(-1, 1):
                date = datetime.now(timezone.utc) + timedelta(days=day_offset)
                date_str = date.strftime('%Y%m%d')

                data = self._make_request(f'{tour_slug}/scoreboard', {'dates': date_str})
                if not data:
                    continue

                events = data.get('events', [])
                for event_data in events:
                    event_id = event_data.get('id')
                    external_id = f"tennis_{event_id}"

                    fixture = Fixture.query.filter_by(external_id=external_id).first()
                    if not fixture:
                        continue

                    status_data = event_data.get('status', {})
                    status_type = status_data.get('type', {}).get('name', '')

                    if status_type in ['STATUS_FINAL', 'STATUS_RETIRED', 'STATUS_WALKOVER']:
                        competition = event_data.get('competitions', [{}])[0]
                        competitors = competition.get('competitors', [])

                        if len(competitors) >= 2:
                            try:
                                fixture.home_score = int(competitors[0].get('score', 0))
                            except (ValueError, TypeError):
                                fixture.home_score = 0
                            try:
                                fixture.away_score = int(competitors[1].get('score', 0))
                            except (ValueError, TypeError):
                                fixture.away_score = 0

                        fixture.status = 'finished'
                        updated += 1

        db.session.commit()
        logger.info(f'Updated {updated} finished tennis fixtures')
        return updated

    def test_connection(self):
        """Test if the ESPN Tennis API is accessible."""
        data = self._make_request('atp/scoreboard')
        if data:
            events = data.get('events', [])
            return True, f"Connected! Found {len(events)} ATP events"
        return False, "Failed to connect to ESPN Tennis API"
