"""
Batch processor testleri.

Bu testler batch deployment katmanını test eder.
Agent logic zaten shared/ altında test edilir —
burada odak noktası toplu işleme, store yazımı
ve hata yönetimi davranışlarıdır.
"""

import json
import tempfile
from pathlib import Path

import pytest

from batch.app.processor import BatchProcessor
from shared.models.base_agent import BaseTriageAgent
from shared.models.mock_llm import MockLLM
from shared.schemas.ticket import Ticket
from shared.types.enums import Priority, TriageStatus
from shared.utils.context import ContextProvider
from shared.utils.store import InferenceStore


@pytest.fixture
def temp_db():
    """Her test için geçici veritabanı."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_batch.db")


@pytest.fixture
def processor(temp_db):
    """Test için konfigüre edilmiş batch processor."""
    agent = BaseTriageAgent(
        llm=MockLLM(latency_ms=1.0),
        context_provider=ContextProvider(),
        deployment_mode="batch",
    )
    store = InferenceStore(db_path=temp_db)
    return BatchProcessor(agent=agent, store=store)


@pytest.fixture
def sample_tickets():
    return [
        Ticket(id="BATCH-001", title="Login page 500 error", body="Getting 500 on login"),
        Ticket(id="BATCH-002", title="Add dark mode", body="I want dark mode feature"),
        Ticket(id="BATCH-003", title="How to reset password?", body="Help me reset my password"),
    ]


@pytest.fixture
def sample_tickets_file(sample_tickets):
    """Ticket'ları geçici JSON dosyasına yaz."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([t.model_dump(mode="json") for t in sample_tickets], f)
        return f.name


def test_process_all_returns_results(processor, sample_tickets):
    results = processor.process_all(sample_tickets)
    assert len(results) == 3
    assert all(r.deployment_mode == "batch" for r in results)


def test_results_saved_to_store(processor, sample_tickets, temp_db):
    processor.process_all(sample_tickets)
    store = InferenceStore(db_path=temp_db)
    assert store.count() == 3


def test_skip_existing_tickets(processor, sample_tickets):
    processor.process_all(sample_tickets)
    results_second_run = processor.process_all(sample_tickets, skip_existing=True)
    assert len(results_second_run) == 0


def test_load_tickets_from_file(processor, sample_tickets_file):
    tickets = processor.load_tickets_from_file(sample_tickets_file)
    assert len(tickets) == 3
    assert tickets[0].id == "BATCH-001"


def test_load_nonexistent_file(processor):
    with pytest.raises(FileNotFoundError):
        processor.load_tickets_from_file("nonexistent.json")


def test_priority_assignment(processor, sample_tickets):
    results = processor.process_all(sample_tickets)
    result_map = {r.ticket_id: r for r in results}

    # 500 error → yüksek öncelik (P0 veya P1)
    assert result_map["BATCH-001"].priority in (Priority.P0, Priority.P1)

    # Feature request → düşük öncelik
    assert result_map["BATCH-002"].priority == Priority.P3
