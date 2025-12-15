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


@pytest.fixture
def app(mock_cv_pipeline_global):
    """Create and configure a test app instance using TestingConfig."""
    import app as app_module

    # Create Flask app
    flask_app = create_app("testing")

    # Ensure mock persists after app creation (defensive)
    app_module.cv_pipeline = mock_cv_pipeline_global

    # Also store on Flask app instance for handler access
    flask_app.cv_pipeline_test = mock_cv_pipeline_global

    yield flask_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()
