"""
Edge Offline Simülasyonu.

Bu script, edge agent'ın tam offline senaryosunda nasıl
çalıştığını simüle eder:
1. Lokal ticket'ları işle (internet yok)
2. Sonuçları lokal storage'a kaydet
3. "Internet geldi" → sunucuya sync simülasyonu

Bu simülasyon, edge deployment'ın gerçek dünya davranışını
göstermek için tasarlanmıştır.
"""

import json
import logging
import time

from edge.app.local_agent import EdgeTriageAgent, LocalStorage
from shared.schemas.ticket import Ticket

logger = logging.getLogger(__name__)


def simulate_offline_scenario():
    """Offline → triage → sync senaryosunu simüle et."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [EDGE-SIM] %(levelname)s %(message)s",
    )

    logger.info("=" * 60)
    logger.info("EDGE OFFLINE SIMULATION")
    logger.info("=" * 60)

    agent = EdgeTriageAgent()
    storage = LocalStorage(output_dir="data/edge_simulation_results")

    # Aşama 1: Offline — lokal ticket'ları işle
    logger.info("\n--- Phase 1: OFFLINE MODE (no internet) ---")

    offline_tickets = [
        Ticket(id="SIM-001", title="App crash on startup", body="Application crashes immediately"),
        Ticket(id="SIM-002", title="Need export feature", body="I want to add CSV export feature"),
        Ticket(id="SIM-003", title="How to use API?", body="I need help understanding the API documentation"),
    ]

    for ticket in offline_tickets:
        start = time.time()
        result = agent.process(ticket)
        file_path = storage.save(result)
        elapsed = (time.time() - start) * 1000

        logger.info(
            f"  [{result.ticket_id}] "
            f"priority={result.priority.value}, "
            f"category={result.category.value}, "
            f"confidence={result.confidence:.2f}, "
            f"latency={elapsed:.3f}ms "
            f"→ saved locally"
        )

    # Aşama 2: Sync — internet geldi
    logger.info("\n--- Phase 2: ONLINE — syncing to server ---")

    pending = storage.pending_sync()
    logger.info(f"  Pending sync: {len(pending)} results")

    for result in pending:
        logger.info(f"  Syncing {result.ticket_id} → server... (simulated)")
        time.sleep(0.1)  # Network latency simülasyonu

    logger.info(f"\n  ✓ All {len(pending)} results synced to server")

    # Aşama 3: Özet
    logger.info("\n--- Summary ---")
    logger.info(f"  Total processed: {len(offline_tickets)}")
    logger.info(f"  Storage: {storage.output_dir}")
    logger.info(f"  All results: {storage.list_results()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    simulate_offline_scenario()
