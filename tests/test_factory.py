from app import create_app


def test_config_development():
    """Test development config loads correctly."""
    app = create_app("development")
    assert app.config["DEBUG"] is True
    assert app.config["LOG_LEVEL"] == "DEBUG"


def test_config_testing():
    """Test testing config loads correctly."""
    app = create_app("testing")
    assert app.config["TESTING"] is True
    assert app.config["DATABASE_PATH"] == ":memory:"
    assert app.config["MOCK_CAMERA"] is True


def test_config_production():
    """Test production config loads correctly."""
    app = create_app("production")
    assert app.config["DEBUG"] is False
    assert app.config["LOG_LEVEL"] == "INFO"


def test_config_systemd():
    """Test systemd config loads correctly."""
    app = create_app("systemd")
    assert app.config["DEBUG"] is False
    assert app.config["LOG_LEVEL"] == "WARNING"
    # SystemdConfig inherits from ProductionConfig
    assert app.config["HOST"] == "127.0.0.1"


def test_blueprints_registered(app):
    """Test that blueprints are registered."""
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    assert "main" in blueprint_names
    assert "api" in blueprint_names


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "DeskPulse"
