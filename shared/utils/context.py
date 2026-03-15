"""
Context Retrieval — Agent'ın karar vermeden önce ek bilgi çekmesi.

Gerçek dünyada context retrieval şunları içerebilir:
- Vector DB'den benzer ticket'ları bulma (RAG)
- Knowledge base'den ilgili dokümanları çekme
- Kullanıcının geçmiş ticket'larını sorgulama
- Sistem durum bilgisini alma

Bu repo'da basit bir in-memory knowledge base ile simüle ediyoruz.
Amacımız context retrieval KAVRAMINI göstermek, production-grade
RAG implementasyonu değil.
"""

from shared.schemas.ticket import Ticket


class ContextProvider:
    """
    Context sağlayıcı abstraction.

    Her deployment modeli aynı context provider'ı kullanabilir,
    ama erişim hızı ve kapsamı farklı olabilir:
    - Batch: Tüm context'e erişir (bulk query)
    - Stream: Event-scoped context
    - Real-time: Hızlı erişim gerekli (cache)
    - Edge: Sınırlı/lokal context
    """

    # basit bir knowledge base simülasyonu
    KNOWLEDGE_BASE: dict[str, str] = {
        "login": "Login issues often relate to the auth service (auth-svc). Check session token expiry and OAuth provider status.",
        "payment": "Payment issues should be escalated to payments team. Check Stripe webhook logs and payment gateway status.",
        "500": "HTTP 500 errors usually indicate backend service failures. Check application logs, database connections, and external API dependencies.",
        "slow": "Performance issues may be caused by: DB query optimization needed, missing cache layer, or external API latency.",
        "ui": "Frontend issues should include browser type and version. Check responsive design breakpoints and CSS specificity.",
        "deploy": "Deployment issues often relate to configuration drift. Check env vars, secrets, and infrastructure-as-code diffs.",
    }

    def get_context(self, ticket: Ticket) -> str | None:
        """
        Ticket'a ilgili context bilgisi döndürür.

        Gerçek dünyada bu bir vector similarity search olabilir.
        Burada basit keyword matching ile simüle ediyoruz.
        """
        text = f"{ticket.title} {ticket.body}".lower()

        matched_contexts = []
        for keyword, context in self.KNOWLEDGE_BASE.items():
            if keyword in text:
                matched_contexts.append(context)

        if not matched_contexts:
            return None

        return "\n---\n".join(matched_contexts)


class LocalContextProvider(ContextProvider):
    """
    Edge deployment için sınırlı context provider.

    Cihaz üzerinde tam knowledge base tutulamayabilir.
    Sadece en sık kullanılan kurallar lokal olarak tutulur.
    """

    KNOWLEDGE_BASE: dict[str, str] = {
        "login": "Possible auth issue. Suggest password reset or session clear.",
        "500": "Server error detected. Escalate to on-call team.",
    }
