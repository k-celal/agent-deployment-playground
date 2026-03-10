"""
Base Agent — Tüm deployment modellerinin paylaştığı agent soyutlaması.

BU DOSYA REPO'NUN KALBİDİR.

Buradaki BaseTriageAgent sınıfı, agent logic'in deployment'tan
nasıl ayrıldığını gösterir. 4 farklı deployment modeli
(batch, stream, realtime, edge) bu sınıfı kullanır.

Tasarım kararı: Agent bir "function" değil "class" olarak tasarlandı çünkü:
1. State tutabilir (LLM client, context store referansı)
2. Dependency injection yapılabilir (mock vs gerçek LLM)
3. Alt sınıflarla özelleştirilebilir (edge'de lightweight versiyon)
"""

import time
from abc import ABC, abstractmethod

from shared.models.mock_llm import BaseLLM
from shared.prompts.triage import TRIAGE_SYSTEM_PROMPT, build_triage_prompt
from shared.schemas.result import TriageResult
from shared.schemas.ticket import Ticket
from shared.types.enums import Category, Priority, TriageStatus
from shared.utils.context import ContextProvider


class BaseTriageAgent:
    """
    Ticket triage agent'ının temel implementasyonu.

    Bu agent şu adımları sırasıyla uygular:
    1. Input Parsing — ticket verisini validate et
    2. Context Retrieval — ilgili ek bilgiyi getir
    3. Reasoning — LLM'e prompt + ticket + context gönder
    4. Output Generation — sonucu standart formata çevir

    Her deployment modeli bu agent'ı doğrudan kullanır.
    Farklılıklar agent'ın DIŞINDA kalır (nasıl tetiklenir,
    veriyi nereden alır, sonucu nereye yazar).
    """

    def __init__(
        self,
        llm: BaseLLM,
        context_provider: ContextProvider | None = None,
        deployment_mode: str = "unknown",
    ):
        self.llm = llm
        self.context_provider = context_provider
        self.deployment_mode = deployment_mode

    def process(self, ticket: Ticket) -> TriageResult:
        """
        Ana agent akışı: input → context → reasoning → output.

        Bu method her deployment modunda çağrılır. Deployment
        katmanı sadece ticket'ı nereden aldığını ve result'ı
        nereye yazdığını belirler.
        """
        start_time = time.time()

        try:
            context = self._retrieve_context(ticket)
            llm_response = self._reason(ticket, context)
            result = self._parse_response(ticket, llm_response)

            elapsed_ms = (time.time() - start_time) * 1000
            result.processing_time_ms = elapsed_ms
            result.deployment_mode = self.deployment_mode

            return result

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return TriageResult(
                ticket_id=ticket.id,
                priority=Priority.P2,
                category=Category.OTHER,
                summary=f"Triage failed: {str(e)}",
                confidence=0.0,
                status=TriageStatus.FAILED,
                processing_time_ms=elapsed_ms,
                deployment_mode=self.deployment_mode,
            )

    def _retrieve_context(self, ticket: Ticket) -> str | None:
        """
        Opsiyonel context bilgisini getirir.

        Production'da bu adım:
        - Vector DB'den benzer ticket'ları çekebilir (RAG)
        - Knowledge base'den ilgili dokümanları bulabilir
        - Kullanıcı geçmişini sorgulayabilir

        Edge deployment'ta context sınırlı veya hiç olmayabilir.
        """
        if self.context_provider is None:
            return None
        return self.context_provider.get_context(ticket)

    def _reason(self, ticket: Ticket, context: str | None) -> dict:
        """
        LLM'e prompt gönderir ve sonucu alır.

        Bu abstraction sayesinde LLM provider'ı değiştirmek
        (OpenAI → Anthropic → lokal model) agent logic'ini
        etkilemez.
        """
        prompt = build_triage_prompt(
            ticket_id=ticket.id,
            title=ticket.title,
            body=ticket.body,
            user_email=ticket.user_email,
            created_at=str(ticket.created_at),
            context=context,
        )

        return self.llm.generate(
            system_prompt=TRIAGE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

    def _parse_response(self, ticket: Ticket, response: dict) -> TriageResult:
        """LLM yanıtını TriageResult'a dönüştürür."""
        return TriageResult(
            ticket_id=ticket.id,
            priority=Priority(response.get("priority", "P2")),
            category=Category(response.get("category", "other")),
            summary=response.get("summary", "No summary available"),
            confidence=float(response.get("confidence", 0.5)),
            suggested_team=response.get("suggested_team"),
            status=TriageStatus.SUCCESS,
        )
