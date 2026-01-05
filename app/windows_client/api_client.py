"""DeskPulse Windows Desktop Client - REST API Client (Story 7.4).

Enterprise-Grade API Client:
- Real backend REST endpoints (NO MOCK DATA)
- Comprehensive error handling with logging
- 5-second timeout (prevents hanging)
- Session reuse for connection pooling
- URL validation for security (H3 fix)
"""
import logging
import requests
import re
from typing import Optional, Dict
from urllib.parse import urlparse

logger = logging.getLogger('deskpulse.windows.api')


class APIClient:
    """
    REST API client for DeskPulse backend communication.

    Handles:
    - GET /api/stats/today for daily statistics
    - HTTP session management with connection pooling
    - Comprehensive error handling (network, timeout, HTTP errors)
    - 5-second timeout on all requests
    """

    def __init__(self, backend_url: str):
        """
        Initialize API client.

        Args:
            backend_url: Backend URL (e.g., http://raspberrypi.local:5000)

        Raises:
            ValueError: If backend_url is invalid or not a local network address

        Security (H3 fix):
            - Validates URL format
            - Restricts to local network addresses (localhost, LAN, mDNS)
            - Prevents arbitrary external URLs
        """
        # Validate and sanitize backend URL (H3 fix)
        self.backend_url = self._validate_backend_url(backend_url)
        self.timeout = 5  # 5-second timeout (prevents hanging)

        # Create session with custom User-Agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DeskPulse-Windows-Client/1.0'
        })

        # Log sanitized URL (no credentials - M4 fix)
        logger.info(f"APIClient initialized for backend: {self._sanitize_url_for_logging(self.backend_url)}")

    def _validate_backend_url(self, url: str) -> str:
        """
        Validate backend URL for security (H3 fix).

        Enterprise-grade URL validation:
        - Must be valid HTTP/HTTPS URL
        - Must be local network address (localhost, 192.168.x.x, 10.x.x.x, .local mDNS)
        - No credentials allowed in URL
        - Prevents SSRF attacks

        Args:
            url: Backend URL to validate

        Returns:
            str: Sanitized URL with trailing slash removed

        Raises:
            ValueError: If URL is invalid or not local network
        """
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid backend URL format: {url}") from e

        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Backend URL must use http or https (got: {parsed.scheme})")

        # Validate hostname exists
        if not parsed.hostname:
            raise ValueError(f"Backend URL must have a hostname: {url}")

        hostname = parsed.hostname.lower()

        # Security: Disallow credentials in URL (H3 fix)
        if parsed.username or parsed.password:
            raise ValueError("Backend URL must not contain credentials")

        # Security: Restrict to local network addresses (H3 fix)
        is_local = (
            hostname in ('localhost', '127.0.0.1', '::1') or
            hostname.endswith('.local') or  # mDNS (raspberrypi.local)
            hostname.startswith('192.168.') or  # Private LAN
            hostname.startswith('10.') or  # Private LAN
            re.match(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.', hostname)  # Private LAN
        )

        if not is_local:
            raise ValueError(
                f"Backend URL must be local network address (localhost, LAN, or .local mDNS). "
                f"Got: {hostname}"
            )

        # Return sanitized URL (no trailing slash)
        return url.rstrip('/')

    def _sanitize_url_for_logging(self, url: str) -> str:
        """
        Sanitize URL for logging (M4 fix).

        Removes credentials if present (should never happen due to validation).

        Args:
            url: URL to sanitize

        Returns:
            str: URL with credentials removed
        """
        try:
            parsed = urlparse(url)
            # Reconstruct URL without credentials
            sanitized = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port:
                sanitized += f":{parsed.port}"
            sanitized += parsed.path
            if parsed.query:
                sanitized += f"?{parsed.query}"
            return sanitized
        except Exception:
            return url  # Fall back to original if parsing fails

    def get_today_stats(self) -> Optional[Dict]:
        """
        Fetch today's posture statistics from backend.

        Endpoint: GET /api/stats/today
        Returns real data from backend (NO MOCK DATA).

        Returns:
            dict: Stats dictionary with keys:
                - posture_score: float (0-100)
                - good_duration_seconds: int
                - bad_duration_seconds: int
                - total_events: int
            None: If request fails (network error, timeout, HTTP error, invalid JSON)

        Error Handling:
            - Network unreachable: Returns None, logs exception
            - HTTP timeout (5s): Returns None, logs exception
            - HTTP 4xx/5xx: Returns None, logs exception
            - JSON parse error: Returns None, logs exception
        """
        endpoint = f"{self.backend_url}/api/stats/today"

        try:
            # Make GET request with 5-second timeout
            response = self.session.get(endpoint, timeout=self.timeout)

            # Raise exception for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Parse JSON response
            stats = response.json()

            logger.info(f"Successfully fetched today's stats: score={stats.get('posture_score', 0):.0f}%")
            return stats

        except requests.exceptions.Timeout:
            logger.exception(f"Timeout fetching stats from {endpoint}")
            return None

        except requests.exceptions.ConnectionError:
            logger.exception(f"Connection error fetching stats from {endpoint}")
            return None

        except requests.exceptions.HTTPError as e:
            # M3 fix: Differentiate 4xx (client error) vs 5xx (server error)
            status_code = e.response.status_code if e.response else 0
            if 400 <= status_code < 500:
                logger.warning(f"Client error ({status_code}) fetching stats from {endpoint}: {e}")
            else:
                logger.exception(f"Server error ({status_code}) fetching stats from {endpoint}: {e}")
            return None

        except Exception as e:
            # Catch all other exceptions (JSON parse errors, etc.)
            logger.exception(f"Unexpected error fetching stats from {endpoint}: {e}")
            return None
