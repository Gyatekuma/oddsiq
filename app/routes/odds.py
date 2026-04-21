"""Odds routes with affiliate URLs."""
from flask import Blueprint, request
from ..extensions import cache
from ..models.odds import Odds
from ..models.market_odds import MarketOdds
from ..models.fixture import Fixture
from ..utils.helpers import json_error, json_success

odds_bp = Blueprint('odds', __name__)


@odds_bp.route('/fixture/<int:fixture_id>', methods=['GET'])
@odds_bp.route('/match/<int:fixture_id>', methods=['GET'])
@odds_bp.route('/<int:fixture_id>', methods=['GET'])
@cache.cached(timeout=300)
def get_fixture_odds(fixture_id):
    """Get all bookmaker odds for a fixture with affiliate URLs, including market odds."""
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    odds = Odds.query.filter_by(fixture_id=fixture_id).order_by(Odds.home_win_odds.desc()).all()

    # Calculate best 1X2 odds
    best_odds = None
    if odds:
        best_home = max(odds, key=lambda o: o.home_win_odds)
        best_away = max(odds, key=lambda o: o.away_win_odds)
        best_draw = max((o for o in odds if o.draw_odds), key=lambda o: o.draw_odds, default=None)

        best_odds = {
            'home': {
                'odds': best_home.home_win_odds,
                'bookmaker': best_home.bookmaker_name,
                'affiliate_url': best_home.affiliate_url
            },
            'away': {
                'odds': best_away.away_win_odds,
                'bookmaker': best_away.bookmaker_name,
                'affiliate_url': best_away.affiliate_url
            }
        }

        if best_draw:
            best_odds['draw'] = {
                'odds': best_draw.draw_odds,
                'bookmaker': best_draw.bookmaker_name,
                'affiliate_url': best_draw.affiliate_url
            }

    # Get market odds (Over/Under, Double Chance, BTTS)
    market_odds_records = MarketOdds.query.filter_by(fixture_id=fixture_id).all()

    # Group market odds by type
    market_odds = {}
    for mo in market_odds_records:
        market_type = mo.market_type

        if market_type not in market_odds:
            market_odds[market_type] = []

        market_odds[market_type].append(mo.to_dict())

    # Calculate best odds for each market
    best_market_odds = {}
    for market_type, mo_list in market_odds.items():
        best_market_odds[market_type] = {}

        for mo in mo_list:
            odds_data = mo.get('odds_data', {})
            for outcome, value in odds_data.items():
                key = f"{outcome}_{mo.get('line_value', '')}" if mo.get('line_value') else outcome

                if key not in best_market_odds[market_type]:
                    best_market_odds[market_type][key] = {
                        'odds': value,
                        'bookmaker': mo['bookmaker_name'],
                        'affiliate_url': mo['affiliate_url'],
                        'line_value': mo.get('line_value'),
                        'outcome': outcome
                    }
                elif value > best_market_odds[market_type][key]['odds']:
                    best_market_odds[market_type][key] = {
                        'odds': value,
                        'bookmaker': mo['bookmaker_name'],
                        'affiliate_url': mo['affiliate_url'],
                        'line_value': mo.get('line_value'),
                        'outcome': outcome
                    }

    return json_success(data={
        'fixture': fixture.to_dict(),
        'odds': [o.to_dict() for o in odds],
        'best_odds': best_odds,
        'market_odds': market_odds,
        'best_market_odds': best_market_odds
    })


