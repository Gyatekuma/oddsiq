#!/usr/bin/env python3
"""
Script to seed market odds (Over/Under, BTTS) for fixtures that have basic odds.
Run from the backend directory:
    python scripts/seed_market_odds.py
"""
import sys
import os
import random

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.odds import Odds
from app.models.market_odds import MarketOdds

# Bookmakers to use
BOOKMAKERS = ['Bet365', 'Betway', '1xBet', 'William Hill', 'Unibet']

def seed_market_odds():
    """Create market odds for fixtures that have basic odds."""
    app = create_app()

    with app.app_context():
        # Get fixtures with odds
        odds_records = Odds.query.all()
        fixture_ids = set(o.fixture_id for o in odds_records)
        print(f'Found {len(fixture_ids)} fixtures with odds')

        ou_created = 0
        btts_created = 0
        dc_created = 0

        for fixture_id in fixture_ids:
            # Get existing odds for this fixture
            existing_odds = Odds.query.filter_by(fixture_id=fixture_id).all()

            for bookmaker in BOOKMAKERS[:3]:  # Use top 3 bookmakers
                # Check if market odds already exist
                existing_ou = MarketOdds.query.filter_by(
                    fixture_id=fixture_id,
                    bookmaker_name=bookmaker,
                    market_type='over_under'
                ).first()

                if not existing_ou:
                    # Create Over/Under odds for multiple lines
                    for line in [1.5, 2.5, 3.5]:
                        # Generate realistic odds
                        if line == 1.5:
                            over_odds = round(random.uniform(1.15, 1.45), 2)
                            under_odds = round(random.uniform(2.50, 4.00), 2)
                        elif line == 2.5:
                            over_odds = round(random.uniform(1.70, 2.10), 2)
                            under_odds = round(random.uniform(1.70, 2.10), 2)
                        else:  # 3.5
                            over_odds = round(random.uniform(2.50, 4.00), 2)
                            under_odds = round(random.uniform(1.20, 1.50), 2)

                        market_odds = MarketOdds(
                            fixture_id=fixture_id,
                            bookmaker_name=bookmaker,
                            market_type='over_under',
                            line_value=line,
                            odds_data={'over': over_odds, 'under': under_odds}
                        )
                        db.session.add(market_odds)
                        ou_created += 1

                # Create BTTS odds
                existing_btts = MarketOdds.query.filter_by(
                    fixture_id=fixture_id,
                    bookmaker_name=bookmaker,
                    market_type='btts'
                ).first()

                if not existing_btts:
                    yes_odds = round(random.uniform(1.65, 2.20), 2)
                    no_odds = round(random.uniform(1.65, 2.20), 2)

                    market_odds = MarketOdds(
                        fixture_id=fixture_id,
                        bookmaker_name=bookmaker,
                        market_type='btts',
                        odds_data={'yes': yes_odds, 'no': no_odds}
                    )
                    db.session.add(market_odds)
                    btts_created += 1

                # Create Double Chance odds from 1X2 if available
                fixture_odds = next((o for o in existing_odds if o.bookmaker_name == bookmaker), None)
                if fixture_odds and fixture_odds.home_win_odds and fixture_odds.draw_odds and fixture_odds.away_win_odds:
                    existing_dc = MarketOdds.query.filter_by(
                        fixture_id=fixture_id,
                        bookmaker_name=bookmaker,
                        market_type='double_chance'
                    ).first()

                    if not existing_dc:
                        # Calculate double chance from 1X2
                        h = fixture_odds.home_win_odds
                        d = fixture_odds.draw_odds
                        a = fixture_odds.away_win_odds

                        # Implied probabilities
                        h_prob = 1/h
                        d_prob = 1/d
                        a_prob = 1/a
                        total = h_prob + d_prob + a_prob

                        # Normalize
                        h_fair = h_prob / total
                        d_fair = d_prob / total
                        a_fair = a_prob / total

                        # Double chance odds (with 5% margin)
                        margin = 0.95
                        dc_1x = round(1 / ((h_fair + d_fair) * margin), 2)
                        dc_x2 = round(1 / ((d_fair + a_fair) * margin), 2)
                        dc_12 = round(1 / ((h_fair + a_fair) * margin), 2)

                        market_odds = MarketOdds(
                            fixture_id=fixture_id,
                            bookmaker_name=bookmaker,
                            market_type='double_chance',
                            odds_data={'1X': dc_1x, 'X2': dc_x2, '12': dc_12}
                        )
                        db.session.add(market_odds)
                        dc_created += 1

        db.session.commit()
        print(f'Created {ou_created} Over/Under records')
        print(f'Created {btts_created} BTTS records')
        print(f'Created {dc_created} Double Chance records')

        # Show totals
        total_market = MarketOdds.query.count()
        print(f'\nTotal MarketOdds records: {total_market}')

if __name__ == '__main__':
    print('Seeding market odds...')
    print('-' * 50)
    seed_market_odds()
    print('-' * 50)
    print('Done!')
