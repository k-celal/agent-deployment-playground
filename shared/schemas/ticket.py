"""
Ticket veri modeli.

Bu Pydantic modeli, tüm deployment modellerinde kullanılan
ortak ticket şemasını tanımlar. Gerçek dünyada bu model
farklı kaynaklardan (API, dosya, event) gelen veriyi
standart bir formata dönüştürür.
"""

from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    """
    Destek ticket'ının temel veri modeli.

    Tüm deployment modelleri bu modeli kullanır:
    - Batch: Dosyadan/DB'den toplu okunan ticket
    - Stream: Event'ten parse edilen ticket
    - Real-time: API request'inden oluşturulan ticket
    - Edge: Lokal input'tan oluşturulan ticket
    """
    id: str = Field(..., description="Unique ticket ID (ör: TICKET-1234)")
    title: str = Field(..., description="Ticket başlığı")
    body: str = Field(..., description="Ticket detay açıklaması")
    user_email: Optional[str] = Field(None, description="Ticket oluşturan kullanıcı")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict, description="Ek metadata (source, tags, vb.)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "TICKET-1234",
                    "title": "Login sayfası 500 hatası veriyor",
                    "body": "Chrome'da login olmaya çalıştığımda 500 Internal Server Error alıyorum.",
                    "user_email": "customer@example.com",
                    "created_at": "2024-01-15T10:30:00Z",
                    "metadata": {"source": "web", "browser": "chrome"}
                }
            ]
        }
    }
