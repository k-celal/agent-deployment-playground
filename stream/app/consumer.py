"""
Stream Consumer — Event-driven ticket işleme.

Bu modül, stream deployment modelinin ana bileşenidir.
Bir event bus/queue'dan gelen ticket event'lerini birer birer tüketir,
agent ile işler ve sonuçları inference store'a yazar.

Stream processing şu durumlarda kullanılır:
- Veri sürekli akıyorsa (event-driven)
- Düşük latency gerekiyorsa ama anlık olması şart değilse (saniyeler OK)
- Event'lere tepki verilmesi gerekiyorsa
- Decoupled mimari isteniyorsa

Bu repo'da gerçek bir message broker (Kafka/RabbitMQ) yerine
in-memory queue simülasyonu kullanıyoruz. Amaç event-driven
processing KAVRAMINI göstermek.

Production'da dikkat edilecekler:
- Idempotency: Aynı event tekrar gelirse tekrar işlenmesin
- Ordering: Event sırası önemli mi?
- Dead Letter Queue: İşlenemeyen event'ler nereye gider?
- Backpressure: Consumer yetişemezse ne olur?
- Offset management: Hangi event'e kadar işlendi?
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from shared.models.base_agent import BaseTriageAgent
from shared.models.mock_llm import MockLLM
from shared.schemas.result import TriageResult
from shared.schemas.ticket import Ticket
from shared.types.enums import TriageStatus
from shared.utils.context import ContextProvider
from shared.utils.store import InferenceStore

logger = logging.getLogger(__name__)


class TicketEvent:
    """
    Simüle edilmiş ticket event'i.

    Gerçek dünyada bu bir Kafka message, RabbitMQ delivery
    veya SQS message olurdu. Event'in önemli özellikleri:
    - event_id: Unique identifier (idempotency için)
    - event_type: Ne oldu? (created, updated, closed)
    - payload: Event verisi (ticket)
    """

    def __init__(self, event_id: str, event_type: str, payload: dict):
        self.event_id = event_id
        self.event_type = event_type
        self.payload = payload
        self.acknowledged = False

    def acknowledge(self) -> None:
        """
        Event'in başarıyla işlendiğini bildir.

        Kafka'da offset commit, RabbitMQ'da ack, SQS'te delete
        karşılığı. Acknowledge edilmeyen event tekrar gönderilir
        (at-least-once delivery).
        """
        self.acknowledged = True
        logger.debug(f"Event acknowledged: {self.event_id}")


class SimpleEventQueue:
    """
    In-memory event queue simülasyonu.

    Gerçek dünyada Kafka, RabbitMQ, SQS, Redis Streams gibi
    bir message broker kullanılır. Bu simülasyon sadece
    event-driven processing akışını göstermek içindir.
    """

    def __init__(self):
        self._queue: asyncio.Queue[TicketEvent | None] = asyncio.Queue()
        self._dead_letter: list[TicketEvent] = []

    async def publish(self, event: TicketEvent) -> None:
        """Event yayınla (producer tarafı)."""
        await self._queue.put(event)
        logger.info(f"Event published: {event.event_id} ({event.event_type})")

    async def consume(self) -> TicketEvent | None:
        """
        Sıradaki event'i al (consumer tarafı).

        None dönerse stream sona ermiş demektir (poison pill pattern).
        """
        return await self._queue.get()

    async def stop(self) -> None:
        """Consumer'a durmasını söyle (poison pill)."""
        await self._queue.put(None)

    def send_to_dlq(self, event: TicketEvent) -> None:
        """
        İşlenemeyen event'i dead letter queue'ya gönder.

        Production'da DLQ ayrı bir topic/queue'dur.
        İşlenemeyen event'ler burada birikir ve
        mühendisler tarafından incelenir.
        """
        self._dead_letter.append(event)
        logger.warning(f"Event sent to DLQ: {event.event_id}")

    @property
    def dead_letter_count(self) -> int:
        return len(self._dead_letter)


