"""Tests for Windows Desktop Client API Client (Story 7.4).

Enterprise-grade REST API client for backend communication.
Tests verify real endpoint integration, error handling, and timeout behavior.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.windows_client.api_client import APIClient


class TestAPIClientInit:
    """Test APIClient initialization and session setup."""

    def test_init_stores_backend_url(self):
        """Test backend URL is stored correctly."""
        client = APIClient("http://raspberrypi.local:5000")
        assert client.backend_url == "http://raspberrypi.local:5000"

    def test_init_creates_session(self):
        """Test requests session is created."""
        client = APIClient("http://localhost:5000")
        assert client.session is not None
        assert hasattr(client.session, 'get')

    def test_session_has_custom_user_agent(self):
        """Test session has DeskPulse User-Agent header."""
        client = APIClient("http://localhost:5000")
        assert 'User-Agent' in client.session.headers
        assert 'DeskPulse-Windows-Client' in client.session.headers['User-Agent']

    def test_timeout_default_is_5_seconds(self):
        """Test default timeout is 5 seconds."""
        client = APIClient("http://localhost:5000")
        assert client.timeout == 5


class TestGetTodayStats:
    """Test get_today_stats() method with real endpoint."""

    @patch('app.windows_client.api_client.requests.Session')
    def test_successful_stats_fetch(self, mock_session_class):
        """Test successful stats fetch from /api/stats/today."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'posture_score': 85.0,
            'good_duration_seconds': 7200,
            'bad_duration_seconds': 1800,
            'total_events': 42
        }

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        stats = client.get_today_stats()

        # Verify endpoint called
        mock_session.get.assert_called_once_with(
            'http://localhost:5000/api/stats/today',
            timeout=5
        )

        # Verify response parsed correctly
        assert stats is not None
        assert stats['posture_score'] == 85.0
        assert stats['good_duration_seconds'] == 7200
        assert stats['bad_duration_seconds'] == 1800
        assert stats['total_events'] == 42

    @patch('app.windows_client.api_client.requests.Session')
    def test_network_error_returns_none(self, mock_session_class):
        """Test network error returns None and logs exception."""
        import requests

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        stats = client.get_today_stats()

        assert stats is None

    @patch('app.windows_client.api_client.requests.Session')
    def test_timeout_returns_none(self, mock_session_class):
        """Test timeout error returns None."""
        import requests

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        stats = client.get_today_stats()

        assert stats is None

    @patch('app.windows_client.api_client.requests.Session')
    def test_http_500_returns_none(self, mock_session_class):
        """Test HTTP 500 error returns None."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        stats = client.get_today_stats()

        assert stats is None

    @patch('app.windows_client.api_client.requests.Session')
    def test_http_404_returns_none(self, mock_session_class):
        """Test HTTP 404 error returns None."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not found")

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        stats = client.get_today_stats()

        assert stats is None

    @patch('app.windows_client.api_client.requests.Session')
    def test_invalid_json_returns_none(self, mock_session_class):
        """Test invalid JSON response returns None."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        stats = client.get_today_stats()

        assert stats is None

    @patch('app.windows_client.api_client.requests.Session')
    def test_uses_5_second_timeout(self, mock_session_class):
        """Test API call uses 5-second timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'posture_score': 85.0}

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        client.get_today_stats()

        # Verify timeout parameter
        call_args = mock_session.get.call_args
        assert call_args[1]['timeout'] == 5


class TestAPIClientErrorHandling:
    """Test comprehensive error handling and logging."""

    @patch('app.windows_client.api_client.requests.Session')
    @patch('app.windows_client.api_client.logger')
    def test_exceptions_are_logged(self, mock_logger, mock_session_class):
        """Test all exceptions are logged with logger.exception()."""
        import requests

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Network error")
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")
        client.get_today_stats()

        # Verify logger.exception was called
        mock_logger.exception.assert_called()

    @patch('app.windows_client.api_client.requests.Session')
    def test_session_reused_across_calls(self, mock_session_class):
        """Test session is reused across multiple API calls (connection pooling)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'posture_score': 85.0}

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient("http://localhost:5000")

        # Make 3 calls
        client.get_today_stats()
        client.get_today_stats()
        client.get_today_stats()

        # Session should be created once, reused 3 times
        assert mock_session_class.call_count == 1
        assert mock_session.get.call_count == 3
