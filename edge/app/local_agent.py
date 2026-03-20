"""
Edge Agent — Cihaz üzeri lightweight ticket triage.

Bu modül, edge deployment modelinin ana bileşenidir.
LLM API'ye erişim olmadan, sınırlı kaynaklarla,
lokal olarak çalışan bir agent simülasyonu gösterir.

Edge deployment şu durumlarda kullanılır:
- Privacy kritikse (veri cihazdan çıkmamalı)
- Offline çalışma gerekiyorsa
- Ultra-düşük latency gerekiyorsa (< 50ms)
- Internet bağlantısı güvenilir değilse
- API maliyetinden kaçınılmak isteniyorsa

Edge'de anahtar kısıtlar:
- Sınırlı bellek ve işlem gücü
- Tam LLM yerine lightweight model veya kural tabanlı mantık
- Sınırlı context (tam knowledge base yok)
- Model güncelleme zorluğu (OTA)

Bu repo'da edge'i simüle ediyoruz:
- Kural tabanlı (rule-based) triage (LLM yerine)
- Sınırlı lokal context
- Lokal dosya sistemi çıktısı
- Graceful degradation (bilinmeyen durumda fallback)
"""

import json
import logging
import time
from pathlib import Path

from shared.schemas.result import TriageResult
from shared.schemas.ticket import Ticket
from shared.types.enums import Category, Priority, TriageStatus

logger = logging.getLogger(__name__)


class EdgeTriageAgent:
    """
    Lightweight edge triage agent.

    Bu agent LLM kullanmaz. Bunun yerine kural tabanlı
    (rule-based) bir sistem kullanır. Gerçek dünyada edge'de:
    - Quantized küçük model (TinyLlama, Phi-2, ONNX)
    - TF Lite / Core ML modeli
    - Veya bu örnekteki gibi kural tabanlı mantık
    kullanılabilir.

    Kural tabanlı yaklaşımın avantajı:
    - Deterministic sonuçlar
    - Çok düşük latency (< 1ms)
    - Sıfır API maliyeti
    - Hallucination riski yok

    Dezavantajı:
    - Yeni pattern'lere adapte olamaz
    - Karmaşık vakaları yakalayamaz
    - Manuel güncelleme gerektirir
    """

    PRIORITY_RULES: list[tuple[list[str], Priority]] = [
        (["down", "outage", "crash", "500", "critical", "emergency"], Priority.P0),
        (["error", "broken", "fail", "login", "auth", "payment"], Priority.P1),
        (["slow", "timeout", "bug", "wrong", "incorrect"], Priority.P2),
        (["feature", "request", "want", "question", "how", "help"], Priority.P3),
    ]

    CATEGORY_RULES: list[tuple[list[str], Category]] = [
        (["down", "outage", "crash", "incident", "alert"], Category.INCIDENT),
        (["error", "bug", "broken", "fail", "wrong", "500"], Category.BUG),
        (["how", "what", "where", "question", "help", "guide"], Category.QUESTION),
        (["feature", "request", "want", "add", "need", "wish"], Category.FEATURE_REQUEST),
        (["test", "qa", "deploy", "maintain", "update"], Category.TASK),
    ]

    TEAM_MAPPING: dict[Category, str] = {
        Category.INCIDENT: "on-call",
        Category.BUG: "engineering",
        Category.FEATURE_REQUEST: "product",
        Category.QUESTION: "support",
        Category.TASK: "engineering",
        Category.OTHER: "support",
    }

    def __init__(self, local_context_path: str | None = None):
        """
        Args:
            local_context_path: Lokal context dosyasının yolu.
                Edge'de tam knowledge base yerine küçük bir
                lokal cache tutulur.
        """
        self.local_context = self._load_local_context(local_context_path)

    def _load_local_context(self, path: str | None) -> dict:
        """Lokal context cache'ini yükle (varsa)."""
        if path is None or not Path(path).exists():
            return {}
        with open(path) as f:
            return json.load(f)

    def process(self, ticket: Ticket) -> TriageResult:
        """
        Kural tabanlı ticket triage.

        LLM çağrısı yok — tüm mantık lokal kurallarla çalışır.
        Bu, edge'in temel özelliğidir: dış bağımlılık minimum.
        """
        start_time = time.time()

        text = f"{ticket.title} {ticket.body}".lower()

        priority = self._determine_priority(text)
        category = self._determine_category(text)
        team = self.TEAM_MAPPING.get(category, "support")
        summary = self._generate_summary(ticket, priority, category)
        confidence = self._calculate_confidence(text, priority, category)

        elapsed_ms = (time.time() - start_time) * 1000

        status = TriageStatus.SUCCESS
        if confidence < 0.4:
            status = TriageStatus.LOW_CONFIDENCE

        return TriageResult(
            ticket_id=ticket.id,
            priority=priority,
            category=category,
            summary=summary,
            confidence=confidence,
            suggested_team=team,
            status=status,
            processing_time_ms=elapsed_ms,
            deployment_mode="edge",
        )

    def _determine_priority(self, text: str) -> Priority:
        for keywords, priority in self.PRIORITY_RULES:
            if any(kw in text for kw in keywords):
                return priority
        return Priority.P2  # Fallback

    def _determine_category(self, text: str) -> Category:
        for keywords, category in self.CATEGORY_RULES:
            if any(kw in text for kw in keywords):
                return category
        return Category.OTHER  # Fallback

    def _generate_summary(self, ticket: Ticket, priority: Priority, category: Category) -> str:
        """
        Basit template-based özet.

        LLM'in doğal dil üretimi yerine, edge'de
        kural tabanlı template'ler kullanılır.
        Daha az zengin ama çok daha hızlı ve güvenilir.
        """
        return (
            f"[Edge Triage] Ticket '{ticket.title}' classified as "
            f"{category.value} with {priority.value} priority. "
            f"Suggested team: {self.TEAM_MAPPING.get(category, 'support')}."
        )

    def _calculate_confidence(self, text: str, priority: Priority, category: Category) -> float:
        """
        Kural tabanlı confidence hesaplama.

        LLM'in confidence score'u yerine, kaç kural eşleştiğine
        göre basit bir güven skoru hesaplar.
        """
        matched_keywords = 0
        total_rules = 0

        for keywords, _ in self.PRIORITY_RULES + self.CATEGORY_RULES:
            total_rules += 1
            if any(kw in text for kw in keywords):
                matched_keywords += 1

        if matched_keywords == 0:
            return 0.2  # Hiçbir kural eşleşmediyse düşük güven

        return min(0.6 + (matched_keywords / total_rules), 0.85)


