import logging
import configparser
import os
from flask import render_template, jsonify, request, current_app
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError
from app.main import bp

# Hierarchical logger for API routes (AC2)
logger = logging.getLogger("deskpulse.api")


@bp.route('/')
def dashboard():
    """
    Main dashboard page (FR35).

    Renders the Pico CSS-based dashboard with live camera feed placeholder,
    posture status, and today's summary. SocketIO updates will activate
    in Story 2.6.

    Returns:
        str: Rendered HTML template
        tuple: Error response with 500 status if template fails
    """
    try:
        logger.info("Dashboard accessed")
        return render_template('dashboard.html')
    except TemplateNotFound:
        logger.error("Dashboard template not found")
        return jsonify({
            'error': 'Dashboard unavailable',
            'message': 'The dashboard template could not be found'
        }), 500
    except TemplateSyntaxError as e:
        logger.error(f"Dashboard template syntax error: {e}")
        return jsonify({
            'error': 'Dashboard unavailable',
            'message': 'The dashboard template has a syntax error'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error rendering dashboard: {e}")
        return jsonify({
            'error': 'Dashboard unavailable',
            'message': 'An unexpected error occurred'
        }), 500


@bp.route('/health')
def health_check():
    """Health check endpoint for installation verification."""
    return jsonify({'status': 'ok', 'service': 'deskpulse'}), 200


@bp.route('/api/network-settings', methods=['GET'])
def get_network_settings():
    """Get current network settings from config."""
    try:
        config_path = os.path.expanduser("~/.config/deskpulse/config.ini")
        config = configparser.ConfigParser()
        config.read(config_path)

        host = config.get('dashboard', 'host', fallback='127.0.0.1')
        port = config.get('dashboard', 'port', fallback='5000')

        return jsonify({
            'host': host,
            'port': port
        }), 200
    except Exception as e:
        logger.error(f"Failed to read network settings: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/network-settings', methods=['POST'])
def update_network_settings():
    """Update network settings in config file."""
    try:
        data = request.get_json()
        new_host = data.get('host', '127.0.0.1')

        # Validate host value
        if new_host not in ['127.0.0.1', '0.0.0.0']:
            return jsonify({
                'success': False,
                'error': 'Invalid host value. Must be 127.0.0.1 or 0.0.0.0'
            }), 400

        config_path = os.path.expanduser("~/.config/deskpulse/config.ini")
        config = configparser.ConfigParser()
        config.read(config_path)

        # Ensure dashboard section exists
        if not config.has_section('dashboard'):
            config.add_section('dashboard')

        # Update host setting
        config.set('dashboard', 'host', new_host)

        # Ensure config directory exists (fixes fresh deployment issue)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Write back to file
        with open(config_path, 'w') as f:
            config.write(f)

        logger.info(f"Network settings updated: host={new_host}")

        return jsonify({
            'success': True,
            'host': new_host,
            'message': 'Settings saved. Restart app to apply changes.'
        }), 200
    except Exception as e:
        logger.error(f"Failed to update network settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
