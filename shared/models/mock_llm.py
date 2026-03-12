"""
LLM Provider Abstraction ve Mock Implementation.

Bu dosya iki şeyi gösterir:
1. BaseLLM: LLM provider'ı değiştirilebilir kılmak için abstraction
2. MockLLM: Gerçek API çağrısı yapmadan test edilebilir mock

Production'da BaseLLM'i extend ederek:
- OpenAILLM
- AnthropicLLM
- LocalLLM (Ollama, vLLM)
gibi implementasyonlar yazarsın.

Bu repo deployment pattern'leri öğrettiği için gerçek LLM bağlantısı
başlangıçta gereksizdir. MockLLM deterministic sonuçlar döner,
böylece deployment katmanını izole olarak test edebilirsin.
"""

import random
import time
from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """
    LLM provider abstraction.

    Tüm LLM provider'lar bu interface'i implement eder.
    Agent bu interface üzerinden çalışır, hangi provider
    olduğunu bilmez — dependency injection.
    """

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> dict:
        """
        LLM'e prompt gönder, structured response al.

        Returns:
            dict: {priority, category, summary, suggested_team, confidence}
        """
        ...


class MockLLM(BaseLLM):
    """
    Test ve geliştirme için mock LLM.

    Ticket başlığı ve body'sindeki anahtar kelimelere göre
    deterministik sonuçlar döner. Bu sayede:
    - API key gerektirmez
    - Hızlı çalışır
    - Sonuçlar öngörülebilir
    - Deployment katmanı izole test edilebilir

    Production'da bunu gerçek LLM provider ile değiştirirsin.
    """

    KEYWORD_RULES: list[tuple[list[str], str, str, str]] = [
        # (keywords, priority, category, team)
        (["500", "error", "crash", "down", "outage"], "P0", "incident", "platform-ops"),
        (["login", "auth", "password", "session", "token"], "P1", "bug", "backend-auth"),
        (["slow", "timeout", "latency", "performance"], "P1", "bug", "backend-perf"),
        (["payment", "billing", "charge", "invoice"], "P1", "bug", "payments"),
        (["ui", "button", "layout", "css", "display"], "P2", "bug", "frontend"),
        (["feature", "request", "want", "need", "add"], "P3", "feature_request", "product"),
        (["how", "what", "where", "help", "question"], "P3", "question", "support"),
        (["test", "qa", "regression", "flaky"], "P2", "task", "qa-team"),
    ]

    def __init__(self, latency_ms: float = 50.0, failure_rate: float = 0.0):
        """
        Args:
            latency_ms: Simüle edilen LLM latency'si (gerçek LLM 200-2000ms arası)
            failure_rate: Hata oranı (0.0-1.0). Production'da ~%1-5 arası normal.
        """
        self.latency_ms = latency_ms
        self.failure_rate = failure_rate

    def generate(self, system_prompt: str, user_prompt: str) -> dict:
        time.sleep(self.latency_ms / 1000)

        if random.random() < self.failure_rate:
            raise RuntimeError("MockLLM simulated failure (LLM API error)")

        text = user_prompt.lower()

        for keywords, priority, category, team in self.KEYWORD_RULES:
            if any(kw in text for kw in keywords):
                confidence = round(random.uniform(0.75, 0.95), 2)
                return {
                    "priority": priority,
                    "category": category,
                    "summary": self._generate_summary(text, category, priority),
                    "suggested_team": team,
                    "confidence": confidence,
                }

        return {
            "priority": "P2",
            "category": "other",
            "summary": "Ticket requires manual review. No clear pattern matched.",
            "suggested_team": "support",
            "confidence": round(random.uniform(0.3, 0.5), 2),
        }

    def _generate_summary(self, text: str, category: str, priority: str) -> str:
        summaries = {
            ("incident", "P0"): "Critical production issue detected. Immediate attention required.",
            ("bug", "P1"): "High-priority bug affecting core functionality. No workaround available.",
            ("bug", "P2"): "Bug identified with partial impact. Workaround may be possible.",
            ("feature_request", "P3"): "Feature request logged. Needs product review for prioritization.",
            ("question", "P3"): "User inquiry received. Standard support response recommended.",
            ("task", "P2"): "Internal task identified. Scheduling needed.",
        }
        return summaries.get(
            (category, priority),
            f"Ticket classified as {category} with {priority} priority.",
        )
