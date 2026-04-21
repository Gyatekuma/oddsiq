"""
Unit tests for the prediction confidence score formula.

Run with: pytest tests/test_predictions.py -v
"""
import pytest
from datetime import datetime, timedelta


class TestPredictionFormulas:
    """Test the prediction service calculations."""

    def test_form_score_all_wins(self):
        """Test form score with all wins (should be 1.0)."""
        # W=3pts, max 15pts for 5 wins
        # Score = 15/15 = 1.0
        from app.models.form_record import FormRecord

        class MockRecord:
            def __init__(self, result):
                self.result = result

        records = [MockRecord('W') for _ in range(5)]
        score = FormRecord.calculate_form_score(records)

        assert score == 1.0

    def test_form_score_all_losses(self):
        """Test form score with all losses (should be 0.0)."""
        from app.models.form_record import FormRecord

        class MockRecord:
            def __init__(self, result):
                self.result = result

        records = [MockRecord('L') for _ in range(5)]
        score = FormRecord.calculate_form_score(records)

        assert score == 0.0

    def test_form_score_all_draws(self):
        """Test form score with all draws."""
        # D=1pt, total 5pts, max 15pts
        # Score = 5/15 = 0.333...
        from app.models.form_record import FormRecord

        class MockRecord:
            def __init__(self, result):
                self.result = result

        records = [MockRecord('D') for _ in range(5)]
        score = FormRecord.calculate_form_score(records)

        assert round(score, 2) == 0.33

    def test_form_score_mixed_results(self):
        """Test form score with mixed results."""
        # 2W, 2D, 1L = 6 + 2 + 0 = 8pts
        # Score = 8/15 = 0.533...
        from app.models.form_record import FormRecord

        class MockRecord:
            def __init__(self, result):
                self.result = result

        records = [
            MockRecord('W'), MockRecord('W'),
            MockRecord('D'), MockRecord('D'),
            MockRecord('L')
        ]
        score = FormRecord.calculate_form_score(records)

        assert round(score, 2) == 0.53

    def test_form_score_empty_records(self):
        """Test form score with no records (should return neutral 0.5)."""
        from app.models.form_record import FormRecord

        score = FormRecord.calculate_form_score([])

        assert score == 0.5

    def test_h2h_score_all_wins_for_team1(self):
        """Test H2H score when team1 won all matches."""
        from app.models.h2h_record import H2HRecord

        class MockH2H:
            def __init__(self, team1_id, result):
                self.team1_id = team1_id
                self.result_for_team1 = result

        records = [MockH2H(1, 'W') for _ in range(5)]
        score = H2HRecord.calculate_h2h_score(records, perspective_team_id=1)

        assert score == 1.0

    def test_h2h_score_from_opponent_perspective(self):
        """Test H2H score from losing team's perspective."""
        from app.models.h2h_record import H2HRecord

        class MockH2H:
            def __init__(self, team1_id, result):
                self.team1_id = team1_id
                self.result_for_team1 = result

        # Team 1 won all 5, so Team 2 lost all 5
        records = [MockH2H(1, 'W') for _ in range(5)]
        score = H2HRecord.calculate_h2h_score(records, perspective_team_id=2)

        assert score == 0.0

    def test_h2h_score_empty(self):
        """Test H2H score with no records (should return neutral 0.5)."""
        from app.models.h2h_record import H2HRecord

        score = H2HRecord.calculate_h2h_score([], perspective_team_id=1)

        assert score == 0.5


class TestValueBetDetection:
    """Test value bet detection logic."""

    def test_value_bet_positive_edge(self):
        """Test that positive edge is detected as value bet."""
        # If model probability = 0.5 and implied probability = 0.4
        # Edge = 0.5 - 0.4 = 0.1 > 0.05 threshold
        model_prob = 0.5
        implied_prob = 0.4  # Odds of 2.5
        threshold = 0.05

        edge = model_prob - implied_prob
        is_value = edge > threshold

        assert is_value == True
        assert edge == 0.1

    def test_value_bet_negative_edge(self):
        """Test that negative edge is not a value bet."""
        model_prob = 0.4
        implied_prob = 0.5  # Odds of 2.0
        threshold = 0.05

        edge = model_prob - implied_prob
        is_value = edge > threshold

        assert is_value == False
        assert edge == -0.1

    def test_value_bet_marginal_edge(self):
        """Test edge at exactly the threshold."""
        model_prob = 0.55
        implied_prob = 0.50  # Odds of 2.0
        threshold = 0.05

        edge = model_prob - implied_prob
        is_value = edge > threshold

        # 0.05 is not > 0.05, so not a value bet
        assert is_value == False

    def test_implied_probability_calculation(self):
        """Test conversion from decimal odds to implied probability."""
        # Decimal odds to probability: 1 / odds
        test_cases = [
            (2.0, 0.5),    # Evens
            (3.0, 0.333),  # 2/1
            (1.5, 0.667),  # 1/2
            (4.0, 0.25),   # 3/1
        ]

        for odds, expected_prob in test_cases:
            implied_prob = 1 / odds
            assert round(implied_prob, 3) == expected_prob


