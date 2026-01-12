"""Unit tests for PostureAnalytics.calculate_trend() method.

Story 4.5: Trend Calculation and Progress Messaging
Tests trend classification, edge cases, and message generation.
"""

import pytest
from datetime import date, timedelta
from app.data.analytics import PostureAnalytics


class TestCalculateTrend:
    """Test suite for calculate_trend() static method."""

    def test_improving_trend(self):
        """Test improving trend (score change > 10 points)."""
        # Create 7-day history with 20-point improvement
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 50.0, 'good_duration_seconds': 3600, 'bad_duration_seconds': 3600, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 55.0, 'good_duration_seconds': 3960, 'bad_duration_seconds': 3240, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 60.0, 'good_duration_seconds': 4320, 'bad_duration_seconds': 2880, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 62.0, 'good_duration_seconds': 4464, 'bad_duration_seconds': 2736, 'user_present_duration_seconds': 7200, 'total_events': 13},
            {'date': date.today() - timedelta(days=2), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 68.0, 'good_duration_seconds': 4896, 'bad_duration_seconds': 2304, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 70.0, 'good_duration_seconds': 5040, 'bad_duration_seconds': 2160, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'improving'
        assert result['score_change'] == 20.0  # 70 - 50
        assert result['average_score'] == 61.4  # (50+55+60+62+65+68+70)/7 ≈ 61.4
        assert result['best_day']['posture_score'] == 70.0
        assert "improved" in result['improvement_message'].lower()
        assert "20.0 points" in result['improvement_message']

    def test_declining_trend(self):
        """Test declining trend (score change < -10 points)."""
        # Create 7-day history with 15-point decline
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 75.0, 'good_duration_seconds': 5400, 'bad_duration_seconds': 1800, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 72.0, 'good_duration_seconds': 5184, 'bad_duration_seconds': 2016, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 70.0, 'good_duration_seconds': 5040, 'bad_duration_seconds': 2160, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 68.0, 'good_duration_seconds': 4896, 'bad_duration_seconds': 2304, 'user_present_duration_seconds': 7200, 'total_events': 13},
            {'date': date.today() - timedelta(days=2), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 63.0, 'good_duration_seconds': 4536, 'bad_duration_seconds': 2664, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 60.0, 'good_duration_seconds': 4320, 'bad_duration_seconds': 2880, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'declining'
        assert result['score_change'] == -15.0  # 60 - 75
        assert result['average_score'] == 67.6  # (75+72+70+68+65+63+60)/7 ≈ 67.6
        assert result['best_day']['posture_score'] == 75.0
        assert "decreased" in result['improvement_message'].lower()
        assert "15.0 points" in result['improvement_message']

    def test_stable_trend_positive(self):
        """Test stable trend with small positive change (+8 points)."""
        # Create 7-day history with 8-point change (within ±10 threshold)
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 60.0, 'good_duration_seconds': 4320, 'bad_duration_seconds': 2880, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 62.0, 'good_duration_seconds': 4464, 'bad_duration_seconds': 2736, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 63.0, 'good_duration_seconds': 4536, 'bad_duration_seconds': 2664, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 13},
            {'date': date.today() - timedelta(days=2), 'posture_score': 66.0, 'good_duration_seconds': 4752, 'bad_duration_seconds': 2448, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 67.0, 'good_duration_seconds': 4824, 'bad_duration_seconds': 2376, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 68.0, 'good_duration_seconds': 4896, 'bad_duration_seconds': 2304, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'stable'
        assert result['score_change'] == 8.0  # 68 - 60
        assert result['average_score'] == 64.4  # (60+62+63+65+66+67+68)/7 ≈ 64.4
        assert "stable" in result['improvement_message'].lower()
        assert "consistency" in result['improvement_message'].lower()

    def test_stable_trend_negative(self):
        """Test stable trend with small negative change (-7 points)."""
        # Create 7-day history with -7-point change (within ±10 threshold)
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 68.0, 'good_duration_seconds': 4896, 'bad_duration_seconds': 2304, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 67.0, 'good_duration_seconds': 4824, 'bad_duration_seconds': 2376, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 66.0, 'good_duration_seconds': 4752, 'bad_duration_seconds': 2448, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 13},
            {'date': date.today() - timedelta(days=2), 'posture_score': 64.0, 'good_duration_seconds': 4608, 'bad_duration_seconds': 2592, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 62.0, 'good_duration_seconds': 4464, 'bad_duration_seconds': 2736, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 61.0, 'good_duration_seconds': 4392, 'bad_duration_seconds': 2808, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'stable'
        assert result['score_change'] == -7.0  # 61 - 68
        assert "stable" in result['improvement_message'].lower()

    def test_insufficient_data_empty_list(self):
        """Test insufficient data with empty history list."""
        history = []

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'insufficient_data'
        assert result['average_score'] == 0.0
        assert result['score_change'] == 0.0
        assert result['best_day'] is None
        assert "keep monitoring" in result['improvement_message'].lower()

    def test_insufficient_data_single_day(self):
        """Test insufficient data with single day of history."""
        history = [
            {'date': date.today(), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 10},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'insufficient_data'
        assert result['average_score'] == 0.0
        assert result['score_change'] == 0.0
        assert result['best_day'] is None
        assert "keep monitoring" in result['improvement_message'].lower()

    def test_edge_case_all_zero_scores(self):
        """Test edge case with all zero posture scores."""
        # Create 7-day history with all zero scores (new user, no events)
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
            {'date': date.today() - timedelta(days=5), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
            {'date': date.today() - timedelta(days=4), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
            {'date': date.today() - timedelta(days=3), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
            {'date': date.today() - timedelta(days=2), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
            {'date': date.today() - timedelta(days=1), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
            {'date': date.today(), 'posture_score': 0.0, 'good_duration_seconds': 0, 'bad_duration_seconds': 0, 'user_present_duration_seconds': 0, 'total_events': 0},
        ]

        result = PostureAnalytics.calculate_trend(history)

        # 0 - 0 = 0 change, falls in stable range (-10 to 10)
        assert result['trend'] == 'stable'
        assert result['score_change'] == 0.0
        assert result['average_score'] == 0.0
        assert result['best_day']['posture_score'] == 0.0
        assert "stable" in result['improvement_message'].lower()

    def test_edge_case_identical_scores(self):
        """Test edge case with identical scores across all days."""
        # Create 7-day history with identical 65% scores
        history = [
            {'date': date.today() - timedelta(days=i), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 10}
            for i in range(6, -1, -1)
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'stable'
        assert result['score_change'] == 0.0  # 65 - 65
        assert result['average_score'] == 65.0
        assert result['best_day']['posture_score'] == 65.0
        assert "stable" in result['improvement_message'].lower()

    def test_edge_case_large_improvement(self):
        """Test edge case with large score improvement (30+ points)."""
        # Create 7-day history with 35-point improvement
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 30.0, 'good_duration_seconds': 2160, 'bad_duration_seconds': 5040, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 35.0, 'good_duration_seconds': 2520, 'bad_duration_seconds': 4680, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 42.0, 'good_duration_seconds': 3024, 'bad_duration_seconds': 4176, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 50.0, 'good_duration_seconds': 3600, 'bad_duration_seconds': 3600, 'user_present_duration_seconds': 7200, 'total_events': 13},
            {'date': date.today() - timedelta(days=2), 'posture_score': 55.0, 'good_duration_seconds': 3960, 'bad_duration_seconds': 3240, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 60.0, 'good_duration_seconds': 4320, 'bad_duration_seconds': 2880, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['trend'] == 'improving'
        assert result['score_change'] == 35.0  # 65 - 30
        assert "improved" in result['improvement_message'].lower()
        assert "35.0 points" in result['improvement_message']

    def test_best_day_identification(self):
        """Test that best_day correctly identifies the highest score day."""
        # Create 7-day history with peak in the middle
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 60.0, 'good_duration_seconds': 4320, 'bad_duration_seconds': 2880, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 65.0, 'good_duration_seconds': 4680, 'bad_duration_seconds': 2520, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 70.0, 'good_duration_seconds': 5040, 'bad_duration_seconds': 2160, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 80.0, 'good_duration_seconds': 5760, 'bad_duration_seconds': 1440, 'user_present_duration_seconds': 7200, 'total_events': 13},  # BEST DAY
            {'date': date.today() - timedelta(days=2), 'posture_score': 75.0, 'good_duration_seconds': 5400, 'bad_duration_seconds': 1800, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 72.0, 'good_duration_seconds': 5184, 'bad_duration_seconds': 2016, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 70.0, 'good_duration_seconds': 5040, 'bad_duration_seconds': 2160, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        assert result['best_day']['posture_score'] == 80.0
        assert result['best_day']['date'] == date.today() - timedelta(days=3)

    def test_rounding_precision(self):
        """Test that average_score and score_change are rounded to 1 decimal place."""
        # Create history with scores that produce non-round averages
        history = [
            {'date': date.today() - timedelta(days=6), 'posture_score': 61.3, 'good_duration_seconds': 4414, 'bad_duration_seconds': 2786, 'user_present_duration_seconds': 7200, 'total_events': 10},
            {'date': date.today() - timedelta(days=5), 'posture_score': 62.7, 'good_duration_seconds': 4514, 'bad_duration_seconds': 2686, 'user_present_duration_seconds': 7200, 'total_events': 12},
            {'date': date.today() - timedelta(days=4), 'posture_score': 63.9, 'good_duration_seconds': 4601, 'bad_duration_seconds': 2599, 'user_present_duration_seconds': 7200, 'total_events': 11},
            {'date': date.today() - timedelta(days=3), 'posture_score': 65.1, 'good_duration_seconds': 4687, 'bad_duration_seconds': 2513, 'user_present_duration_seconds': 7200, 'total_events': 13},
            {'date': date.today() - timedelta(days=2), 'posture_score': 66.4, 'good_duration_seconds': 4781, 'bad_duration_seconds': 2419, 'user_present_duration_seconds': 7200, 'total_events': 14},
            {'date': date.today() - timedelta(days=1), 'posture_score': 67.8, 'good_duration_seconds': 4882, 'bad_duration_seconds': 2318, 'user_present_duration_seconds': 7200, 'total_events': 15},
            {'date': date.today(), 'posture_score': 69.2, 'good_duration_seconds': 4982, 'bad_duration_seconds': 2218, 'user_present_duration_seconds': 7200, 'total_events': 16},
        ]

        result = PostureAnalytics.calculate_trend(history)

        # Check that results are rounded to 1 decimal place
        assert isinstance(result['average_score'], float)
        assert isinstance(result['score_change'], float)
        # Verify rounding (average should be ~65.2, change should be 7.9)
        assert result['average_score'] == 65.2
        assert result['score_change'] == 7.9  # 69.2 - 61.3

    def test_input_validation_non_list(self):
        """Test input validation rejects non-list input (Code Review Fix #1)."""
        with pytest.raises(TypeError, match="history must be a list"):
            PostureAnalytics.calculate_trend("not a list")

        with pytest.raises(TypeError, match="history must be a list"):
            PostureAnalytics.calculate_trend(None)

        with pytest.raises(TypeError, match="history must be a list"):
            PostureAnalytics.calculate_trend({'date': date.today(), 'posture_score': 50.0})

    def test_input_validation_non_dict_elements(self):
        """Test input validation rejects non-dict elements (Code Review Fix #1)."""
        history = [
            {'date': date.today(), 'posture_score': 50.0},
            "not a dict",  # Invalid element
        ]

        with pytest.raises(TypeError, match="history\\[1\\] must be dict"):
            PostureAnalytics.calculate_trend(history)

    def test_input_validation_missing_posture_score(self):
        """Test input validation rejects dicts missing posture_score key (Code Review Fix #1)."""
        history = [
            {'date': date.today(), 'posture_score': 50.0},
            {'date': date.today() - timedelta(days=1)},  # Missing posture_score
        ]

        with pytest.raises(ValueError, match="history\\[1\\] missing required 'posture_score' key"):
            PostureAnalytics.calculate_trend(history)

    def test_nan_infinity_handling(self):
        """Test NaN/Infinity handling in trend calculation (Code Review Fix #9)."""
        import math

        # Test with NaN score (data corruption scenario)
        history = [
            {'date': date.today() - timedelta(days=1), 'posture_score': math.nan},
            {'date': date.today(), 'posture_score': 65.0},
        ]

        result = PostureAnalytics.calculate_trend(history)

        # Should return insufficient_data when NaN detected
        assert result['trend'] == 'insufficient_data'
        assert result['average_score'] == 0.0
        assert result['score_change'] == 0.0
        assert 'data quality issues' in result['improvement_message'].lower()
