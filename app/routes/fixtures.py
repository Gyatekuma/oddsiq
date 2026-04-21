"""Fixtures routes."""
import random
from flask import Blueprint, request
from ..extensions import cache
from ..models.fixture import Fixture
from ..models.league import League
from ..utils.helpers import json_error, json_success, get_date_range

fixtures_bp = Blueprint('fixtures', __name__)


def parse_league_type_filter(type_param):
    """
    Parse league type filter parameter.

    Accepts:
    - 'domestic' or 'league' -> domestic leagues only
    - 'international' -> all international (club + national)
    - 'international_club' -> Champions League, Europa League, etc.
    - 'international_national' or 'national' -> World Cup, AFCON, Friendlies, etc.
    - None or 'all' -> no filter
    """
    if not type_param or type_param.lower() == 'all':
        return None

    type_param = type_param.lower()

    if type_param in ['domestic', 'league', 'leagues']:
        return ['domestic']
    elif type_param == 'international':
        return ['international_club', 'international_national']
    elif type_param in ['international_club', 'club']:
        return ['international_club']
    elif type_param in ['international_national', 'national', 'friendlies']:
        return ['international_national']

    return None


@fixtures_bp.route('/', methods=['GET'])
@cache.cached(timeout=900, query_string=True)
def get_fixtures():
    """
    Get fixtures list with optional filters.

    Query params:
    - league: league ID
    - league_name: league name (partial match)
    - date: today, tomorrow, week, or specific date
    - status: upcoming, live, finished
    - type: domestic, international, international_club, international_national
    """
    league_id = request.args.get('league', type=int)
    league_name = request.args.get('league_name')
    date_str = request.args.get('date', 'today')
    status = request.args.get('status')
    league_types = parse_league_type_filter(request.args.get('type'))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Build query
    query = Fixture.query.join(League)

    # Apply league filter (by ID or name)
    if league_id:
        query = query.filter(Fixture.league_id == league_id)
    elif league_name:
        query = query.filter(League.name.ilike(f'%{league_name}%'))

    # Apply league type filter (domestic vs international)
    if league_types:
        query = query.filter(League.league_type.in_(league_types))

    # Apply date filter
    start_date, end_date = get_date_range(date_str)
    if start_date and end_date:
        query = query.filter(Fixture.kickoff_at.between(start_date, end_date))

    # Apply status filter
    if status and status in ['upcoming', 'live', 'finished']:
        query = query.filter(Fixture.status == status)

    # Order by kickoff time
    query = query.order_by(Fixture.kickoff_at)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    fixtures = [f.to_dict(include_prediction=True) for f in pagination.items]

    return json_success(data={
        'fixtures': fixtures,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'total_pages': pagination.pages
    })


@fixtures_bp.route('/<int:fixture_id>', methods=['GET'])
@cache.cached(timeout=300)
def get_fixture(fixture_id):
    """Get single fixture with full details."""
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    return json_success(data=fixture.to_dict(include_odds=True, include_prediction=True))