@odds_bp.route('/fixture/<int:fixture_id>/best', methods=['GET'])
@cache.cached(timeout=300)
def get_best_odds(fixture_id):
    """Get best odds for a fixture."""
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    odds = Odds.query.filter_by(fixture_id=fixture_id).all()

    if not odds:
        return json_success(data={'best_odds': None})

    best_home = max(odds, key=lambda o: o.home_win_odds)
    best_away = max(odds, key=lambda o: o.away_win_odds)
    best_draw = max((o for o in odds if o.draw_odds), key=lambda o: o.draw_odds, default=None)

    best_odds = {
        'home': {
            'odds': best_home.home_win_odds,
            'bookmaker': best_home.bookmaker_name,
            'affiliate_url': best_home.affiliate_url
        },
        'away': {
            'odds': best_away.away_win_odds,
            'bookmaker': best_away.bookmaker_name,
            'affiliate_url': best_away.affiliate_url
        }
    }

    if best_draw:
        best_odds['draw'] = {
            'odds': best_draw.draw_odds,
            'bookmaker': best_draw.bookmaker_name,
            'affiliate_url': best_draw.affiliate_url
        }

    return json_success(data={'best_odds': best_odds})


@odds_bp.route('/bookmakers', methods=['GET'])
@cache.cached(timeout=3600)
def get_bookmakers():
    """Get list of available bookmakers."""
    from sqlalchemy import distinct

    bookmakers = Odds.query.with_entities(
        distinct(Odds.bookmaker_name)
    ).all()

    return json_success(data={
        'bookmakers': [b[0] for b in bookmakers]
    })


@odds_bp.route('/compare/<int:fixture_id>', methods=['GET'])
@cache.cached(timeout=300)
def compare_odds(fixture_id):
    """Compare odds across bookmakers for a fixture."""
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    odds = Odds.query.filter_by(fixture_id=fixture_id).all()

    if not odds:
        return json_error('No odds available for this fixture', 404)

    # Organize by bookmaker
    comparison = []
    for odd in odds:
        comparison.append({
            'bookmaker': odd.bookmaker_name,
            'home_win': odd.home_win_odds,
            'draw': odd.draw_odds,
            'away_win': odd.away_win_odds,
            'affiliate_url': odd.affiliate_url,
            'fetched_at': odd.fetched_at.isoformat()
        })

    # Sort by home win odds (best first)
    comparison.sort(key=lambda x: x['home_win'], reverse=True)

    return json_success(data={
        'fixture': fixture.to_dict(),
        'comparison': comparison
    })


@odds_bp.route('/fixture/<int:fixture_id>/markets', methods=['GET'])
@cache.cached(timeout=300)
def get_all_market_odds(fixture_id):
    """
    Get all market odds for a fixture (Over/Under, Double Chance, BTTS).

    Returns odds grouped by market type with best odds highlighted.
    """
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    # Get all market odds for this fixture
    market_odds = MarketOdds.query.filter_by(fixture_id=fixture_id).all()

    # Group by market type
    grouped = {}
    for odds in market_odds:
        market_type = odds.market_type

        if market_type not in grouped:
            grouped[market_type] = {
                'odds': [],
                'best_odds': {}
            }

        odds_dict = odds.to_dict()
        grouped[market_type]['odds'].append(odds_dict)

        # Track best odds for each outcome
        for outcome, value in (odds.odds_data or {}).items():
            if outcome not in grouped[market_type]['best_odds']:
                grouped[market_type]['best_odds'][outcome] = {
                    'odds': value,
                    'bookmaker': odds.bookmaker_name,
                    'affiliate_url': odds.affiliate_url
                }
            elif value > grouped[market_type]['best_odds'][outcome]['odds']:
                grouped[market_type]['best_odds'][outcome] = {
                    'odds': value,
                    'bookmaker': odds.bookmaker_name,
                    'affiliate_url': odds.affiliate_url
                }

    return json_success(data={
        'fixture': fixture.to_dict(),
        'markets': grouped
    })


