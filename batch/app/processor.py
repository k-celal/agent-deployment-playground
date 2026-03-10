"""
Batch Processor — Toplu ticket işleme motoru.

Bu modül, batch deployment modelinin ana bileşenidir.
Bir grup ticket'ı dosyadan veya veritabanından okur,
agent ile sırasıyla işler ve sonuçları inference store'a yazar.

Batch processing şu durumlarda kullanılır:
- Anlık cevap gerekmediğinde
- Toplu veri işleme gerektiğinde (gece enrichment, rapor)
- Maliyet optimize edilmek istendiğinde (off-peak kaynaklar)
- Tüm veriye erişim gerektiğinde (bulk read)

Production'da dikkat edilecekler:
- Checkpoint mekanizması (crash durumunda kaldığı yerden devam)
- Progress tracking (10K kayıttan kaçı işlendi?)
- Error handling (hatalı kayıtları logla, diğerlerine devam et)
- Resource management (DB bağlantısını aşırı yükleme)
"""

import json
import logging
from pathlib import Path

from shared.models.base_agent import BaseTriageAgent
from shared.models.mock_llm import MockLLM
from shared.schemas.result import TriageResult
from shared.schemas.ticket import Ticket
from shared.utils.context import ContextProvider
from shared.utils.store import InferenceStore

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Toplu ticket işleme.

    Akış:
    1. load_tickets() → dosyadan ticket'ları oku
    2. process_all() → her ticket'ı agent ile işle
    3. Sonuçlar inference store'a toplu yazılır

    Production'da bu bir Kubernetes CronJob, Airflow DAG
    veya basit bir cron + Python script olabilir.
    """

    def __init__(
        self,
        agent: BaseTriageAgent | None = None,
        store: InferenceStore | None = None,
    ):
        if agent is None:
            llm = MockLLM(latency_ms=20.0)
            context = ContextProvider()
            agent = BaseTriageAgent(
                llm=llm, context_provider=context, deployment_mode="batch"
            )

        self.agent = agent
        self.store = store or InferenceStore(db_path="data/batch_inference.db")

    def load_tickets_from_file(self, file_path: str) -> list[Ticket]:
        """
        JSON dosyasından ticket'ları yükle.

        Production'da bu:
        - DB query olabilir
        - S3'ten dosya okuma olabilir
        - API'den pagination ile çekme olabilir
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        with open(path) as f:
            data = json.load(f)

        tickets = [Ticket(**item) for item in data]
        logger.info(f"Loaded {len(tickets)} tickets from {file_path}")
        return tickets

    def process_all(
        self,
        tickets: list[Ticket],
        skip_existing: bool = True,
    ) -> list[TriageResult]:
        """
        Tüm ticket'ları sırayla işle.

        Args:
            tickets: İşlenecek ticket listesi
            skip_existing: True ise zaten işlenmiş ticket'ları atla (idempotency)

        Production'da bu method'a eklenebilecekler:
        - Paralel işleme (multiprocessing/threading)
        - Checkpoint (her N kayıtta progress kaydet)
        - Rate limiting (LLM API limitlerini aşmamak için)
        - Progress bar (tqdm)
        """
        results: list[TriageResult] = []
        skipped = 0
        failed = 0

        for i, ticket in enumerate(tickets, 1):
            if skip_existing and self.store.exists(ticket.id):
                logger.debug(f"Skipping already processed ticket: {ticket.id}")
                skipped += 1
                continue

            logger.info(f"Processing ticket {i}/{len(tickets)}: {ticket.id}")

            result = self.agent.process(ticket)
            results.append(result)

            if result.status.value == "failed":
                failed += 1
                logger.warning(f"Failed to process ticket {ticket.id}: {result.summary}")

        if results:
            self.store.save_batch(results)
            logger.info(
                f"Batch complete: {len(results)} processed, "
                f"{skipped} skipped, {failed} failed"
            )

        return results


def run_batch(input_file: str = "examples/requests/batch_tickets.json") -> None:
    """Batch processor'ı çalıştıran CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [BATCH] %(levelname)s %(message)s",
    )

    logger.info("=" * 60)
    logger.info("BATCH PROCESSOR STARTING")
    logger.info("=" * 60)

    processor = BatchProcessor()

    try:
        tickets = processor.load_tickets_from_file(input_file)
        results = processor.process_all(tickets)

        logger.info("=" * 60)
        logger.info("BATCH RESULTS SUMMARY")
        logger.info("=" * 60)

        for result in results:
            logger.info(
                f"  {result.ticket_id}: "
                f"priority={result.priority.value}, "
                f"category={result.category.value}, "
                f"confidence={result.confidence:.2f}, "
                f"time={result.processing_time_ms:.1f}ms"
            )

        logger.info(f"Total: {len(results)} tickets processed")
        logger.info(f"Store location: {processor.store.db_path}")

    except FileNotFoundError as e:
        logger.error(str(e))
    except Exception as e:
        logger.exception(f"Batch processing failed: {e}")


if __name__ == "__main__":
    run_batch()
