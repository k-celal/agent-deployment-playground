"""
Real-time API testleri.

FastAPI'nin TestClient'ını kullanarak API endpoint'lerini test eder.
Bu testler deployment katmanını (HTTP handling, validation, response format)
test eder — agent logic ayrıca test edilir.
"""

import pytest
from fastapi.testclient import TestClient

from realtime.app.api import app


@pytest.fixture
def client():
    """FastAPI test client'ı."""
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ticket-triage-realtime"


def test_triage_endpoint(client):
    payload = {
        "ticket_id": "RT-001",
        "title": "Login page 500 error",
        "body": "Getting 500 Internal Server Error on login page",
        "user_email": "test@example.com",
    }
    response = client.post("/triage", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["ticket_id"] == "RT-001"
    assert data["priority"] in ["P0", "P1", "P2", "P3"]
    assert data["category"] in [
        "bug", "feature_request", "question", "incident", "task", "other"
    ]
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["processing_time_ms"] > 0


def test_triage_validation_error(client):
    """Eksik field'larla istek validation error dönmeli."""
    payload = {"ticket_id": "RT-BAD"}  # title ve body eksik
    response = client.post("/triage", json=payload)
    assert response.status_code == 422


def test_triage_feature_request(client):
    payload = {
        "ticket_id": "RT-002",
        "title": "Add dark mode feature",
        "body": "I want a dark mode toggle in settings",
    }
    response = client.post("/triage", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["category"] == "feature_request"
    assert data["priority"] == "P3"


def test_get_result_not_found(client):
    response = client.get("/results/NONEXISTENT-TICKET")
    assert response.status_code == 404


def test_get_result_after_triage(client):
    payload = {
        "ticket_id": "RT-003",
        "title": "Payment not working",
        "body": "Can't process payment with credit card",
    }
    client.post("/triage", json=payload)

    response = client.get("/results/RT-003")
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "RT-003"


def test_processing_time_header(client):
    """Her response'ta X-Processing-Time-Ms header'ı olmalı."""
    response = client.get("/health")
    assert "X-Processing-Time-Ms" in response.headers


def test_multiple_sequential_requests(client):
    """Sıralı istekler bağımsız sonuç dönmeli (stateless)."""
    for i in range(3):
        payload = {
            "ticket_id": f"RT-SEQ-{i}",
            "title": f"Test ticket {i}",
            "body": f"Test body {i}",
        }
        response = client.post("/triage", json=payload)
        assert response.status_code == 200
        assert response.json()["ticket_id"] == f"RT-SEQ-{i}"
