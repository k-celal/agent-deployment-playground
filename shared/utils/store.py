"""
Inference Store — Agent sonuçlarının saklandığı depolama katmanı.

Inference store terimi, ML/AI sistemlerinde model çıktılarının
(inference result) persist edildiği yeri ifade eder. Bu depolama:
- Audit trail sağlar (hangi ticket nasıl sınıflandırıldı?)
- Analytics mümkün kılar (doğruluk oranı ne?)
- Idempotency desteği verir (bu ticket zaten işlendi mi?)
- Debugging kolaylaştırır (model neden bu kararı verdi?)

Bu repo'da SQLite kullanıyoruz. Production'da PostgreSQL,
DynamoDB veya benzer bir DB tercih edilir.
"""

import json
import sqlite3
from pathlib import Path

from shared.schemas.result import TriageResult


class InferenceStore:
    """
    SQLite tabanlı inference store.

    Tüm deployment modelleri sonuçları buraya yazar.
    Batch toplu yazar, stream birer birer yazar,
    real-time opsiyonel olarak yazar (veya sadece response döner),
    edge lokal storage'a yazar (bu store'u kullanmayabilir).
    """

    def __init__(self, db_path: str = "inference_store.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS triage_results (
                    ticket_id TEXT PRIMARY KEY,
                    priority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    suggested_team TEXT,
                    status TEXT NOT NULL,
                    processing_time_ms REAL,
                    processed_at TEXT NOT NULL,
                    deployment_mode TEXT,
                    raw_json TEXT NOT NULL
                )
            """)
            conn.commit()

    def save(self, result: TriageResult) -> None:
        """Tek bir triage sonucunu kaydet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO triage_results
                (ticket_id, priority, category, summary, confidence,
                 suggested_team, status, processing_time_ms, processed_at,
                 deployment_mode, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.ticket_id,
                    result.priority.value,
                    result.category.value,
                    result.summary,
                    result.confidence,
                    result.suggested_team,
                    result.status.value,
                    result.processing_time_ms,
                    result.processed_at.isoformat(),
                    result.deployment_mode,
                    result.model_dump_json(),
                ),
            )
            conn.commit()

    def save_batch(self, results: list[TriageResult]) -> None:
        """
        Toplu kayıt — batch deployment için optimize.

        Tek bir transaction'da çok sayıda sonuç yazar.
        Bu, her kayıt için ayrı transaction açmaktan
        çok daha hızlıdır (özellikle binlerce kayıtta).
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO triage_results
                (ticket_id, priority, category, summary, confidence,
                 suggested_team, status, processing_time_ms, processed_at,
                 deployment_mode, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.ticket_id, r.priority.value, r.category.value,
                        r.summary, r.confidence, r.suggested_team,
                        r.status.value, r.processing_time_ms,
                        r.processed_at.isoformat(), r.deployment_mode,
                        r.model_dump_json(),
                    )
                    for r in results
                ],
            )
            conn.commit()

    def get(self, ticket_id: str) -> TriageResult | None:
        """Ticket ID ile sonuç sorgula."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT raw_json FROM triage_results WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()

        if row is None:
            return None
        return TriageResult.model_validate_json(row[0])

    def exists(self, ticket_id: str) -> bool:
        """
        Ticket'ın zaten işlenip işlenmediğini kontrol et.

        Idempotency için kritik: Stream'de aynı event tekrar
        gelirse, bu kontrol ile tekrar işlemeyi önlersin.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM triage_results WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()
        return row is not None

    def get_all(self) -> list[TriageResult]:
        """Tüm sonuçları getir (debug ve raporlama için)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT raw_json FROM triage_results").fetchall()
        return [TriageResult.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        """Toplam sonuç sayısını döndür."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM triage_results").fetchone()
        return row[0] if row else 0
