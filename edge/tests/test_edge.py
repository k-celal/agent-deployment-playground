"""
Edge agent testleri.

Edge deployment'ın özelliklerini test eder:
- Kural tabanlı triage doğruluğu
- Lokal storage
- Graceful degradation (bilinmeyen input)
- Ultra-düşük latency
"""

import tempfile
from pathlib import Path

import pytest

from edge.app.local_agent import EdgeTriageAgent, LocalStorage
from shared.schemas.ticket import Ticket
from shared.types.enums import Category, Priority, TriageStatus


@pytest.fixture
def agent():
    return EdgeTriageAgent()


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalStorage(output_dir=tmpdir)


def make_ticket(ticket_id: str, title: str, body: str) -> Ticket:
    return Ticket(id=ticket_id, title=title, body=body)


class TestEdgeTriageAgent:

    def test_critical_incident(self, agent):
        ticket = make_ticket("E-001", "Production is down", "All services are down and crashing")
        result = agent.process(ticket)
        assert result.priority == Priority.P0
        assert result.category == Category.INCIDENT

    def test_bug_detection(self, agent):
        ticket = make_ticket("E-002", "Login error on Chrome", "Getting error when trying to login")
        result = agent.process(ticket)
        assert result.priority == Priority.P1
        assert result.category == Category.BUG

    def test_feature_request(self, agent):
        ticket = make_ticket("E-003", "I want dark mode", "Please add dark mode feature")
        result = agent.process(ticket)
        assert result.priority == Priority.P3
        assert result.category == Category.FEATURE_REQUEST

    def test_question(self, agent):
        ticket = make_ticket("E-004", "How to reset password?", "I need help resetting my password")
        result = agent.process(ticket)
        assert result.priority == Priority.P3
        assert result.category == Category.QUESTION

    def test_unknown_input_graceful_degradation(self, agent):
        """Bilinmeyen input'ta güvenli fallback çalışmalı."""
        ticket = make_ticket("E-005", "Xyz abc", "Random text that matches no rules")
        result = agent.process(ticket)
        assert result.priority == Priority.P2  # Güvenli default
        assert result.category == Category.OTHER
        assert result.confidence < 0.4

    def test_low_confidence_status(self, agent):
        """Düşük confidence → LOW_CONFIDENCE status."""
        ticket = make_ticket("E-006", "Something", "Vague description")
        result = agent.process(ticket)
        if result.confidence < 0.4:
            assert result.status == TriageStatus.LOW_CONFIDENCE

    def test_deployment_mode(self, agent):
        ticket = make_ticket("E-007", "Test", "Test body with error keyword")
        result = agent.process(ticket)
        assert result.deployment_mode == "edge"

    def test_ultra_low_latency(self, agent):
        """Edge agent < 5ms'de işlemeli (kural tabanlı, LLM yok)."""
        ticket = make_ticket("E-008", "Slow page load", "Page takes too long")
        result = agent.process(ticket)
        assert result.processing_time_ms is not None
        assert result.processing_time_ms < 5.0


class TestLocalStorage:

    def test_save_and_load(self, temp_storage, agent):
        ticket = make_ticket("STORE-001", "Login error", "Auth error on login")
        result = agent.process(ticket)
        temp_storage.save(result)

        loaded = temp_storage.load("STORE-001")
        assert loaded is not None
        assert loaded.ticket_id == "STORE-001"

    def test_load_nonexistent(self, temp_storage):
        assert temp_storage.load("NONEXISTENT") is None

    def test_list_results(self, temp_storage, agent):
        for i in range(3):
            ticket = make_ticket(f"LIST-{i}", f"Ticket {i}", "Body text error")
            result = agent.process(ticket)
            temp_storage.save(result)

        results = temp_storage.list_results()
        assert len(results) == 3

    def test_pending_sync(self, temp_storage, agent):
        ticket = make_ticket("SYNC-001", "Test ticket", "Body with bug error")
        result = agent.process(ticket)
        temp_storage.save(result)

        pending = temp_storage.pending_sync()
        assert len(pending) == 1
        assert pending[0].ticket_id == "SYNC-001"
