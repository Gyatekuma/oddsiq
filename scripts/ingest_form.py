#!/usr/bin/env python3
"""
Script to manually trigger form data ingestion for football teams.
Run from the backend directory:
    python scripts/ingest_form.py
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.tasks.scheduler import run_job_manually

if __name__ == '__main__':
    app = create_app()

    print('Starting form data ingestion...')
    print('This will fetch recent match results for all football teams.')
    print('-' * 50)

    try:
        count = run_job_manually('ingest_football_form', app)
        print('-' * 50)
        print(f'Done! Created {count} form records.')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
