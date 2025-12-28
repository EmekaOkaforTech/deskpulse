import pytest
from unittest.mock import Mock
from app import create_app


@pytest.fixture(scope='session', autouse=True)
def mock_cv_pipeline_global():
    """
    Mock cv_pipeline globally to prevent camera initialization in tests.

    This fixture runs before any tests and prevents the CV pipeline from
    starting during app creation, which would cause timeouts in test environment.
    """
    import app

    # Create mock alert manager with monitoring methods
    mock_alert_manager = Mock()
    mock_alert_manager.pause_monitoring = Mock()
    mock_alert_manager.resume_monitoring = Mock()
    mock_alert_manager.get_monitoring_status = Mock(return_value={
        'monitoring_active': True,
        'threshold_seconds': 600,
        'cooldown_seconds': 300
    })
    mock_alert_manager.monitoring_paused = False

    # Create mock pipeline
    mock_pipeline = Mock()
    mock_pipeline.alert_manager = mock_alert_manager
    mock_pipeline.start = Mock()  # Mock start to prevent camera init
    mock_pipeline.stop = Mock()

    # Set global mock before app creation
    app.cv_pipeline = mock_pipeline

    yield mock_pipeline


@pytest.fixture(scope='session')
def app(mock_cv_pipeline_global):
    """Create and configure a test app instance using TestingConfig.

    Scope: session - single app for all tests (Flask-SocketIO best practice).
    Prevents handler re-registration issues and ensures consistent mock behavior.
    Test isolation maintained via Flask's test request context and pytest's
    function-scoped fixtures.

    Reference: Flask-SocketIO GitHub #510 - handler registration fails when
    app recreated multiple times in same process.
    """
    import app as app_module

    # Create Flask app
    flask_app = create_app("testing")

    # Ensure mock persists after app creation (defensive)
    app_module.cv_pipeline = mock_cv_pipeline_global

    # Also store on Flask app instance for handler access
    flask_app.cv_pipeline_test = mock_cv_pipeline_global

    yield flask_app


@pytest.fixture
def app_context(app):
    """Provide Flask app context using session-scoped app.

    Overrides pytest-flask's default app_context to use our session-scoped
    app fixture. This ensures mock_cv_pipeline_global is visible in all
    tests requiring app context (e.g., AlertManager tests).

    Critical: Without this, pytest-flask creates new context without mocks.
    """
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def mock_camera():
    """Mock camera that returns fake frames for testing.

    Returns numpy arrays (480x640x3 uint8) as fake camera frames.
    Prevents hardware dependency in CV pipeline tests.
    """
    import numpy as np
    camera = Mock()
    camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    return camera


@pytest.fixture
def socketio_client(app):
    """Create SocketIO test client with proper setup.

    Follows Flask-SocketIO official test patterns:
    1. Create test client
    2. Clear initial connection messages
    3. Ready for test assertions

    Reference: Flask-SocketIO test_socketio.py patterns
    """
    from app.extensions import socketio

    # Create test client
    client = socketio.test_client(app)

    # Clear initial connection/status messages (Flask-SocketIO best practice)
    # Connection emits 'status' event - clear before test assertions
    client.get_received()

    yield client

    # Cleanup: disconnect client after test
    if client.is_connected():
        client.disconnect()
