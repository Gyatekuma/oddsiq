"""ESPN API integration service (free, no API key required)."""
import logging
from datetime import datetime, timedelta, timezone
import requests
from flask import current_app
from ..extensions import db
from ..models.sport import Sport
from ..models.league import League
from ..models.team import Team
from ..models.fixture import Fixture

logger = logging.getLogger(__name__)


class ESPNService:
    """Service for fetching football data from ESPN's free API."""

    BASE_URL = 'https://site.api.espn.com/apis/site/v2/sports/soccer'

    # ESPN league slugs and their details
    SUPPORTED_LEAGUES = {
        # Domestic leagues
        'eng.1': {'name': 'Premier League', 'country': 'England', 'type': 'domestic'},
        'esp.1': {'name': 'La Liga', 'country': 'Spain', 'type': 'domestic'},
        'ger.1': {'name': 'Bundesliga', 'country': 'Germany', 'type': 'domestic'},
        'ita.1': {'name': 'Serie A', 'country': 'Italy', 'type': 'domestic'},
        'fra.1': {'name': 'Ligue 1', 'country': 'France', 'type': 'domestic'},
        'ned.1': {'name': 'Eredivisie', 'country': 'Netherlands', 'type': 'domestic'},
        'por.1': {'name': 'Primeira Liga', 'country': 'Portugal', 'type': 'domestic'},
        # International club competitions
        'uefa.champions': {'name': 'UEFA Champions League', 'country': 'Europe', 'type': 'international_club'},
        'uefa.europa': {'name': 'UEFA Europa League', 'country': 'Europe', 'type': 'international_club'},
        'uefa.europa.conf': {'name': 'UEFA Conference League', 'country': 'Europe', 'type': 'international_club'},
        # International national team competitions
        'fifa.world': {'name': 'FIFA World Cup', 'country': 'World', 'type': 'international_national'},
        'fifa.worldq.uefa': {'name': 'World Cup Qualifiers - UEFA', 'country': 'Europe', 'type': 'international_national'},
        'fifa.worldq.caf': {'name': 'World Cup Qualifiers - Africa', 'country': 'Africa', 'type': 'international_national'},
        'fifa.worldq.conmebol': {'name': 'World Cup Qualifiers - CONMEBOL', 'country': 'South America', 'type': 'international_national'},
        'uefa.euro': {'name': 'UEFA Euro', 'country': 'Europe', 'type': 'international_national'},
        'uefa.nations': {'name': 'UEFA Nations League', 'country': 'Europe', 'type': 'international_national'},
        'conmebol.america': {'name': 'Copa America', 'country': 'South America', 'type': 'international_national'},
        'caf.nations': {'name': 'Africa Cup of Nations', 'country': 'Africa', 'type': 'international_national'},
        'fifa.friendly': {'name': 'International Friendlies', 'country': 'World', 'type': 'international_national'},
    }

    def _make_request(self, endpoint, params=None):
        """Make a request to ESPN API."""
        try:
            url = f'{self.BASE_URL}/{endpoint}'
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'ESPN API request failed: {e}')
            return None

    def get_or_create_sport(self):
        """Get or create the football sport."""
        sport = Sport.query.filter_by(name='football').first()
        if not sport:
            sport = Sport(name='football')
            db.session.add(sport)
            db.session.commit()
        return sport

    def ingest_leagues(self):
        """Ingest supported leagues into the database."""
        sport = self.get_or_create_sport()
        created_count = 0

        for league_slug, league_info in self.SUPPORTED_LEAGUES.items():
            existing = League.query.filter_by(external_id=league_slug).first()
            if not existing:
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=league_slug,
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                created_count += 1
            else:
                # Update league type if needed
                if existing.league_type != league_info.get('type', 'domestic'):
                    existing.league_type = league_info.get('type', 'domestic')

        db.session.commit()
        logger.info(f'Ingested {created_count} new leagues')
        return created_count

    def ingest_fixtures(self, days_ahead=7):
        """Fetch upcoming fixtures for all supported leagues."""
        total_fixtures = 0

        for league_slug, league_info in self.SUPPORTED_LEAGUES.items():
            # Get league from DB
            league = League.query.filter_by(external_id=league_slug).first()
            if not league:
                sport = self.get_or_create_sport()
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=league_slug,
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
                logger.info(f"Found {len(events)} events for {league_info['name']} on {date_str}")

                for event_data in events:
                    created = self._process_event(event_data, league)
                    total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} fixtures')
        return total_fixtures

    def ingest_today_fixtures(self):
        """Fetch only today's fixtures (faster, fewer API calls)."""
        total_fixtures = 0
        today = datetime.now(timezone.utc).strftime('%Y%m%d')

        for league_slug, league_info in self.SUPPORTED_LEAGUES.items():
            league = League.query.filter_by(external_id=league_slug).first()
            if not league:
                sport = self.get_or_create_sport()
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=league_slug,
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                db.session.flush()

            data = self._make_request(f'{league_slug}/scoreboard', {'dates': today})
            if not data:
                continue

            events = data.get('events', [])
            if events:
                logger.info(f"Found {len(events)} events for {league_info['name']}")

            for event_data in events:
                created = self._process_event(event_data, league)
                total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} fixtures for today')
        return total_fixtures

    def _process_event(self, event_data, league):
        """Process and store a single event."""
        event_id = event_data.get('id')
        external_id = str(event_id)

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
            # Fallback: first is home, second is away
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
            # ESPN uses ISO format: 2026-03-30T15:00Z
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
        """Parse ESPN status to our format (only: upcoming, live, finished)."""
        status_map = {
            'STATUS_SCHEDULED': 'upcoming',
            'STATUS_IN_PROGRESS': 'live',
            'STATUS_HALFTIME': 'live',
            'STATUS_FULL_TIME': 'finished',
            'STATUS_FINAL': 'finished',
            'STATUS_FINAL_AET': 'finished',
            'STATUS_FINAL_PEN': 'finished',
            # Map postponed/cancelled to upcoming (they might be rescheduled)
            'STATUS_POSTPONED': 'upcoming',
            'STATUS_CANCELED': 'upcoming',
            'STATUS_DELAYED': 'upcoming',
        }
        return status_map.get(status_type, 'upcoming')

    def _get_or_create_team(self, team_data, league_id):
        """Get or create a team from ESPN data."""
        team_info = team_data.get('team', {})
        external_id = str(team_info.get('id', ''))
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

    def test_connection(self):
        """Test if the ESPN API is accessible."""
        data = self._make_request('eng.1/scoreboard')
        if data:
            events = data.get('events', [])
            return True, f"Connected! Found {len(events)} Premier League events"
        return False, "Failed to connect to ESPN API"
