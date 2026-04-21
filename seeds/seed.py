"""
Realistic seed data for development.

Run with: python -m seeds.seed

Creates:
- 3 sports (football, basketball, tennis)
- 16 leagues including international competitions:
  - Domestic: Premier League, La Liga, Bundesliga, Serie A
  - Club International: Champions League, Europa League
  - National Team: World Cup Qualifiers, AFCON, Euro Qualifiers,
                   Copa America, Nations League, International Friendlies
  - Other: NBA, EuroLeague, ATP Tour, WTA Tour
- 80+ teams including national teams
- 55+ fixtures with predictions (domestic + international + friendlies)
- All fixtures are for today and future dates
- Odds for all fixtures
- Form records for teams
- Sample users (admin, premium, free)
- Newsletter subscribers
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    User, Sport, League, Team, Fixture, Prediction,
    Odds, FormRecord, H2HRecord, Newsletter, Guide, AccuracyLog
)


def seed_database():
    """Seed the database with realistic development data."""
    app = create_app('development')

    with app.app_context():
        print('Clearing existing data...')
        # Clear in reverse dependency order
        AccuracyLog.query.delete()
        Odds.query.delete()
        Prediction.query.delete()
        H2HRecord.query.delete()
        FormRecord.query.delete()
        Fixture.query.delete()
        Team.query.delete()
        League.query.delete()
        Guide.query.delete()
        Newsletter.query.delete()
        Sport.query.delete()
        # Delete refresh tokens and subscriptions before users (foreign key constraints)
        from app.models.token import RefreshToken
        from app.models.subscription import Subscription
        RefreshToken.query.delete()
        Subscription.query.delete()
        User.query.delete()
        db.session.commit()

        print('Creating sports...')
        football = Sport(name='football')
        basketball = Sport(name='basketball')
        tennis = Sport(name='tennis')
        db.session.add_all([football, basketball, tennis])
        db.session.commit()

        print('Creating leagues...')
        # Football leagues - Domestic
        epl = League(sport_id=football.id, name='Premier League', country='England', external_id='39', league_type='domestic')
        la_liga = League(sport_id=football.id, name='La Liga', country='Spain', external_id='140', league_type='domestic')
        bundesliga = League(sport_id=football.id, name='Bundesliga', country='Germany', external_id='78', league_type='domestic')
        serie_a = League(sport_id=football.id, name='Serie A', country='Italy', external_id='135', league_type='domestic')

        # Football leagues - International Club Competitions
        ucl = League(sport_id=football.id, name='UEFA Champions League', country='Europe', external_id='2', league_type='international_club')
        uel = League(sport_id=football.id, name='UEFA Europa League', country='Europe', external_id='3', league_type='international_club')

        # Football leagues - International National Team Competitions
        wcq = League(sport_id=football.id, name='World Cup Qualifiers', country='International', external_id='wcq', league_type='international_national')
        afcon = League(sport_id=football.id, name='Africa Cup of Nations', country='Africa', external_id='6', league_type='international_national')
        euro_qual = League(sport_id=football.id, name='Euro Qualifiers', country='Europe', external_id='960', league_type='international_national')
        copa_america = League(sport_id=football.id, name='Copa America', country='South America', external_id='9', league_type='international_national')
        nations_league = League(sport_id=football.id, name='UEFA Nations League', country='Europe', external_id='5', league_type='international_national')
        friendlies = League(sport_id=football.id, name='International Friendlies', country='International', external_id='10', league_type='international_national')

        # Basketball leagues
        nba = League(sport_id=basketball.id, name='NBA', country='USA', external_id='nba', league_type='domestic')
        euroleague = League(sport_id=basketball.id, name='EuroLeague', country='Europe', external_id='euroleague', league_type='international_club')

        # Tennis "leagues"
        atp = League(sport_id=tennis.id, name='ATP Tour', country='International', external_id='atp', league_type='international_national')
        wta = League(sport_id=tennis.id, name='WTA Tour', country='International', external_id='wta', league_type='international_national')

        db.session.add_all([
            epl, la_liga, bundesliga, serie_a,
            ucl, uel,
            wcq, afcon, euro_qual, copa_america, nations_league, friendlies,
            nba, euroleague, atp, wta
        ])
        db.session.commit()

        print('Creating teams...')
        # EPL teams
        epl_teams = [
            Team(league_id=epl.id, name='Manchester City', external_id='50'),
            Team(league_id=epl.id, name='Arsenal', external_id='42'),
            Team(league_id=epl.id, name='Liverpool', external_id='40'),
            Team(league_id=epl.id, name='Manchester United', external_id='33'),
            Team(league_id=epl.id, name='Chelsea', external_id='49'),
            Team(league_id=epl.id, name='Tottenham', external_id='47'),
            Team(league_id=epl.id, name='Newcastle', external_id='34'),
            Team(league_id=epl.id, name='Brighton', external_id='51'),
            Team(league_id=epl.id, name='Aston Villa', external_id='66'),
            Team(league_id=epl.id, name='West Ham', external_id='48'),
        ]

        # La Liga teams
        laliga_teams = [
            Team(league_id=la_liga.id, name='Real Madrid', external_id='541'),
            Team(league_id=la_liga.id, name='Barcelona', external_id='529'),
            Team(league_id=la_liga.id, name='Atletico Madrid', external_id='530'),
            Team(league_id=la_liga.id, name='Sevilla', external_id='536'),
            Team(league_id=la_liga.id, name='Real Sociedad', external_id='548'),
            Team(league_id=la_liga.id, name='Villarreal', external_id='533'),
            Team(league_id=la_liga.id, name='Athletic Bilbao', external_id='531'),
            Team(league_id=la_liga.id, name='Real Betis', external_id='543'),
            Team(league_id=la_liga.id, name='Valencia', external_id='532'),
            Team(league_id=la_liga.id, name='Osasuna', external_id='727'),
        ]

        # Bundesliga teams
        bundesliga_teams = [
            Team(league_id=bundesliga.id, name='Bayern Munich', external_id='157'),
            Team(league_id=bundesliga.id, name='Borussia Dortmund', external_id='165'),
            Team(league_id=bundesliga.id, name='RB Leipzig', external_id='173'),
            Team(league_id=bundesliga.id, name='Bayer Leverkusen', external_id='168'),
            Team(league_id=bundesliga.id, name='Eintracht Frankfurt', external_id='169'),
        ]

        # Serie A teams
        serie_a_teams = [
            Team(league_id=serie_a.id, name='Inter Milan', external_id='505'),
            Team(league_id=serie_a.id, name='AC Milan', external_id='489'),
            Team(league_id=serie_a.id, name='Juventus', external_id='496'),
            Team(league_id=serie_a.id, name='Napoli', external_id='492'),
            Team(league_id=serie_a.id, name='Roma', external_id='497'),
        ]

        # International National Teams - Europe
        euro_teams = [
            Team(league_id=nations_league.id, name='France', external_id='2'),
            Team(league_id=nations_league.id, name='England', external_id='10'),
            Team(league_id=nations_league.id, name='Germany', external_id='25'),
            Team(league_id=nations_league.id, name='Spain', external_id='9'),
            Team(league_id=nations_league.id, name='Portugal', external_id='27'),
            Team(league_id=nations_league.id, name='Netherlands', external_id='21'),
            Team(league_id=nations_league.id, name='Italy', external_id='768'),
            Team(league_id=nations_league.id, name='Belgium', external_id='1'),
        ]

        # International National Teams - Africa (AFCON)
        africa_teams = [
            Team(league_id=afcon.id, name='Nigeria', external_id='1118'),
            Team(league_id=afcon.id, name='Morocco', external_id='31'),
            Team(league_id=afcon.id, name='Senegal', external_id='1120'),
            Team(league_id=afcon.id, name='Egypt', external_id='1112'),
            Team(league_id=afcon.id, name='Cameroon', external_id='1108'),
            Team(league_id=afcon.id, name='Ghana', external_id='1114'),
            Team(league_id=afcon.id, name='Ivory Coast', external_id='1113'),
            Team(league_id=afcon.id, name='Algeria', external_id='1104'),
        ]

        # International National Teams - South America (Copa America)
        sa_teams = [
            Team(league_id=copa_america.id, name='Brazil', external_id='6'),
            Team(league_id=copa_america.id, name='Argentina', external_id='26'),
            Team(league_id=copa_america.id, name='Uruguay', external_id='7'),
            Team(league_id=copa_america.id, name='Colombia', external_id='1561'),
            Team(league_id=copa_america.id, name='Chile', external_id='1558'),
            Team(league_id=copa_america.id, name='Ecuador', external_id='2382'),
        ]

        # World Cup Qualifiers teams (mix of regions)
        wcq_teams = [
            Team(league_id=wcq.id, name='USA', external_id='2384'),
            Team(league_id=wcq.id, name='Mexico', external_id='2379'),
            Team(league_id=wcq.id, name='Japan', external_id='12'),
            Team(league_id=wcq.id, name='South Korea', external_id='17'),
            Team(league_id=wcq.id, name='Australia', external_id='20'),
            Team(league_id=wcq.id, name='Saudi Arabia', external_id='23'),
        ]

        # International Friendlies teams (global mix)
        friendly_teams = [
            Team(league_id=friendlies.id, name='Croatia', external_id='3'),
            Team(league_id=friendlies.id, name='Denmark', external_id='24'),
            Team(league_id=friendlies.id, name='Switzerland', external_id='15'),
            Team(league_id=friendlies.id, name='Poland', external_id='18'),
            Team(league_id=friendlies.id, name='Sweden', external_id='16'),
            Team(league_id=friendlies.id, name='Austria', external_id='4'),
            Team(league_id=friendlies.id, name='Wales', external_id='8'),
            Team(league_id=friendlies.id, name='Scotland', external_id='19'),
            Team(league_id=friendlies.id, name='Turkey', external_id='11'),
            Team(league_id=friendlies.id, name='Czech Republic', external_id='13'),
        ]

        # NBA teams
        nba_teams = [
            Team(league_id=nba.id, name='Boston Celtics', external_id='1'),
            Team(league_id=nba.id, name='LA Lakers', external_id='14'),
            Team(league_id=nba.id, name='Golden State Warriors', external_id='10'),
            Team(league_id=nba.id, name='Milwaukee Bucks', external_id='15'),
            Team(league_id=nba.id, name='Phoenix Suns', external_id='24'),
            Team(league_id=nba.id, name='Denver Nuggets', external_id='8'),
            Team(league_id=nba.id, name='Miami Heat', external_id='16'),
            Team(league_id=nba.id, name='Philadelphia 76ers', external_id='23'),
            Team(league_id=nba.id, name='Brooklyn Nets', external_id='4'),
            Team(league_id=nba.id, name='Dallas Mavericks', external_id='7'),
        ]

        # ATP players (as teams)
        atp_players = [
            Team(league_id=atp.id, name='Novak Djokovic', external_id='d001'),
            Team(league_id=atp.id, name='Carlos Alcaraz', external_id='a001'),
            Team(league_id=atp.id, name='Daniil Medvedev', external_id='m001'),
            Team(league_id=atp.id, name='Jannik Sinner', external_id='s001'),
            Team(league_id=atp.id, name='Andrey Rublev', external_id='r001'),
        ]

        all_teams = (epl_teams + laliga_teams + bundesliga_teams + serie_a_teams +
                     euro_teams + africa_teams + sa_teams + wcq_teams + friendly_teams +
                     nba_teams + atp_players)
        db.session.add_all(all_teams)
        db.session.commit()

        print('Creating form records...')
        # Create form records for all club and national teams
        all_football_teams = (epl_teams + laliga_teams + bundesliga_teams + serie_a_teams +
                              euro_teams + africa_teams + sa_teams + wcq_teams + friendly_teams)
        for team in all_football_teams:
            for i in range(5):
                result = random.choice(['W', 'W', 'D', 'L'])  # Slight bias toward wins
                goals_scored = random.randint(0, 4)
                goals_conceded = random.randint(0, 3)

                form = FormRecord(
                    team_id=team.id,
                    match_date=(datetime.utcnow() - timedelta(days=(i + 1) * 7)).date(),
                    result=result,
                    goals_scored=goals_scored,
                    goals_conceded=goals_conceded
                )
                db.session.add(form)

        db.session.commit()

        print('Creating H2H records...')
        # Create H2H records for teams that will play each other
        # EPL H2H
        for i in range(len(epl_teams)):
            for j in range(i + 1, len(epl_teams)):
                team1 = epl_teams[i]
                team2 = epl_teams[j]
                # Create 3-5 historical matches
                for k in range(random.randint(3, 5)):
                    result = random.choice(['W', 'D', 'L'])
                    h2h = H2HRecord(
                        team1_id=team1.id,
                        team2_id=team2.id,
                        match_date=(datetime.utcnow() - timedelta(days=(k + 1) * 60)).date(),
                        result_for_team1=result
                    )
                    db.session.add(h2h)

        # La Liga H2H
        for i in range(len(laliga_teams)):
            for j in range(i + 1, len(laliga_teams)):
                team1 = laliga_teams[i]
                team2 = laliga_teams[j]
                for k in range(random.randint(3, 5)):
                    result = random.choice(['W', 'D', 'L'])
                    h2h = H2HRecord(
                        team1_id=team1.id,
                        team2_id=team2.id,
                        match_date=(datetime.utcnow() - timedelta(days=(k + 1) * 60)).date(),
                        result_for_team1=result
                    )
                    db.session.add(h2h)

        # Bundesliga H2H
        for i in range(len(bundesliga_teams)):
            for j in range(i + 1, len(bundesliga_teams)):
                team1 = bundesliga_teams[i]
                team2 = bundesliga_teams[j]
                for k in range(random.randint(3, 5)):
                    result = random.choice(['W', 'D', 'L'])
                    h2h = H2HRecord(
                        team1_id=team1.id,
                        team2_id=team2.id,
                        match_date=(datetime.utcnow() - timedelta(days=(k + 1) * 60)).date(),
                        result_for_team1=result
                    )
                    db.session.add(h2h)

        # Serie A H2H
        for i in range(len(serie_a_teams)):
            for j in range(i + 1, len(serie_a_teams)):
                team1 = serie_a_teams[i]
                team2 = serie_a_teams[j]
                for k in range(random.randint(3, 5)):
                    result = random.choice(['W', 'D', 'L'])
                    h2h = H2HRecord(
                        team1_id=team1.id,
                        team2_id=team2.id,
                        match_date=(datetime.utcnow() - timedelta(days=(k + 1) * 60)).date(),
                        result_for_team1=result
                    )
                    db.session.add(h2h)

        # International teams H2H (selected pairs)
        international_matchups = [
            (euro_teams[0], euro_teams[1]),  # France vs England
            (euro_teams[2], euro_teams[3]),  # Germany vs Spain
            (africa_teams[0], africa_teams[1]),  # Nigeria vs Morocco
            (africa_teams[2], africa_teams[3]),  # Senegal vs Egypt
            (sa_teams[0], sa_teams[1]),  # Brazil vs Argentina
        ]
        for team1, team2 in international_matchups:
            for k in range(random.randint(3, 5)):
                result = random.choice(['W', 'D', 'L'])
                h2h = H2HRecord(
                    team1_id=team1.id,
                    team2_id=team2.id,
                    match_date=(datetime.utcnow() - timedelta(days=(k + 1) * 90)).date(),
                    result_for_team1=result
                )
                db.session.add(h2h)

        db.session.commit()

        print('Creating fixtures...')
        fixtures = []
        fixture_count = 0

        # Helper to create fixtures at specific times
        def kickoff_at(days=0, hour=19, minute=0):
            """Create a kickoff time at specified day offset and time (UTC)."""
            now = datetime.utcnow()
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days)

        # Create EPL fixtures with realistic UK times (UTC)
        # Typical kickoff times: 12:30, 15:00, 17:30, 20:00
        epl_times = [
            (0, 15, 0),   # Today 15:00
            (0, 17, 30),  # Today 17:30
            (0, 20, 0),   # Today 20:00
            (1, 14, 0),   # Tomorrow 14:00
            (1, 16, 30),  # Tomorrow 16:30
            (2, 15, 0),   # Day 2
            (3, 20, 0),   # Day 3
            (5, 12, 30),  # Day 5
            (6, 15, 0),   # Day 6
            (7, 17, 30),  # Day 7
        ]
        for i in range(10):
            home = epl_teams[i]
            away = epl_teams[(i + 1) % 10]
            days, hour, minute = epl_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=epl.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'epl_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create La Liga fixtures with realistic Spanish times (UTC)
        # Spain is UTC+1/+2, typical times: 14:00, 16:15, 18:30, 21:00 local = 13:00, 15:15, 17:30, 20:00 UTC
        laliga_times = [
            (0, 18, 30),  # Today 18:30 UTC (20:30 Spain)
            (0, 21, 0),   # Today 21:00 UTC (23:00 Spain)
            (1, 17, 30),  # Tomorrow
            (1, 20, 0),   # Tomorrow
            (2, 18, 30),  # Day 2
            (3, 21, 0),   # Day 3
            (4, 17, 30),  # Day 4
            (5, 20, 0),   # Day 5
            (6, 18, 30),  # Day 6
            (7, 21, 0),   # Day 7
        ]
        for i in range(10):
            home = laliga_teams[i]
            away = laliga_teams[(i + 3) % 10]
            days, hour, minute = laliga_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=la_liga.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'laliga_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create UEFA Champions League fixtures with realistic times (20:00 or 17:45 UTC)
        ucl_clubs = epl_teams[:4] + laliga_teams[:4] + bundesliga_teams[:4] + serie_a_teams[:4]
        random.shuffle(ucl_clubs)
        ucl_times = [
            (1, 20, 0), (1, 20, 0), (2, 20, 0), (2, 20, 0),
            (3, 17, 45), (3, 20, 0), (4, 20, 0), (4, 20, 0),
        ]
        for i in range(8):
            home = ucl_clubs[i * 2]
            away = ucl_clubs[i * 2 + 1]
            days, hour, minute = ucl_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=ucl.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'ucl_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create UEFA Europa League fixtures with realistic times (17:45 or 20:00 UTC)
        uel_clubs = epl_teams[4:8] + laliga_teams[4:8] + bundesliga_teams + serie_a_teams
        random.shuffle(uel_clubs)
        uel_times = [
            (1, 17, 45), (1, 20, 0), (2, 17, 45),
            (2, 20, 0), (3, 17, 45), (3, 20, 0),
        ]
        for i in range(6):
            home = uel_clubs[i * 2]
            away = uel_clubs[i * 2 + 1]
            days, hour, minute = uel_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=uel.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'uel_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create UEFA Nations League fixtures with realistic times
        nl_times = [
            (0, 19, 45),  # Today 19:45 UTC
            (0, 19, 45),  # Today 19:45 UTC (concurrent matches)
            (1, 19, 45),  # Tomorrow
            (2, 19, 45),  # Day 2
        ]
        for i in range(4):
            home = euro_teams[i * 2]
            away = euro_teams[i * 2 + 1]
            days, hour, minute = nl_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=nations_league.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'nl_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create AFCON fixtures with realistic times (UTC)
        afcon_times = [
            (0, 16, 0),   # Today 16:00 UTC
            (0, 19, 0),   # Today 19:00 UTC
            (1, 16, 0),   # Tomorrow
            (2, 19, 0),   # Day 2
        ]
        for i in range(4):
            home = africa_teams[i * 2]
            away = africa_teams[i * 2 + 1]
            days, hour, minute = afcon_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=afcon.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'afcon_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create Copa America fixtures with realistic times (South America)
        copa_times = [
            (0, 22, 0),   # Today 22:00 UTC
            (1, 23, 0),   # Tomorrow
            (2, 21, 0),   # Day 2
        ]
        for i in range(3):
            home = sa_teams[i * 2]
            away = sa_teams[i * 2 + 1]
            days, hour, minute = copa_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=copa_america.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'copa_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create World Cup Qualifiers fixtures with realistic times
        wcq_times = [
            (1, 19, 0),   # Tomorrow 19:00 UTC
            (2, 18, 0),   # Day 2
            (3, 20, 0),   # Day 3
        ]
        for i in range(3):
            home = wcq_teams[i * 2]
            away = wcq_teams[i * 2 + 1]
            days, hour, minute = wcq_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=wcq.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'wcq_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Create International Friendlies fixtures with realistic times
        friendly_times = [
            (0, 14, 0),   # Today 14:00 UTC
            (0, 17, 0),   # Today 17:00 UTC
            (1, 19, 0),   # Tomorrow
            (2, 18, 30),  # Day 2
            (3, 20, 0),   # Day 3
        ]
        for i in range(5):
            home = friendly_teams[i * 2]
            away = friendly_teams[i * 2 + 1]
            days, hour, minute = friendly_times[i]
            kickoff = kickoff_at(days, hour, minute)

            fixture = Fixture(
                league_id=friendlies.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'friendly_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        # Add cross-regional friendlies with REALISTIC match times (UTC)
        # Times are in UTC - frontend should convert to user's local timezone
        cross_friendlies = [
            (africa_teams[5], euro_teams[2], 0, 18, 45),   # Ghana vs Germany - TODAY 18:45 UTC (6:45pm)
            (euro_teams[0], africa_teams[0], 0, 20, 0),    # France vs Nigeria - TODAY 20:00 UTC (8:00pm)
            (sa_teams[0], euro_teams[4], 0, 19, 30),       # Brazil vs Portugal - TODAY 19:30 UTC (7:30pm)
            (wcq_teams[0], euro_teams[1], 1, 19, 0),       # USA vs England - Tomorrow 19:00 UTC
            (africa_teams[1], sa_teams[1], 2, 20, 0),      # Morocco vs Argentina - 2 days 20:00 UTC
            (wcq_teams[2], euro_teams[3], 3, 18, 30),      # Japan vs Spain - 3 days 18:30 UTC
        ]
        for item in cross_friendlies:
            home, away, days_offset, hour, minute = item
            kickoff = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_offset)
            fixture = Fixture(
                league_id=friendlies.id,
                home_team_id=home.id,
                away_team_id=away.id,
                kickoff_at=kickoff,
                status='upcoming',
                external_id=f'friendly_{fixture_count}'
            )
            fixtures.append(fixture)
            fixture_count += 1

        db.session.add_all(fixtures)
        db.session.commit()

        print('Creating predictions and odds...')
        bookmakers = [
            ('Betway', 'BETWAY'),
            ('1xBet', 'ONEXBET'),
            ('Bet365', 'BET365'),
            ('SportyBet', 'SPORTYBET'),
        ]

        for fixture in fixtures:
            # Create prediction
            outcome = random.choice(['home', 'draw', 'away'])
            confidence = random.uniform(0.5, 0.95)
            is_value = confidence > 0.75 and random.random() > 0.5
            is_premium = confidence > 0.8

            prediction = Prediction(
                fixture_id=fixture.id,
                predicted_outcome=outcome,
                confidence_score=confidence,
                is_value_bet=is_value,
                is_premium=is_premium,
                expert_note='Strong form and favorable H2H record.' if is_premium else None
            )
            db.session.add(prediction)

            # Create odds for each bookmaker
            for bookmaker_name, affiliate_key in bookmakers:
                home_odds = round(random.uniform(1.2, 4.5), 2)
                draw_odds = round(random.uniform(2.5, 4.0), 2)
                away_odds = round(random.uniform(1.3, 5.0), 2)

                odds = Odds(
                    fixture_id=fixture.id,
                    bookmaker_name=bookmaker_name,
                    affiliate_url=f'https://{bookmaker_name.lower()}.com/?ref=oddsiq',
                    home_win_odds=home_odds,
                    draw_odds=draw_odds,
                    away_win_odds=away_odds
                )
                db.session.add(odds)

        db.session.commit()

        print('Creating users...')
        # Admin user
        admin = User(email='admin@oddsiq.com', role='admin')
        admin.set_password('admin123')

        # Premium user
        premium = User(
            email='premium@oddsiq.com',
            role='premium',
            subscription_expires_at=datetime.utcnow() + timedelta(days=30)
        )
        premium.set_password('premium123')

        # Free user
        free_user = User(email='user@example.com', role='free')
        free_user.set_password('user123')

        db.session.add_all([admin, premium, free_user])
        db.session.commit()

        print('Creating newsletter subscribers...')
        subscribers = [
            Newsletter(email='subscriber1@example.com'),
            Newsletter(email='subscriber2@example.com'),
            Newsletter(email='subscriber3@example.com'),
        ]
        db.session.add_all(subscribers)
        db.session.commit()

        print('Creating guides...')
        guides = [
            Guide(
                title='Understanding Football Betting Markets',
                slug='understanding-football-betting-markets',
                body='''
# Understanding Football Betting Markets

Football betting offers various markets for punters. Here's a breakdown of the most popular ones:

## 1X2 (Match Result)
The simplest market - predict the outcome: Home win (1), Draw (X), or Away win (2).

## Over/Under Goals
Bet on whether the total goals will be over or under a specified number (e.g., Over 2.5 goals).

## Both Teams to Score (BTTS)
Predict whether both teams will score at least one goal.

## Asian Handicap
A more advanced market that eliminates the draw option by giving teams a handicap.

## Tips for Success
- Always research team form
- Check head-to-head records
- Consider home advantage
- Look for value, not just winners
                ''',
                sport_id=football.id,
                published=True
            ),
            Guide(
                title='Introduction to Value Betting',
                slug='introduction-to-value-betting',
                body='''
# Introduction to Value Betting

Value betting is the cornerstone of profitable sports betting.

## What is Value?
Value exists when the probability of an outcome is higher than what the odds suggest.

## Formula
Value = (Probability × Odds) - 1

If Value > 0, you have a value bet.

## Example
If you believe a team has a 50% chance of winning, but odds of 2.20:
- Value = (0.50 × 2.20) - 1 = 0.10 (10% value)

This is a value bet worth taking.

## Key Principles
1. Think in probabilities, not just outcomes
2. Shop for the best odds
3. Keep detailed records
4. Bet consistently, not emotionally
                ''',
                sport_id=None,  # General guide
                published=True
            ),
        ]
        db.session.add_all(guides)
        db.session.commit()

        print('Seed completed successfully!')
        print(f'Created:')
        print(f'  - 3 sports')
        print(f'  - 16 leagues (4 domestic + 8 international + 4 other)')
        print(f'  - {len(all_teams)} teams/players')
        print(f'  - {len(fixtures)} fixtures (including international & friendlies)')
        print(f'  - {len(fixtures)} predictions')
        print(f'  - {len(fixtures) * len(bookmakers)} odds records')
        print(f'  - 3 users (admin, premium, free)')
        print(f'  - 3 newsletter subscribers')
        print(f'  - 2 guides')


if __name__ == '__main__':
    seed_database()
