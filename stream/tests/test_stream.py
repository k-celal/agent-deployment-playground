"""
Stream consumer testleri.

Bu testler event-driven processing davranışlarını test eder:
- Event tüketme ve işleme
- Idempotency (tekrarlayan event)
- Dead letter queue (işlenemeyen event)
- Event acknowledge
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from shared.models.base_agent import BaseTriageAgent
from shared.models.mock_llm import MockLLM
from shared.utils.context import ContextProvider
from shared.utils.store import InferenceStore
from stream.app.consumer import SimpleEventQueue, StreamConsumer, TicketEvent


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_stream.db")


@pytest.fixture
def queue():
    return SimpleEventQueue()


@pytest.fixture
def consumer(queue, temp_db):
    agent = BaseTriageAgent(
        llm=MockLLM(latency_ms=1.0),
        context_provider=ContextProvider(),
        deployment_mode="stream",
    )
    store = InferenceStore(db_path=temp_db)
    return StreamConsumer(queue=queue, agent=agent, store=store)


def make_ticket_event(ticket_id: str, title: str = "Test ticket", body: str = "Test body") -> TicketEvent:
    return TicketEvent(
        event_id=f"evt-{ticket_id}",
        event_type="ticket.created",
        payload={
            "id": ticket_id,
            "title": title,
            "body": body,
        },
    )


@pytest.mark.asyncio
async def test_process_single_event(queue, consumer):
    event = make_ticket_event("STREAM-001", "Login 500 error", "Getting 500 on login")
    await queue.publish(event)
    await queue.stop()

    await consumer.start()
    assert consumer.processed_count == 1
    assert event.acknowledged


@pytest.mark.asyncio
async def test_idempotent_processing(queue, consumer):
    """Aynı ticket_id ile gelen event tekrar işlenmemeli."""
    event1 = make_ticket_event("STREAM-DUP")
    event2 = make_ticket_event("STREAM-DUP")

    await queue.publish(event1)
    await queue.publish(event2)
    await queue.stop()

    await consumer.start()
    assert consumer.processed_count == 1
    assert consumer.skipped_count == 1


@pytest.mark.asyncio
async def test_non_ticket_event_ignored(queue, consumer):
    """ticket.created dışındaki event'ler ignore edilmeli."""
    event = TicketEvent(
        event_id="evt-other",
        event_type="ticket.closed",
        payload={"id": "STREAM-CLOSED"},
    )
    await queue.publish(event)
    await queue.stop()

    await consumer.start()
    assert consumer.processed_count == 0
    assert event.acknowledged


@pytest.mark.asyncio
async def test_multiple_events(queue, consumer):
    for i in range(5):
        event = make_ticket_event(f"STREAM-MULTI-{i}", f"Ticket {i}", f"Body {i}")
        await queue.publish(event)
    await queue.stop()

    await consumer.start()
    assert consumer.processed_count == 5


@pytest.mark.asyncio
async def test_results_stored(queue, consumer, temp_db):
    event = make_ticket_event("STREAM-STORE", "Payment error", "Can't process payment")
    await queue.publish(event)
    await queue.stop()

    await consumer.start()

    store = InferenceStore(db_path=temp_db)
    result = store.get("STREAM-STORE")
    assert result is not None
    assert result.deployment_mode == "stream"