@odds_bp.route('/fixture/<int:fixture_id>/over-under', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_over_under_odds(fixture_id):
    """
    Get Over/Under odds for a fixture.

    Query params:
    - line: specific line (e.g., 2.5). If not provided, returns all lines.
    """
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    line = request.args.get('line', type=float)

    query = MarketOdds.query.filter_by(
        fixture_id=fixture_id,
        market_type='over_under'
    )

    if line is not None:
        query = query.filter_by(line_value=line)

    odds_records = query.all()

    # Group by line value
    by_line = {}
    for odds in odds_records:
        line_val = odds.line_value

        if line_val not in by_line:
            by_line[line_val] = {
                'line': line_val,
                'odds': [],
                'best_over': None,
                'best_under': None
            }

        odds_dict = odds.to_dict()
        by_line[line_val]['odds'].append(odds_dict)

        # Track best odds
        odds_data = odds.odds_data or {}
        over_odds = odds_data.get('over')
        under_odds = odds_data.get('under')

        if over_odds:
            if not by_line[line_val]['best_over'] or over_odds > by_line[line_val]['best_over']['odds']:
                by_line[line_val]['best_over'] = {
                    'odds': over_odds,
                    'bookmaker': odds.bookmaker_name,
                    'affiliate_url': odds.affiliate_url
                }

        if under_odds:
            if not by_line[line_val]['best_under'] or under_odds > by_line[line_val]['best_under']['odds']:
                by_line[line_val]['best_under'] = {
                    'odds': under_odds,
                    'bookmaker': odds.bookmaker_name,
                    'affiliate_url': odds.affiliate_url
                }

    return json_success(data={
        'fixture': fixture.to_dict(),
        'over_under': list(by_line.values())
    })


@odds_bp.route('/fixture/<int:fixture_id>/double-chance', methods=['GET'])
@cache.cached(timeout=300)
def get_double_chance_odds(fixture_id):
    """Get Double Chance odds (1X, X2, 12) for a fixture."""
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    odds_records = MarketOdds.query.filter_by(
        fixture_id=fixture_id,
        market_type='double_chance'
    ).all()

    odds_list = []
    best_odds = {'1X': None, 'X2': None, '12': None}

    for odds in odds_records:
        odds_dict = odds.to_dict()
        odds_list.append(odds_dict)

        odds_data = odds.odds_data or {}
        for outcome in ['1X', 'X2', '12']:
            value = odds_data.get(outcome)
            if value:
                if not best_odds[outcome] or value > best_odds[outcome]['odds']:
                    best_odds[outcome] = {
                        'odds': value,
                        'bookmaker': odds.bookmaker_name,
                        'affiliate_url': odds.affiliate_url
                    }

    return json_success(data={
        'fixture': fixture.to_dict(),
        'double_chance': {
            'odds': odds_list,
            'best_odds': best_odds,
            'outcomes': {
                '1X': 'Home or Draw',
                'X2': 'Draw or Away',
                '12': 'Home or Away'
            }
        }
    })


@odds_bp.route('/fixture/<int:fixture_id>/btts', methods=['GET'])
@cache.cached(timeout=300)
def get_btts_odds(fixture_id):
    """Get Both Teams To Score odds for a fixture."""
    fixture = Fixture.query.get(fixture_id)

    if not fixture:
        return json_error('Fixture not found', 404)

    odds_records = MarketOdds.query.filter_by(
        fixture_id=fixture_id,
        market_type='btts'
    ).all()

    odds_list = []
    best_yes = None
    best_no = None

    for odds in odds_records:
        odds_dict = odds.to_dict()
        odds_list.append(odds_dict)

        odds_data = odds.odds_data or {}
        yes_odds = odds_data.get('yes')
        no_odds = odds_data.get('no')

        if yes_odds:
            if not best_yes or yes_odds > best_yes['odds']:
                best_yes = {
                    'odds': yes_odds,
                    'bookmaker': odds.bookmaker_name,
                    'affiliate_url': odds.affiliate_url
                }

        if no_odds:
            if not best_no or no_odds > best_no['odds']:
                best_no = {
                    'odds': no_odds,
                    'bookmaker': odds.bookmaker_name,
                    'affiliate_url': odds.affiliate_url
                }

    return json_success(data={
        'fixture': fixture.to_dict(),
        'btts': {
            'odds': odds_list,
            'best_yes': best_yes,
            'best_no': best_no
        }
    })
