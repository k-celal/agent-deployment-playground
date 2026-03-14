"""
Ticket triage sistemi için enum tanımları.

Bu enum'lar tüm deployment modellerinde ortaktır.
Agent'ın ürettiği sonuçlar bu kategorilere uymalıdır.
"""

from enum import Enum


class Priority(str, Enum):
    """Ticket öncelik seviyesi. P0 en acil, P3 en düşük."""
    P0 = "P0"  # Kritik — production down, veri kaybı
    P1 = "P1"  # Yüksek — önemli fonksiyon çalışmıyor
    P2 = "P2"  # Orta — kısmi etki, workaround var
    P3 = "P3"  # Düşük — kozmetik, istek, soru


class Category(str, Enum):
    """Ticket kategori sınıflandırması."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    QUESTION = "question"
    INCIDENT = "incident"
    TASK = "task"
    OTHER = "other"


class TriageStatus(str, Enum):
    """Triage işleminin durumu."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"        # Zaten işlenmiş (idempotency)
    LOW_CONFIDENCE = "low_confidence"  # Model emin değil, insana yönlendir