class LocalStorage:
    """
    Edge lokal depolama.

    Inference store'un edge karşılığı. Sonuçlar lokal
    dosya sistemine JSON olarak yazılır. Internet olduğunda
    merkez sunucuya sync edilebilir.
    """

    def __init__(self, output_dir: str = "data/edge_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, result: TriageResult) -> Path:
        """Sonucu lokal JSON dosyası olarak kaydet."""
        file_path = self.output_dir / f"{result.ticket_id}.json"
        with open(file_path, "w") as f:
            f.write(result.model_dump_json(indent=2))
        return file_path

    def load(self, ticket_id: str) -> TriageResult | None:
        """Lokal sonucu oku."""
        file_path = self.output_dir / f"{ticket_id}.json"
        if not file_path.exists():
            return None
        with open(file_path) as f:
            return TriageResult.model_validate_json(f.read())

    def list_results(self) -> list[str]:
        """Kaydedilmiş tüm sonuç ID'lerini listele."""
        return [p.stem for p in self.output_dir.glob("*.json")]

    def pending_sync(self) -> list[TriageResult]:
        """
        Sunucuya henüz sync edilmemiş sonuçları getir.

        Production'da her sonuçta bir "synced" flag'i olurdu.
        Bu simülasyonda tüm lokal sonuçları döndürüyoruz.
        """
        results = []
        for path in self.output_dir.glob("*.json"):
            with open(path) as f:
                results.append(TriageResult.model_validate_json(f.read()))
        return results


def run_edge(input_file: str = "examples/requests/edge_tickets.json") -> None:
    """Edge agent'ı simülasyon modunda çalıştır."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [EDGE] %(levelname)s %(message)s",
    )

    logger.info("=" * 60)
    logger.info("EDGE AGENT STARTING (Local/Offline Mode)")
    logger.info("=" * 60)

    agent = EdgeTriageAgent()
    storage = LocalStorage()

    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_file}")
        return

    with open(input_path) as f:
        tickets_data = json.load(f)

    for ticket_data in tickets_data:
        ticket = Ticket(**ticket_data)
        result = agent.process(ticket)
        file_path = storage.save(result)

        logger.info(
            f"  {result.ticket_id}: "
            f"priority={result.priority.value}, "
            f"category={result.category.value}, "
            f"confidence={result.confidence:.2f}, "
            f"time={result.processing_time_ms:.3f}ms "
            f"→ {file_path}"
        )

    logger.info("=" * 60)
    logger.info(f"Edge processing complete. {len(tickets_data)} tickets processed.")
    logger.info(f"Results saved to: {storage.output_dir}")
    logger.info(f"Pending sync: {len(storage.pending_sync())} results")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_edge()
