"""Integration tests for /api/stats/trend endpoint.

Story 4.5: Trend Calculation and Progress Messaging
Tests REST API endpoint response structure, trend classification, and error handling.
"""

import pytest
from datetime import date, timedelta
from app import create_app
from app.data.repository import PostureEventRepository


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Create app context for database operations."""
    with app.app_context():
        yield


class TestTrendEndpoint:
    """Test suite for /api/stats/trend endpoint."""

    def test_endpoint_exists(self, client):
        """Test that /api/stats/trend endpoint exists and returns 200."""
        response = client.get('/api/stats/trend')
        assert response.status_code == 200

    def test_response_structure(self, client):
        """Test that response contains all required fields."""
        response = client.get('/api/stats/trend')
        data = response.get_json()

        # Verify all required fields present
        assert 'trend' in data
        assert 'average_score' in data
        assert 'score_change' in data
        assert 'best_day' in data
        assert 'improvement_message' in data

    def test_trend_field_values(self, client):
        """Test that trend field contains valid classification."""
        response = client.get('/api/stats/trend')
        data = response.get_json()

        # Trend must be one of the valid classifications
        valid_trends = ['improving', 'stable', 'declining', 'insufficient_data']
        assert data['trend'] in valid_trends

    def test_stable_trend_empty_database(self, client, app_context):
        """Test stable trend with empty database (7 days of zero scores)."""
        # Empty database returns 7 days of all-zero scores
        # This gives stable trend (score_change = 0, within ±10 threshold)
        response = client.get('/api/stats/trend')
        data = response.get_json()

        assert data['trend'] == 'stable'
        assert data['average_score'] == 0.0
        assert data['score_change'] == 0.0
        assert data['best_day']['posture_score'] == 0.0
        assert 'stable' in data['improvement_message'].lower()

    def test_json_serialization_dates(self, client):
        """Test that date objects are properly serialized to ISO 8601 strings."""
        # Test with current database state (empty or populated)
        response = client.get('/api/stats/trend')
        data = response.get_json()

        # Verify best_day date is serialized (even if all zeros, best_day exists)
        assert data['best_day'] is not None
        assert 'date' in data['best_day']
        assert isinstance(data['best_day']['date'], str)
        # Verify ISO 8601 format (YYYY-MM-DD)
        assert len(data['best_day']['date']) == 10
        assert data['best_day']['date'][4] == '-'
        assert data['best_day']['date'][7] == '-'

    def test_content_type(self, client):
        """Test that response has correct JSON content type."""
        response = client.get('/api/stats/trend')
        assert response.content_type == 'application/json'

    def test_http_method_get_only(self, client):
        """Test that endpoint only accepts GET requests."""
        # GET should work
        response = client.get('/api/stats/trend')
        assert response.status_code == 200

        # POST should fail
        response = client.post('/api/stats/trend')
        assert response.status_code == 405  # Method Not Allowed

        # PUT should fail
        response = client.put('/api/stats/trend')
        assert response.status_code == 405

        # DELETE should fail
        response = client.delete('/api/stats/trend')
        assert response.status_code == 405

    def test_numeric_precision(self, client):
        """Test that average_score and score_change are rounded to 1 decimal."""
        response = client.get('/api/stats/trend')
        data = response.get_json()

        # Verify numeric types
        assert isinstance(data['average_score'], (int, float))
        assert isinstance(data['score_change'], (int, float))

        # If data exists, verify precision (1 decimal place)
        if data['average_score'] != 0.0:
            # Count decimal places
            avg_str = str(data['average_score'])
            if '.' in avg_str:
                decimals = len(avg_str.split('.')[1])
                assert decimals <= 1, f"average_score has {decimals} decimals, expected ≤1"

        if data['score_change'] != 0.0:
            change_str = str(data['score_change'])
            if '.' in change_str:
                decimals = len(change_str.split('.')[1])
                assert decimals <= 1, f"score_change has {decimals} decimals, expected ≤1"

    def test_improvement_message_exists(self, client):
        """Test that improvement_message is always a non-empty string."""
        response = client.get('/api/stats/trend')
        data = response.get_json()

        assert isinstance(data['improvement_message'], str)
        assert len(data['improvement_message']) > 0

    def test_stable_trend_message_format(self, client):
        """Test message format for stable trend."""
        response = client.get('/api/stats/trend')
        data = response.get_json()

        if data['trend'] == 'stable':
            # Stable message should mention "stable" or "consistency"
            message_lower = data['improvement_message'].lower()
            assert 'stable' in message_lower or 'consistency' in message_lower

    def test_insufficient_data_message_format(self, client):
        """Test message format for insufficient_data trend."""
        response = client.get('/api/stats/trend')
        data = response.get_json()

        if data['trend'] == 'insufficient_data':
            # Message should encourage monitoring
            message_lower = data['improvement_message'].lower()
            assert 'keep monitoring' in message_lower or 'progress' in message_lower

    def test_error_handling_get_history_exception(self, client, monkeypatch):
        """Test error handling when get_7_day_history raises exception (Code Review Fix #3)."""
        def mock_get_history_error():
            raise RuntimeError("Simulated database error")

        # Monkey-patch the get_7_day_history method to raise exception
        monkeypatch.setattr('app.api.routes.PostureAnalytics.get_7_day_history', mock_get_history_error)

        response = client.get('/api/stats/trend')

        # Should return 500 error with error message
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Failed to calculate trend'

    def test_error_handling_calculate_trend_exception(self, client, monkeypatch):
        """Test error handling when calculate_trend raises exception (Code Review Fix #3)."""
        def mock_calculate_trend_error(history):
            raise ValueError("Simulated calculation error")

        # Monkey-patch the calculate_trend method to raise exception
        monkeypatch.setattr('app.api.routes.PostureAnalytics.calculate_trend', mock_calculate_trend_error)

        response = client.get('/api/stats/trend')

        # Should return 500 error with error message
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Failed to calculate trend'
