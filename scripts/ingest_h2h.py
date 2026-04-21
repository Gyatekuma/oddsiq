#!/usr/bin/env python3
"""
Script to populate H2H records from finished matches.
Run from the backend directory:
    python scripts/ingest_h2h.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.fixture import Fixture
from app.models.h2h_record import H2HRecord

def ingest_h2h_from_fixtures():
    """Create H2H records from finished fixtures."""
    app = create_app()

    with app.app_context():
        # Get all finished fixtures
        finished = Fixture.query.filter_by(status='finished').all()
        print(f'Found {len(finished)} finished fixtures')

        h2h_created = 0

        for fixture in finished:
            if not fixture.home_team_id or not fixture.away_team_id:
                continue

            if fixture.home_score is None or fixture.away_score is None:
                continue

            # Determine result for home team
            if fixture.home_score > fixture.away_score:
                result_for_home = 'W'
            elif fixture.home_score < fixture.away_score:
                result_for_home = 'L'
            else:
                result_for_home = 'D'

            # Check if H2H record already exists
            existing = H2HRecord.query.filter(
                H2HRecord.team1_id == fixture.home_team_id,
                H2HRecord.team2_id == fixture.away_team_id,
                H2HRecord.match_date == fixture.kickoff_at.date()
            ).first()

            if not existing:
                h2h = H2HRecord(
                    team1_id=fixture.home_team_id,
                    team2_id=fixture.away_team_id,
                    match_date=fixture.kickoff_at.date(),
                    result_for_team1=result_for_home
                )
                db.session.add(h2h)
                h2h_created += 1

        db.session.commit()
        print(f'Created {h2h_created} H2H records')

        # Show total H2H records
        total = H2HRecord.query.count()
        print(f'Total H2H records in database: {total}')

if __name__ == '__main__':
    print('Ingesting H2H records from finished fixtures...')
    print('-' * 50)
    ingest_h2h_from_fixtures()
    print('-' * 50)
    print('Done!')
