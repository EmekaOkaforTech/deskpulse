import logging
from flask import jsonify
from app.main import bp

# Hierarchical logger for API routes (AC2)
logger = logging.getLogger("deskpulse.api")


@bp.route("/")
def index():
    logger.debug("API request: method=GET path=/")
    return {"status": "ok", "service": "DeskPulse"}


@bp.route('/health')
def health_check():
    """Health check endpoint for installation verification."""
    return jsonify({'status': 'ok', 'service': 'deskpulse'}), 200
