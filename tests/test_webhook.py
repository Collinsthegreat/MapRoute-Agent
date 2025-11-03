"""Tests for webhook endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_webhook_valid_request():
    """Test webhook with valid route request."""
    payload = {
        "message": "directions from Lagos to Abuja",
        "user_id": "test_user_123"
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data


def test_webhook_invalid_json():
    """Test webhook with invalid JSON."""
    response = client.post("/webhook", data="invalid json")
    assert response.status_code == 422


def test_webhook_empty_message():
    """Test webhook with empty message."""
    payload = {"message": ""}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 400


def test_webhook_help_request():
    """Test webhook with help request."""
    payload = {"message": "help"}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "help" in data["text"].lower() or "directions" in data["text"].lower()