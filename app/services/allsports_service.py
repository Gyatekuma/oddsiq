"""AllSportsAPI integration service (via RapidAPI)."""
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


class AllSportsService:
    """Service for fetching data from AllSportsAPI via RapidAPI."""

    # RapidAPI endpoint
    BASE_URL = 'https://allsportsapi2.p.rapidapi.com/api/football'
    RAPIDAPI_HOST = 'allsportsapi2.p.rapidapi.com'

    # League IDs from AllSportsAPI (you can add more as needed)
    SUPPORTED_LEAGUES = {
        # English leagues
        152: {'name': 'Premier League', 'country': 'England', 'type': 'domestic'},
        153: {'name': 'Championship', 'country': 'England', 'type': 'domestic'},
        # Spanish leagues
        302: {'name': 'La Liga', 'country': 'Spain', 'type': 'domestic'},
        # German leagues
        175: {'name': 'Bundesliga', 'country': 'Germany', 'type': 'domestic'},
        # Italian leagues
        207: {'name': 'Serie A', 'country': 'Italy', 'type': 'domestic'},
        # French leagues
        168: {'name': 'Ligue 1', 'country': 'France', 'type': 'domestic'},
        # International club competitions
        3: {'name': 'UEFA Champions League', 'country': 'Europe', 'type': 'international_club'},
        4: {'name': 'UEFA Europa League', 'country': 'Europe', 'type': 'international_club'},
        683: {'name': 'UEFA Conference League', 'country': 'Europe', 'type': 'international_club'},
        # International national team competitions
        28: {'name': 'World Cup', 'country': 'World', 'type': 'international_national'},
        29: {'name': 'World Cup Qualifiers', 'country': 'World', 'type': 'international_national'},
        1: {'name': 'UEFA Euro', 'country': 'Europe', 'type': 'international_national'},
        17: {'name': 'Africa Cup of Nations', 'country': 'Africa', 'type': 'international_national'},
        21: {'name': 'Copa America', 'country': 'South America', 'type': 'international_national'},
        533: {'name': 'UEFA Nations League', 'country': 'Europe', 'type': 'international_national'},
        # International Friendlies
        10: {'name': 'International Friendlies', 'country': 'World', 'type': 'international_national'},
    }

    def __init__(self):
        # Use the same RapidAPI key as API-Football
        self.api_key = current_app.config.get('API_FOOTBALL_KEY', '')
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': self.RAPIDAPI_HOST
        }

    def _make_request(self, endpoint, params=None):
        """Make a request to AllSportsAPI via RapidAPI."""
        if not self.api_key:
            logger.warning('RapidAPI key not configured')
            return None

        try:
            url = f'{self.BASE_URL}/{endpoint}'
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Handle different response formats
            if isinstance(data, dict):
                if data.get('error'):
                    logger.error(f'AllSportsAPI error: {data.get("error")}')
                    return None
                # Return the data or events array
                return data.get('events', data.get('data', data))
            return data
        except requests.RequestException as e:
            logger.error(f'AllSportsAPI request failed: {e}')
            return None

    def get_or_create_sport(self):
        """Get or create the football sport."""
        sport = Sport.query.filter_by(name='football').first()
        if not sport:
            sport = Sport(name='football')
            db.session.add(sport)
            db.session.commit()
        return sport

    def fetch_leagues(self):
        """Fetch all available leagues from the API."""
        leagues_data = self._make_request('Leagues')
        if leagues_data:
            print(f"Found {len(leagues_data)} leagues")
            for league in leagues_data[:20]:  # Show first 20
                print(f"  ID: {league.get('league_key')} - {league.get('league_name')} ({league.get('country_name')})")
        return leagues_data

    def ingest_leagues(self):
        """Ingest supported leagues into the database."""
        sport = self.get_or_create_sport()
        created_count = 0
        updated_count = 0

        for external_id, league_info in self.SUPPORTED_LEAGUES.items():
            existing = League.query.filter_by(external_id=str(external_id)).first()
            if not existing:
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=str(external_id),
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                created_count += 1
            else:
                if existing.league_type != league_info.get('type', 'domestic'):
                    existing.league_type = league_info.get('type', 'domestic')
                    updated_count += 1

        db.session.commit()
        logger.info(f'Ingested {created_count} new leagues, updated {updated_count}')
        return created_count

    def ingest_fixtures(self, days_ahead=7):
        """Fetch upcoming fixtures for all supported leagues."""
        sport = self.get_or_create_sport()
        total_fixtures = 0

        now = datetime.now(timezone.utc)
        from_date = now.strftime('%Y-%m-%d')
        to_date = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        for external_id, league_info in self.SUPPORTED_LEAGUES.items():
            # Get league from DB
            league = League.query.filter_by(external_id=str(external_id)).first()
            if not league:
                # Create the league if it doesn't exist
                league = League(
                    sport_id=sport.id,
                    name=league_info['name'],
                    country=league_info['country'],
                    external_id=str(external_id),
                    league_type=league_info.get('type', 'domestic')
                )
                db.session.add(league)
                db.session.flush()

            # Fetch fixtures from API
            fixtures_data = self._make_request('Fixtures', {
                'from': from_date,
                'to': to_date,
                'leagueId': external_id
            })

            if not fixtures_data:
                continue

            logger.info(f"Found {len(fixtures_data)} fixtures for {league_info['name']}")

            for fixture_data in fixtures_data:
                created = self._process_fixture(fixture_data, league)
                total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} fixtures')
        return total_fixtures

    def ingest_all_fixtures(self, days_ahead=7):
        """Fetch ALL fixtures without league filter (uses fewer API calls)."""
        sport = self.get_or_create_sport()
        total_fixtures = 0

        now = datetime.now(timezone.utc)
        from_date = now.strftime('%Y-%m-%d')
        to_date = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        # Fetch all fixtures at once
        fixtures_data = self._make_request('Fixtures', {
            'from': from_date,
            'to': to_date
        })

        if not fixtures_data:
            logger.warning('No fixtures returned from API')
            return 0

        logger.info(f"Found {len(fixtures_data)} total fixtures")

        for fixture_data in fixtures_data:
            # Get or create league
            league_id = fixture_data.get('league_key')
            league_name = fixture_data.get('league_name', 'Unknown League')
            country_name = fixture_data.get('country_name', 'Unknown')

            league = League.query.filter_by(external_id=str(league_id)).first()
            if not league:
                # Determine league type
                league_type = 'domestic'
                league_name_lower = league_name.lower()
                if any(x in league_name_lower for x in ['champions league', 'europa league', 'conference league']):
                    league_type = 'international_club'
                elif any(x in league_name_lower for x in ['world cup', 'euro', 'nations league', 'africa cup', 'copa america', 'friendl']):
                    league_type = 'international_national'

                league = League(
                    sport_id=sport.id,
                    name=league_name,
                    country=country_name,
                    external_id=str(league_id),
                    league_type=league_type
                )
                db.session.add(league)
                db.session.flush()

            created = self._process_fixture(fixture_data, league)
            total_fixtures += created

        db.session.commit()
        logger.info(f'Ingested {total_fixtures} fixtures')
        return total_fixtures

    def _process_fixture(self, fixture_data, league):
        """Process and store a single fixture."""
        external_id = str(fixture_data.get('event_key'))

        # Check if fixture exists
        existing = Fixture.query.filter_by(external_id=external_id).first()
        if existing:
            # Update status and scores
            status = self._parse_status(fixture_data.get('event_status'))
            existing.status = status
            existing.home_score = fixture_data.get('event_final_result', '').split('-')[0].strip() or None
            existing.away_score = fixture_data.get('event_final_result', '').split('-')[-1].strip() or None
            return 0

        # Get or create teams
        home_team = self._get_or_create_team(
            fixture_data.get('home_team_key'),
            fixture_data.get('home_team_name', 'Unknown'),
            fixture_data.get('home_team_logo'),
            league.id
        )
        away_team = self._get_or_create_team(
            fixture_data.get('away_team_key'),
            fixture_data.get('away_team_name', 'Unknown'),
            fixture_data.get('away_team_logo'),
            league.id
        )

        if not home_team or not away_team:
            return 0

        # Parse kickoff time
        event_date = fixture_data.get('event_date', '')
        event_time = fixture_data.get('event_time', '00:00')
        try:
            kickoff_at = datetime.strptime(f'{event_date} {event_time}', '%Y-%m-%d %H:%M')
        except ValueError:
            kickoff_at = datetime.now(timezone.utc)

        # Determine status
        status = self._parse_status(fixture_data.get('event_status'))

        # Create fixture
        fixture = Fixture(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            kickoff_at=kickoff_at,
            status=status,
            external_id=external_id
        )
        db.session.add(fixture)
        return 1

    def _parse_status(self, status_str):
        """Parse event status to our format."""
        if not status_str:
            return 'upcoming'
        status_str = str(status_str).lower()
        if status_str in ['', 'ns', 'tbd', 'not started']:
            return 'upcoming'
        elif status_str in ['finished', 'ft', 'aet', 'pen']:
            return 'finished'
        elif status_str.isdigit() or status_str in ['ht', '1h', '2h', 'et', 'live']:
            return 'live'
        return 'upcoming'

    def _get_or_create_team(self, external_id, name, logo_url, league_id):
        """Get or create a team."""
        if not external_id or not name:
            return None

        external_id = str(external_id)
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
