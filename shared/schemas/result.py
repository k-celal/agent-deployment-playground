"""
Agent triage sonuç modeli.

Bu model, agent'ın bir ticket'ı işledikten sonra ürettiği
sonucu temsil eder. Tüm deployment modellerinde aynı output
formatı kullanılır — bu tutarlılık agent logic ile deployment'ın
ayrılmasının bir sonucudur.
"""

from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field

from shared.types.enums import Category, Priority, TriageStatus


class TriageResult(BaseModel):
    """
    Agent'ın ürettiği triage sonucu.

    Her deployment modeli bu formatı döner:
    - Batch: Inference store'a bu formatta yazar
    - Stream: Event sonucu olarak bu formatı produce eder
    - Real-time: HTTP response olarak bu formatı döner
    - Edge: Lokal storage'a bu formatta kaydeder
    """
    ticket_id: str = Field(..., description="İşlenen ticket'ın ID'si")
    priority: Priority = Field(..., description="Belirlenen öncelik seviyesi")
    category: Category = Field(..., description="Belirlenen kategori")
    summary: str = Field(..., description="Agent tarafından üretilen özet")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model güven skoru (0.0-1.0). Production'da düşük confidence'ı insana yönlendir."
    )
    suggested_team: Optional[str] = Field(None, description="Önerilen takım ataması")
    status: TriageStatus = Field(default=TriageStatus.SUCCESS)
    processing_time_ms: Optional[float] = Field(None, description="İşleme süresi (ms)")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deployment_mode: Optional[str] = Field(
        None,
        description="Hangi deployment modunda işlendi (batch/stream/realtime/edge)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticket_id": "TICKET-1234",
                    "priority": "P1",
                    "category": "bug",
                    "summary": "Kullanıcı Chrome'da login sırasında 500 hatası alıyor. Authentication servisinde sorun olabilir.",
                    "confidence": 0.87,
                    "suggested_team": "backend-auth",
                    "status": "success",
                    "processing_time_ms": 145.2,
                    "deployment_mode": "realtime"
                }
            ]
        }
    }
