"""
Tests for main routes blueprint.
AC0: Health endpoint verification for installer.
"""
import pytest
from flask import json


def test_health_endpoint_exists(client):
    """Test that /health endpoint exists and returns 200 OK."""
    response = client.get('/health')
    assert response.status_code == 200


def test_health_endpoint_returns_correct_json(client):
    """Test that /health endpoint returns expected JSON structure."""
    response = client.get('/health')
    data = json.loads(response.data)

    assert 'status' in data
    assert 'service' in data
    assert data['status'] == 'ok'
    assert data['service'] == 'deskpulse'


def test_health_endpoint_content_type(client):
    """Test that /health endpoint returns JSON content type."""
    response = client.get('/health')
    assert response.content_type == 'application/json'
