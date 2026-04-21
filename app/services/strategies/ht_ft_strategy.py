"""Half-time/Full-time prediction strategy."""
import logging
from .base_market_strategy import BaseMarketStrategy

logger = logging.getLogger(__name__)


class HTFTStrategy(BaseMarketStrategy):
    """
    Strategy for Half-time/Full-time predictions.

    Predicts the outcome at half-time AND full-time.
    9 possible combinations:
    - home_home, home_draw, home_away
    - draw_home, draw_draw, draw_away
    - away_home, away_draw, away_away

    Uses:
    - Full-time prediction (from main service)
    - Historical HT lead rates
    - Comeback statistics
    """

    OUTCOMES = [
        'home_home', 'home_draw', 'home_away',
        'draw_home', 'draw_draw', 'draw_away',
        'away_home', 'away_draw', 'away_away'
    ]

    @property
    def market_type(self) -> str:
        return 'ht_ft'

    @property
    def market_name(self) -> str:
        return 'Half-time/Full-time'

    def get_valid_outcomes(self) -> list:
        return self.OUTCOMES

    def get_ht_probabilities(self, fixture):
        """
        Calculate half-time outcome probabilities.

        Based on team statistics:
        - How often team leads at HT
        - How often matches are drawn at HT
        """
        home_stats = self.get_team_stats(fixture.home_team_id)
        away_stats = self.get_team_stats(fixture.away_team_id)

        # Get HT lead rates
        if hasattr(home_stats, 'get_ht_lead_rate') and home_stats.matches_played > 0:
            home_ht_lead_rate = home_stats.get_ht_lead_rate() / 100
        else:
            home_ht_lead_rate = 0.35  # Default home HT lead rate

        if hasattr(away_stats, 'get_ht_lead_rate') and away_stats.matches_played > 0:
            away_ht_lead_rate = away_stats.get_ht_lead_rate() / 100
        else:
            away_ht_lead_rate = 0.25  # Default away HT lead rate

        # Estimate HT draw probability
        # Typically 30-40% of matches are drawn at HT
        ht_draw_rate = 1 - home_ht_lead_rate - away_ht_lead_rate
        ht_draw_rate = max(0.25, min(0.45, ht_draw_rate))

        # Normalize
        total = home_ht_lead_rate + away_ht_lead_rate + ht_draw_rate
        return {
            'home': home_ht_lead_rate / total,
            'draw': ht_draw_rate / total,
            'away': away_ht_lead_rate / total
        }

    def get_ft_probabilities(self, fixture):
        """Get full-time probabilities from main prediction service."""
        from ..prediction_service import PredictionService

        try:
            pred_service = PredictionService()
            result = pred_service.calculate_confidence_score(fixture)

            home_score = result.get('home_score', 0.5)
            away_score = result.get('away_score', 0.5)
            predicted_outcome = result.get('predicted_outcome', 'draw')

            # Convert to probabilities
            total = home_score + away_score
            if total > 0:
                home_prob = home_score / total
                away_prob = away_score / total
            else:
                home_prob = 0.40
                away_prob = 0.35

            # Estimate draw probability
            score_diff = abs(home_score - away_score)
            if score_diff < 0.05:
                draw_prob = 0.30
            elif score_diff < 0.10:
                draw_prob = 0.25
            else:
                draw_prob = 0.20

            # Normalize
            total_prob = home_prob + draw_prob + away_prob
            return {
                'home': home_prob / total_prob,
                'draw': draw_prob / total_prob,
                'away': away_prob / total_prob
            }
        except Exception as e:
            logger.error(f"Failed to get FT probabilities: {e}")
            return {'home': 0.40, 'draw': 0.25, 'away': 0.35}

    def calculate_prediction(self, fixture, **kwargs):
        """
        Calculate HT/FT prediction.

        Calculates probability for each of 9 combinations and selects the best.

        Key insight: HT and FT outcomes are correlated but not identical.
        - Teams leading at HT usually win (but not always)
        - HT draws can go any way at FT
        """
        ht_probs = self.get_ht_probabilities(fixture)
        ft_probs = self.get_ft_probabilities(fixture)

        # Calculate conditional probabilities
        # P(FT|HT) - probability of full-time outcome given half-time outcome
        htft_probs = {}

        # If home leads at HT
        htft_probs['home_home'] = ht_probs['home'] * 0.75  # 75% of HT leaders win
        htft_probs['home_draw'] = ht_probs['home'] * 0.18  # 18% draw
        htft_probs['home_away'] = ht_probs['home'] * 0.07  # 7% lose (rare)

        # If drawn at HT
        htft_probs['draw_home'] = ht_probs['draw'] * ft_probs['home'] * 0.9
        htft_probs['draw_draw'] = ht_probs['draw'] * 0.35  # HT draws often stay draws
        htft_probs['draw_away'] = ht_probs['draw'] * ft_probs['away'] * 0.9

        # If away leads at HT
        htft_probs['away_home'] = ht_probs['away'] * 0.08  # Rare comeback
        htft_probs['away_draw'] = ht_probs['away'] * 0.17
        htft_probs['away_away'] = ht_probs['away'] * 0.75

        # Normalize
        total = sum(htft_probs.values())
        for outcome in htft_probs:
            htft_probs[outcome] /= total

        # Find best outcome
        best_outcome = max(htft_probs, key=htft_probs.get)
        best_probability = htft_probs[best_outcome]

        # HT/FT is hard to predict, so confidence is capped lower
        if best_probability >= 0.30:
            confidence_score = 0.55 + (best_probability - 0.30) * 0.5
        elif best_probability >= 0.20:
            confidence_score = 0.45 + (best_probability - 0.20)
        else:
            confidence_score = 0.35 + (best_probability * 0.5)

        # Cap between 0.25 and 0.65 (HT/FT is difficult)
        confidence_score = max(0.25, min(0.65, confidence_score))

        return {
            'predicted_outcome': best_outcome,
            'confidence_score': confidence_score,
            'model_probability': best_probability,
            'line_value': None,
            'extra_data': {
                'all_probabilities': {k: round(v * 100, 1) for k, v in htft_probs.items()},
                'ht_probabilities': {k: round(v * 100, 1) for k, v in ht_probs.items()},
                'ft_probabilities': {k: round(v * 100, 1) for k, v in ft_probs.items()}
            }
        }

    def get_outcome_description(self, outcome):
        """Get human-readable description of the outcome."""
        ht, ft = outcome.split('_')
        names = {'home': 'Home', 'draw': 'Draw', 'away': 'Away'}
        return f"{names[ht]} / {names[ft]}"
