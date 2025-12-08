import pytest
from app import create_app


@pytest.fixture
def app():
    """Create and configure a test app instance using TestingConfig."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()