class StreamConsumer:
    """
    Event-driven ticket triage consumer.

    Akış:
    1. Queue'dan event al
    2. Idempotency kontrolü (zaten işlendi mi?)
    3. Ticket'ı parse et
    4. Agent ile işle
    5. Sonucu inference store'a yaz
    6. Event'i acknowledge et

    Hata durumunda:
    - Retry (max_retries kadar)
    - Başarısızsa → Dead Letter Queue
    """

    def __init__(
        self,
        queue: SimpleEventQueue,
        agent: BaseTriageAgent | None = None,
        store: InferenceStore | None = None,
        max_retries: int = 3,
    ):
        self.queue = queue

        if agent is None:
            llm = MockLLM(latency_ms=30.0)
            context = ContextProvider()
            agent = BaseTriageAgent(
                llm=llm, context_provider=context, deployment_mode="stream"
            )

        self.agent = agent
        self.store = store or InferenceStore(db_path="data/stream_inference.db")
        self.max_retries = max_retries
        self.processed_count = 0
        self.skipped_count = 0
        self.failed_count = 0

    async def start(self) -> None:
        """
        Consumer loop'u başlat.

        Bu loop sürekli çalışır ve yeni event'ler geldiğinde işler.
        None (poison pill) geldiğinde durur.
        """
        logger.info("Stream consumer started. Waiting for events...")

        while True:
            event = await self.queue.consume()

            if event is None:
                logger.info("Received stop signal. Consumer shutting down.")
                break

            await self._process_event(event)

        self._log_summary()

    async def _process_event(self, event: TicketEvent) -> None:
        """Tek bir event'i işle — retry ve DLQ mantığı ile."""
        # Sadece ticket.created event'lerini işle
        if event.event_type != "ticket.created":
            logger.debug(f"Ignoring event type: {event.event_type}")
            event.acknowledge()
            return

        ticket_id = event.payload.get("id", "unknown")

        # Idempotency kontrolü
        if self.store.exists(ticket_id):
            logger.info(f"Ticket already processed (idempotent skip): {ticket_id}")
            event.acknowledge()
            self.skipped_count += 1
            return

        for attempt in range(1, self.max_retries + 1):
            try:
                ticket = Ticket(**event.payload)
                result = self.agent.process(ticket)
                self.store.save(result)
                event.acknowledge()
                self.processed_count += 1

                logger.info(
                    f"Processed: {ticket_id} → "
                    f"priority={result.priority.value}, "
                    f"category={result.category.value}, "
                    f"confidence={result.confidence:.2f}"
                )
                return

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed for "
                    f"{ticket_id}: {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(0.1 * attempt)  # basit backoff

        # Tüm retry'lar başarısız → DLQ
        self.queue.send_to_dlq(event)
        self.failed_count += 1

    def _log_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("STREAM CONSUMER SUMMARY")
        logger.info(f"  Processed: {self.processed_count}")
        logger.info(f"  Skipped (idempotent): {self.skipped_count}")
        logger.info(f"  Failed (DLQ): {self.failed_count}")
        logger.info(f"  Dead letters: {self.queue.dead_letter_count}")
        logger.info("=" * 60)


async def run_stream(events_file: str = "examples/events/ticket_events.json") -> None:
    """Stream consumer'ı simüle edilmiş event'lerle çalıştır."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [STREAM] %(levelname)s %(message)s",
    )

    logger.info("=" * 60)
    logger.info("STREAM CONSUMER STARTING")
    logger.info("=" * 60)

    queue = SimpleEventQueue()
    consumer = StreamConsumer(queue=queue)

    # Event'leri dosyadan yükle ve queue'ya publish et
    events_path = Path(events_file)
    if events_path.exists():
        with open(events_path) as f:
            events_data = json.load(f)

        for event_data in events_data:
            event = TicketEvent(
                event_id=event_data["event_id"],
                event_type=event_data["event_type"],
                payload=event_data["payload"],
            )
            await queue.publish(event)

        await queue.stop()  # Poison pill
    else:
        logger.error(f"Events file not found: {events_file}")
        return

    await consumer.start()


if __name__ == "__main__":
    asyncio.run(run_stream())