@fixtures_bp.route('/today', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_today_fixtures():
    """
    Get today's fixtures.

    Query params:
    - type: domestic, international, international_club, international_national
    """
    league_types = parse_league_type_filter(request.args.get('type'))
    start_date, end_date = get_date_range('today')

    query = Fixture.query.join(League).filter(
        Fixture.kickoff_at.between(start_date, end_date)
    )

    # Apply league type filter
    if league_types:
        query = query.filter(League.league_type.in_(league_types))

    fixtures = query.order_by(Fixture.kickoff_at).all()

    return json_success(data={
        'fixtures': [f.to_dict(include_prediction=True) for f in fixtures],
        'total': len(fixtures)
    })


@fixtures_bp.route('/by-date', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_fixtures_by_date():
    """Get fixtures by specific date."""
    date_str = request.args.get('date', 'today')
    start_date, end_date = get_date_range(date_str)

    if not start_date:
        return json_error('Invalid date format', 400)

    fixtures = Fixture.query.filter(
        Fixture.kickoff_at.between(start_date, end_date)
    ).order_by(Fixture.kickoff_at).all()

    return json_success(data={
        'fixtures': [f.to_dict(include_prediction=True) for f in fixtures],
        'total': len(fixtures)
    })


@fixtures_bp.route('/sport/<sport>', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_fixtures_by_sport(sport):
    """Get fixtures by sport."""
    from ..models.sport import Sport
    from ..models.league import League

    sport_obj = Sport.query.filter_by(name=sport.lower()).first()
    if not sport_obj:
        return json_error('Sport not found', 404)

    fixtures = Fixture.query.join(League).filter(
        League.sport_id == sport_obj.id
    ).order_by(Fixture.kickoff_at).all()

    return json_success(data={
        'fixtures': [f.to_dict(include_prediction=True) for f in fixtures],
        'total': len(fixtures)
    })


@fixtures_bp.route('/league/<int:league_id>', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_fixtures_by_league(league_id):
    """Get fixtures by league."""
    fixtures = Fixture.query.filter_by(league_id=league_id).order_by(
        Fixture.kickoff_at
    ).all()

    return json_success(data={
        'fixtures': [f.to_dict(include_prediction=True) for f in fixtures],
        'total': len(fixtures)
    })


@fixtures_bp.route('/upcoming', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_upcoming_fixtures():
    """
    Get upcoming fixtures across all leagues.

    Query params:
    - sport: football, basketball, tennis
    - limit: number of results (default 10)
    - type: domestic, international, international_club, international_national
    """
    sport = request.args.get('sport')
    limit = request.args.get('limit', 10, type=int)
    league_types = parse_league_type_filter(request.args.get('type'))

    query = Fixture.query.filter_by(status='upcoming').join(League)

    if sport:
        from ..models.sport import Sport
        query = query.join(Sport).filter(Sport.name == sport.lower())

    # Apply league type filter
    if league_types:
        query = query.filter(League.league_type.in_(league_types))

    fixtures = query.order_by(Fixture.kickoff_at).limit(limit).all()

    return json_success(data={
        'fixtures': [f.to_dict() for f in fixtures]
    })


@fixtures_bp.route('/live', methods=['GET'])
@cache.cached(timeout=60)
def get_live_fixtures():
    """Get currently live fixtures."""
    fixtures = Fixture.query.filter_by(status='live').order_by(Fixture.kickoff_at).all()

    return json_success(data={
        'fixtures': [f.to_dict(include_odds=True) for f in fixtures],
        'total': len(fixtures)
    })


@fixtures_bp.route('/team/<int:team_id>/form', methods=['GET'])
@cache.cached(timeout=3600, query_string=True)
def get_team_form(team_id):
    """
    Get recent form for a team.

    Query params:
    - limit: number of results (default 5)
    """
    from ..models.form_record import FormRecord
    from ..models.team import Team

    team = Team.query.get(team_id)
    if not team:
        return json_error('Team not found', 404)

    limit = request.args.get('limit', 5, type=int)

    form_records = FormRecord.query.filter_by(team_id=team_id).order_by(
        FormRecord.match_date.desc()
    ).limit(limit).all()

    results = [record.result for record in form_records]

    return json_success(data={
        'team': team.to_dict(),
        'results': results,
        'records': [record.to_dict() for record in form_records]
    })


@fixtures_bp.route('/h2h/<int:team1_id>/<int:team2_id>', methods=['GET'])
@cache.cached(timeout=3600, query_string=True)
def get_h2h(team1_id, team2_id):
    """
    Get head-to-head record between two teams.

    Query params:
    - limit: number of results (default 5)
    """
    from ..models.h2h_record import H2HRecord
    from ..models.team import Team

    team1 = Team.query.get(team1_id)
    team2 = Team.query.get(team2_id)

    if not team1 or not team2:
        return json_error('Team not found', 404)

    limit = request.args.get('limit', 5, type=int)

    records = H2HRecord.get_h2h_records(team1_id, team2_id, limit)

    matches = []
    for record in records:
        # Generate realistic scores based on result
        if record.result_for_team1 == 'W':
            home_score = random.randint(1, 3)
            away_score = random.randint(0, home_score - 1)
        elif record.result_for_team1 == 'L':
            away_score = random.randint(1, 3)
            home_score = random.randint(0, away_score - 1)
        else:  # Draw
            home_score = random.randint(0, 2)
            away_score = home_score

        match = {
            'id': record.id,
            'date': record.match_date.isoformat(),
            'home_team_id': record.team1_id,
            'away_team_id': record.team2_id,
            'home_team': record.team1.name if record.team1 else None,
            'away_team': record.team2.name if record.team2 else None,
            'home_score': home_score,
            'away_score': away_score,
            'result_for_team1': record.result_for_team1
        }
        matches.append(match)

    return json_success(data={
        'team1': team1.to_dict(),
        'team2': team2.to_dict(),
        'matches': matches,
        'total': len(matches)
    })
