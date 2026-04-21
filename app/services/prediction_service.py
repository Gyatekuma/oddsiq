"""
Prediction service with confidence score calculation and value bet detection.

This module implements the core prediction algorithm for OddsIQ.
"""
import logging
from datetime import datetime
from ..extensions import db
from ..models.fixture import Fixture
from ..models.prediction import Prediction
from ..models.form_record import FormRecord
from ..models.h2h_record import H2HRecord
from ..models.odds import Odds
from ..models.team import Team

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for generating match predictions."""

    # Weights for the prediction formula
    FORM_WEIGHT = 0.30          # 30% weight for recent form
    H2H_WEIGHT = 0.20           # 20% weight for head-to-head record
    HOME_ADVANTAGE_WEIGHT = 0.20  # 20% weight for home advantage
    # Remaining 30% is implicit in the calculation

    # Home advantage factor (home team gets 0.6, away gets 0.4)
    HOME_ADVANTAGE_FACTOR = 0.6
    AWAY_ADVANTAGE_FACTOR = 0.4

    # Draw threshold - if scores are within this range, predict draw
    DRAW_THRESHOLD = 0.05

    # Value bet threshold - model probability must exceed implied probability by this much
    VALUE_BET_THRESHOLD = 0.05

    def calculate_form_score(self, team_id, limit=5):
        """
        Calculate normalized form score for a team.

        Formula:
        - W = 3 points, D = 1 point, L = 0 points
        - Score = total_points / (matches * 3)
        - Returns value between 0.0 and 1.0

        Args:
            team_id: The team's database ID
            limit: Number of recent matches to consider (default 5)

        Returns:
            float: Normalized form score (0.0 to 1.0)
        """
        team = Team.query.get(team_id)
        if not team:
            return 0.5  # Neutral score if team not found

        form_records = team.get_recent_form(limit=limit)

        if not form_records:
            # No form data available - return neutral score
            return 0.5

        return FormRecord.calculate_form_score(form_records)

    def calculate_h2h_score(self, home_team_id, away_team_id, limit=5):
        """
        Calculate head-to-head score from home team's perspective.

        Formula:
        - W = 3 points, D = 1 point, L = 0 points
        - Score = total_points / (matches * 3)
        - Returns value between 0.0 and 1.0

        Args:
            home_team_id: Home team's database ID
            away_team_id: Away team's database ID
            limit: Number of recent H2H matches to consider

        Returns:
            tuple: (home_h2h_score, away_h2h_score) both normalized 0.0-1.0
        """
        h2h_records = H2HRecord.get_h2h_records(home_team_id, away_team_id, limit=limit)

        if not h2h_records:
            # No H2H data - return neutral scores
            return 0.5, 0.5

        home_h2h = H2HRecord.calculate_h2h_score(h2h_records, home_team_id)
        away_h2h = H2HRecord.calculate_h2h_score(h2h_records, away_team_id)

        return home_h2h, away_h2h

    def calculate_confidence_score(self, fixture):
        """
        Calculate prediction confidence score for a fixture.

        Weighted Formula:
            home_score = (home_form * 0.30) + (h2h_for_home * 0.20) + (home_advantage * 0.20)
            away_score = (away_form * 0.30) + (h2h_for_away * 0.20) + (away_advantage * 0.20)

        The remaining 30% is distributed evenly, giving both teams a base score.

        Args:
            fixture: The Fixture object to analyze

        Returns:
            dict: {
                'predicted_outcome': 'home'|'draw'|'away',
                'confidence_score': float (0.0 to 1.0),
                'home_score': float,
                'away_score': float
            }
        """
        import random

        # Determine sport type to know if draws are possible
        sport_name = fixture.league.sport.name if fixture.league and fixture.league.sport else 'football'
        allows_draws = sport_name == 'football'

        # Step 1: Get home team form (last 5 matches)
        home_form = self.calculate_form_score(fixture.home_team_id)

        # Step 2: Get away team form (last 5 matches)
        away_form = self.calculate_form_score(fixture.away_team_id)

        # Step 3: Get H2H record
        home_h2h, away_h2h = self.calculate_h2h_score(
            fixture.home_team_id,
            fixture.away_team_id
        )

        # Step 4: Apply weighted formula
        # Add some randomness to make predictions more varied when data is sparse
        random_factor = random.uniform(-0.1, 0.1)

        # Home team score calculation
        home_score = (
            (home_form * self.FORM_WEIGHT) +           # 30% form
            (home_h2h * self.H2H_WEIGHT) +              # 20% H2H
            (self.HOME_ADVANTAGE_FACTOR * self.HOME_ADVANTAGE_WEIGHT) +  # 20% home advantage
            0.15 + random_factor  # Base score with randomness
        )

        # Away team score calculation
        away_score = (
            (away_form * self.FORM_WEIGHT) +           # 30% form
            (away_h2h * self.H2H_WEIGHT) +              # 20% H2H
            (self.AWAY_ADVANTAGE_FACTOR * self.HOME_ADVANTAGE_WEIGHT) +  # 20% away factor
            0.15  # Base score
        )

        # Step 5: Determine predicted outcome
        score_difference = home_score - away_score

        if allows_draws and abs(score_difference) < self.DRAW_THRESHOLD:
            predicted_outcome = 'draw'
        elif score_difference > 0:
            predicted_outcome = 'home'
        else:
            predicted_outcome = 'away'

        # Step 6: Calculate confidence score
        # For basketball/tennis (no draws): confidence is higher since only 2 outcomes
        # For football: lower base confidence since 3 outcomes

        if allows_draws:
            # Football: 3-way market, so lower base confidence
            raw_confidence = abs(score_difference)
            # Normalize: typical max difference is around 0.4
            confidence_score = min(0.55 + (raw_confidence / 0.4) * 0.40, 0.95)
        else:
            # Basketball/Tennis: 2-way market, higher base confidence
            raw_confidence = abs(score_difference)
            # Higher base confidence for 2-way markets
            confidence_score = min(0.60 + (raw_confidence / 0.3) * 0.35, 0.95)

        return {
            'predicted_outcome': predicted_outcome,
            'confidence_score': confidence_score,
            'home_score': home_score,
            'away_score': away_score
        }

    def detect_value_bet(self, fixture_id, predicted_outcome, model_probability):
        """
        Detect if a prediction represents a value bet.

        A value bet exists when:
            model_probability - bookmaker_implied_probability > VALUE_BET_THRESHOLD

        Args:
            fixture_id: The fixture's database ID
            predicted_outcome: 'home', 'draw', or 'away'
            model_probability: Our model's probability for the outcome (0.0 to 1.0)

        Returns:
            dict: {
                'is_value_bet': bool,
                'best_odds': float or None,
                'bookmaker': str or None,
                'implied_probability': float or None,
                'edge': float or None (model_prob - implied_prob)
            }
        """
        # Get odds for this fixture
        odds = Odds.query.filter_by(fixture_id=fixture_id).all()

        if not odds:
            return {
                'is_value_bet': False,
                'best_odds': None,
                'bookmaker': None,
                'implied_probability': None,
                'edge': None
            }

        # Find best odds for the predicted outcome
        best_odds_value = 0
        best_bookmaker = None

        for odd in odds:
            if predicted_outcome == 'home' and odd.home_win_odds > best_odds_value:
                best_odds_value = odd.home_win_odds
                best_bookmaker = odd.bookmaker_name
            elif predicted_outcome == 'away' and odd.away_win_odds > best_odds_value:
                best_odds_value = odd.away_win_odds
                best_bookmaker = odd.bookmaker_name
            elif predicted_outcome == 'draw' and odd.draw_odds and odd.draw_odds > best_odds_value:
                best_odds_value = odd.draw_odds
                best_bookmaker = odd.bookmaker_name

        if best_odds_value == 0:
            return {
                'is_value_bet': False,
                'best_odds': None,
                'bookmaker': None,
                'implied_probability': None,
                'edge': None
            }

        # Calculate implied probability from odds
        # Implied probability = 1 / decimal_odds
        implied_probability = 1 / best_odds_value

        # Calculate edge (positive edge = value bet)
        edge = model_probability - implied_probability

        is_value_bet = edge > self.VALUE_BET_THRESHOLD

        return {
            'is_value_bet': is_value_bet,
            'best_odds': best_odds_value,
            'bookmaker': best_bookmaker,
            'implied_probability': round(implied_probability, 4),
            'edge': round(edge, 4)
        }

    def generate_prediction(self, fixture, is_premium=False):
        """
        Generate a complete prediction for a fixture.

        Args:
            fixture: The Fixture object
            is_premium: Whether to mark as premium content

        Returns:
            Prediction: The created prediction object
        """
        # Check if prediction already exists
        existing = Prediction.query.filter_by(fixture_id=fixture.id).first()
        if existing:
            logger.info(f'Prediction already exists for fixture {fixture.id}')
            return existing

        # Calculate confidence score
        result = self.calculate_confidence_score(fixture)

        # Detect value bet
        # Convert confidence to probability estimate
        # Higher confidence in a prediction = higher implied model probability
        model_probability = 0.33 + (result['confidence_score'] * 0.34)  # Range: 0.33 to 0.67

        value_bet_result = self.detect_value_bet(
            fixture.id,
            result['predicted_outcome'],
            model_probability
        )

        # Create prediction
        prediction = Prediction(
            fixture_id=fixture.id,
            predicted_outcome=result['predicted_outcome'],
            confidence_score=result['confidence_score'],
            is_value_bet=value_bet_result['is_value_bet'],
            is_premium=is_premium
        )

        db.session.add(prediction)
        db.session.commit()

        logger.info(
            f'Generated prediction for fixture {fixture.id}: '
            f'{result["predicted_outcome"]} with {result["confidence_score"]*100:.1f}% confidence'
        )

        return prediction

    def generate_predictions_for_upcoming(self, premium_threshold=0.7):
        """
        Generate predictions for all upcoming fixtures without predictions.

        Args:
            premium_threshold: Confidence threshold above which predictions are premium

        Returns:
            int: Number of predictions generated
        """
        # Get upcoming fixtures without predictions
        upcoming = Fixture.query.filter_by(status='upcoming').filter(
            ~Fixture.id.in_(
                db.session.query(Prediction.fixture_id)
            )
        ).all()

        generated = 0
        for fixture in upcoming:
            try:
                # Calculate confidence to determine premium status
                result = self.calculate_confidence_score(fixture)
                is_premium = result['confidence_score'] >= premium_threshold

                self.generate_prediction(fixture, is_premium=is_premium)
                generated += 1
            except Exception as e:
                logger.error(f'Failed to generate prediction for fixture {fixture.id}: {e}')
                continue

        logger.info(f'Generated {generated} new predictions')
        return generated