class TestConfidenceScore:
    """Test confidence score calculation."""

    def test_confidence_bounds(self):
        """Test that confidence score is between 0 and 1."""
        # Any calculated confidence should be in valid range
        home_score = 0.7
        away_score = 0.3
        difference = abs(home_score - away_score)

        # Normalize to 0-1 (max typical difference is ~0.4)
        confidence = min(difference / 0.4, 1.0)

        assert 0 <= confidence <= 1

    def test_draw_prediction_threshold(self):
        """Test that close scores predict draw."""
        draw_threshold = 0.05

        # Scores within threshold should predict draw
        home_score = 0.52
        away_score = 0.50
        difference = home_score - away_score

        if abs(difference) < draw_threshold:
            predicted = 'draw'
        elif difference > 0:
            predicted = 'home'
        else:
            predicted = 'away'

        assert predicted == 'draw'

    def test_home_win_prediction(self):
        """Test that higher home score predicts home win."""
        draw_threshold = 0.05

        home_score = 0.7
        away_score = 0.4
        difference = home_score - away_score

        if abs(difference) < draw_threshold:
            predicted = 'draw'
        elif difference > 0:
            predicted = 'home'
        else:
            predicted = 'away'

        assert predicted == 'home'

    def test_away_win_prediction(self):
        """Test that higher away score predicts away win."""
        draw_threshold = 0.05

        home_score = 0.35
        away_score = 0.65
        difference = home_score - away_score

        if abs(difference) < draw_threshold:
            predicted = 'draw'
        elif difference > 0:
            predicted = 'home'
        else:
            predicted = 'away'

        assert predicted == 'away'


class TestWeightedFormula:
    """Test the weighted scoring formula."""

    def test_weight_sum(self):
        """Test that weights are properly distributed."""
        form_weight = 0.30
        h2h_weight = 0.20
        home_advantage_weight = 0.20
        base_score = 0.15  # Half of remaining 30%

        # For home team
        home_advantage_factor = 0.6

        total_weight = form_weight + h2h_weight + home_advantage_weight + base_score

        # Total should be less than 1 (remaining goes to away team)
        assert total_weight == 0.85

    def test_home_advantage_calculation(self):
        """Test home advantage contributes correctly."""
        home_advantage_weight = 0.20
        home_factor = 0.6
        away_factor = 0.4

        home_advantage_contribution = home_factor * home_advantage_weight
        away_advantage_contribution = away_factor * home_advantage_weight

        assert home_advantage_contribution == 0.12
        assert away_advantage_contribution == 0.08

    def test_perfect_form_maximum_contribution(self):
        """Test that perfect form contributes maximum to score."""
        form_weight = 0.30
        perfect_form = 1.0

        contribution = perfect_form * form_weight

        assert contribution == 0.30

    def test_zero_form_no_contribution(self):
        """Test that zero form adds nothing."""
        form_weight = 0.30
        zero_form = 0.0

        contribution = zero_form * form_weight

        assert contribution == 0.0


# Integration test that requires app context
@pytest.fixture
def app():
    """Create application for testing."""
    from app import create_app
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestPredictionServiceIntegration:
    """Integration tests for the prediction service."""

    def test_prediction_service_initialization(self, app):
        """Test that prediction service can be initialized."""
        with app.app_context():
            from app.services.prediction_service import PredictionService
            service = PredictionService()

            assert service.FORM_WEIGHT == 0.30
            assert service.H2H_WEIGHT == 0.20
            assert service.DRAW_THRESHOLD == 0.05
            assert service.VALUE_BET_THRESHOLD == 0.05

    def test_form_score_with_no_team(self, app):
        """Test form score calculation with non-existent team."""
        with app.app_context():
            from app.services.prediction_service import PredictionService
            service = PredictionService()

            # Non-existent team should return neutral score
            score = service.calculate_form_score(team_id=99999)

            assert score == 0.5

    def test_h2h_score_with_no_records(self, app):
        """Test H2H score with non-existent teams."""
        with app.app_context():
            from app.services.prediction_service import PredictionService
            service = PredictionService()

            home_h2h, away_h2h = service.calculate_h2h_score(
                home_team_id=99999,
                away_team_id=99998
            )

            # Should return neutral scores
            assert home_h2h == 0.5
            assert away_h2h == 0.5
