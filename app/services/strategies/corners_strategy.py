"""Corners Over/Under prediction strategy."""
import logging
from .base_market_strategy import BaseMarketStrategy

logger = logging.getLogger(__name__)


class CornersStrategy(BaseMarketStrategy):
    """
    Strategy for Corners Over/Under predictions.

    Uses team corner statistics to predict expected total corners:
    - Average corners won (attacking style)
    - Average corners conceded (defensive style)

    Typical match average: ~10 corners total
    """

    SUPPORTED_LINES = [7.5, 8.5, 9.5, 10.5, 11.5, 12.5]
    DEFAULT_AVG_CORNERS = 10.0  # Typical match average

    @property
    def market_type(self) -> str:
        return 'corners'

    @property
    def market_name(self) -> str:
        return 'Corners Over/Under'

    def get_valid_outcomes(self) -> list:
        return ['over', 'under']

    def calculate_expected_corners(self, fixture):
        """
        Calculate expected total corners.

        Formula:
        - Expected home corners = (home_corners_for + away_corners_against) / 2
        - Expected away corners = (away_corners_for + home_corners_against) / 2
        - Total = home + away
        """
        home_stats = self.get_team_stats(fixture.home_team_id)
        away_stats = self.get_team_stats(fixture.away_team_id)

        # Get corner averages
        home_corners_for = getattr(home_stats, 'avg_corners_for', 5.0)
        home_corners_against = getattr(home_stats, 'avg_corners_against', 5.0)
        away_corners_for = getattr(away_stats, 'avg_corners_for', 4.5)
        away_corners_against = getattr(away_stats, 'avg_corners_against', 5.0)

        # Calculate expected corners for each team
        # Home teams typically win more corners
        home_expected = ((home_corners_for + away_corners_against) / 2) * 1.05
        away_expected = (away_corners_for + home_corners_against) / 2

        total_expected = home_expected + away_expected

        return {
            'expected_total': total_expected,
            'home_expected': home_expected,
            'away_expected': away_expected
        }

    def _calculate_confidence_for_distance(self, distance, is_over):
        """Calculate confidence based on distance from line."""
        if is_over:
            if distance > 0:
                base_confidence = 0.50 + (distance * 0.08)
            else:
                base_confidence = 0.50 - (abs(distance) * 0.06)
        else:  # under
            if distance < 0:
                base_confidence = 0.50 + (abs(distance) * 0.08)
            else:
                base_confidence = 0.50 - (distance * 0.06)

        # Cap confidence between 0.35 and 0.75 (corners are harder to predict)
        return max(0.35, min(0.75, base_confidence))

    def calculate_prediction(self, fixture, line_value=9.5, outcome=None, **kwargs):
        """
        Calculate Corners Over/Under prediction.

        Args:
            fixture: Fixture model instance
            line_value: The corner line (default 9.5)
            outcome: Specific outcome to predict ('over' or 'under'). If None, predicts the most likely.

        Returns:
            dict with predicted_outcome, confidence_score, etc.
        """
        if line_value not in self.SUPPORTED_LINES:
            line_value = 9.5

        corners_data = self.calculate_expected_corners(fixture)
        expected_total = corners_data['expected_total']

        # Calculate distance from line
        distance = expected_total - line_value

        over_confidence = self._calculate_confidence_for_distance(distance, is_over=True)
        under_confidence = self._calculate_confidence_for_distance(distance, is_over=False)

        extra_data = {
            'expected_total': round(expected_total, 1),
            'home_expected': round(corners_data['home_expected'], 1),
            'away_expected': round(corners_data['away_expected'], 1),
            'over_confidence': round(over_confidence, 3),
            'under_confidence': round(under_confidence, 3)
        }

        # If specific outcome requested, return that
        if outcome == 'over':
            return {
                'predicted_outcome': 'over',
                'confidence_score': over_confidence,
                'model_probability': over_confidence,
                'line_value': line_value,
                'extra_data': extra_data
            }
        elif outcome == 'under':
            return {
                'predicted_outcome': 'under',
                'confidence_score': under_confidence,
                'model_probability': under_confidence,
                'line_value': line_value,
                'extra_data': extra_data
            }

        # Default: return the most likely outcome
        if distance > 0:
            predicted_outcome = 'over'
            confidence_score = over_confidence
        else:
            predicted_outcome = 'under'
            confidence_score = under_confidence

        return {
            'predicted_outcome': predicted_outcome,
            'confidence_score': confidence_score,
            'model_probability': confidence_score,
            'line_value': line_value,
            'extra_data': extra_data
        }

    def calculate_all_outcomes(self, fixture, line_value=9.5):
        """
        Calculate predictions for BOTH over and under for a specific line.

        Returns:
            list of dicts with predictions for both outcomes
        """
        if line_value not in self.SUPPORTED_LINES:
            line_value = 9.5

        corners_data = self.calculate_expected_corners(fixture)
        expected_total = corners_data['expected_total']
        distance = expected_total - line_value

        over_confidence = self._calculate_confidence_for_distance(distance, is_over=True)
        under_confidence = self._calculate_confidence_for_distance(distance, is_over=False)

        extra_data = {
            'expected_total': round(expected_total, 1),
            'home_expected': round(corners_data['home_expected'], 1),
            'away_expected': round(corners_data['away_expected'], 1)
        }

        return [
            {
                'predicted_outcome': 'over',
                'confidence_score': over_confidence,
                'model_probability': over_confidence,
                'line_value': line_value,
                'extra_data': extra_data
            },
            {
                'predicted_outcome': 'under',
                'confidence_score': under_confidence,
                'model_probability': under_confidence,
                'line_value': line_value,
                'extra_data': extra_data
            }
        ]

    def generate_predictions_for_all_lines(self, fixture, is_premium=False, lines=None):
        """
        Generate predictions for multiple corner lines.

        Args:
            fixture: Fixture model instance
            is_premium: Whether to mark as premium
            lines: List of lines to generate (default: [8.5, 9.5, 10.5])

        Returns:
            List of MarketPrediction instances
        """
        if lines is None:
            lines = [8.5, 9.5, 10.5]

        predictions = []
        for line in lines:
            prediction = self.generate_prediction(fixture, is_premium=is_premium, line_value=line)
            if prediction:
                predictions.append(prediction)

        return predictions
