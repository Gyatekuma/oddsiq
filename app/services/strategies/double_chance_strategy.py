"""Double Chance prediction strategy."""
import logging
from .base_market_strategy import BaseMarketStrategy

logger = logging.getLogger(__name__)


class DoubleChanceStrategy(BaseMarketStrategy):
    """
    Strategy for Double Chance predictions.

    Double Chance covers two of three outcomes:
    - 1X: Home win OR Draw
    - X2: Draw OR Away win
    - 12: Home win OR Away win (no draw)

    Uses the existing 1X2 prediction logic to calculate
    individual probabilities, then combines them.
    """

    @property
    def market_type(self) -> str:
        return 'double_chance'

    @property
    def market_name(self) -> str:
        return 'Double Chance'

    def get_valid_outcomes(self) -> list:
        return ['1X', 'X2', '12']

    def get_1x2_probabilities(self, fixture):
        """
        Calculate individual home/draw/away probabilities.

        Reuses logic from the main prediction service.
        """
        from ..prediction_service import PredictionService

        try:
            pred_service = PredictionService()
            result = pred_service.calculate_confidence_score(fixture)

            home_score = result.get('home_score', 0.5)
            away_score = result.get('away_score', 0.5)

            # Convert scores to rough probabilities
            total = home_score + away_score
            if total > 0:
                home_prob = home_score / total
                away_prob = away_score / total
            else:
                home_prob = 0.45
                away_prob = 0.35

            # Estimate draw probability based on score difference
            score_diff = abs(home_score - away_score)
            if score_diff < 0.05:
                draw_prob = 0.30
            elif score_diff < 0.10:
                draw_prob = 0.25
            elif score_diff < 0.20:
                draw_prob = 0.22
            else:
                draw_prob = 0.18

            # Normalize so they sum to 1
            total_prob = home_prob + draw_prob + away_prob
            home_prob /= total_prob
            draw_prob /= total_prob
            away_prob /= total_prob

            return {
                'home': home_prob,
                'draw': draw_prob,
                'away': away_prob
            }
        except Exception as e:
            logger.error(f"Failed to get 1X2 probabilities: {e}")
            # Return defaults
            return {
                'home': 0.40,
                'draw': 0.25,
                'away': 0.35
            }

    def _calculate_confidence_for_probability(self, probability):
        """Convert raw probability to confidence score."""
        # Double chance typically has high confidence since it covers 2 outcomes
        if probability >= 0.70:
            confidence_score = 0.70 + (probability - 0.70) * 0.5
        elif probability >= 0.60:
            confidence_score = 0.60 + (probability - 0.60)
        else:
            confidence_score = 0.50 + (probability - 0.50) * 0.8

        # Cap between 0.55 and 0.85
        return max(0.55, min(0.85, confidence_score))

    def calculate_prediction(self, fixture, outcome=None, **kwargs):
        """
        Calculate Double Chance prediction.

        Args:
            fixture: Fixture model instance
            outcome: Specific outcome to predict ('1X', 'X2', '12'). If None, predicts the most likely.

        Returns:
            dict with predicted_outcome, confidence_score, etc.
        """
        probs = self.get_1x2_probabilities(fixture)

        # Calculate double chance probabilities
        dc_1x = probs['home'] + probs['draw']  # Home or Draw
        dc_x2 = probs['draw'] + probs['away']  # Draw or Away
        dc_12 = probs['home'] + probs['away']  # Home or Away

        double_chances = {
            '1X': dc_1x,
            'X2': dc_x2,
            '12': dc_12
        }

        extra_data = {
            '1X_probability': round(dc_1x * 100, 1),
            'X2_probability': round(dc_x2 * 100, 1),
            '12_probability': round(dc_12 * 100, 1),
            'home_probability': round(probs['home'] * 100, 1),
            'draw_probability': round(probs['draw'] * 100, 1),
            'away_probability': round(probs['away'] * 100, 1)
        }

        # If specific outcome requested, return that
        if outcome in double_chances:
            probability = double_chances[outcome]
            confidence_score = self._calculate_confidence_for_probability(probability)
            return {
                'predicted_outcome': outcome,
                'confidence_score': confidence_score,
                'model_probability': probability,
                'line_value': None,
                'extra_data': extra_data
            }

        # Default: return the most likely outcome
        best_outcome = max(double_chances, key=double_chances.get)
        best_probability = double_chances[best_outcome]
        confidence_score = self._calculate_confidence_for_probability(best_probability)

        return {
            'predicted_outcome': best_outcome,
            'confidence_score': confidence_score,
            'model_probability': best_probability,
            'line_value': None,
            'extra_data': extra_data
        }

    def calculate_all_outcomes(self, fixture):
        """
        Calculate predictions for ALL three double chance options.

        Returns:
            list of dicts with predictions for 1X, X2, and 12
        """
        probs = self.get_1x2_probabilities(fixture)

        # Calculate double chance probabilities
        dc_1x = probs['home'] + probs['draw']  # Home or Draw
        dc_x2 = probs['draw'] + probs['away']  # Draw or Away
        dc_12 = probs['home'] + probs['away']  # Home or Away

        double_chances = {
            '1X': dc_1x,
            'X2': dc_x2,
            '12': dc_12
        }

        extra_data = {
            '1X_probability': round(dc_1x * 100, 1),
            'X2_probability': round(dc_x2 * 100, 1),
            '12_probability': round(dc_12* 100, 1),
            'home_probability': round(probs['home'] * 100, 1),
            'draw_probability': round(probs['draw'] * 100, 1),
            'away_probability': round(probs['away'] * 100, 1)
        }

        results = []
        for outcome, probability in double_chances.items():
            confidence_score = self._calculate_confidence_for_probability(probability)
            results.append({
                'predicted_outcome': outcome,
                'confidence_score': confidence_score,
                'model_probability': probability,
                'line_value': None,
                'extra_data': extra_data
            })

        return results

    def get_outcome_description(self, outcome):
        """Get human-readable description of the outcome."""
        descriptions = {
            '1X': 'Home Win or Draw',
            'X2': 'Draw or Away Win',
            '12': 'Home Win or Away Win'
        }
        return descriptions.get(outcome, outcome)
