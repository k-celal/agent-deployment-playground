"""
Ticket triage prompt template'leri.

Prompt'lar agent logic'in bir parçasıdır — deployment'tan bağımsızdır.
Aynı prompt batch'te de, real-time'da da, edge'de de kullanılır.

Production'da prompt management ayrı bir disiplindir:
- Versioning (prompt'un hangi versiyonu kullanıldı?)
- A/B testing (hangi prompt daha iyi sonuç veriyor?)
- Template injection güvenliği
"""

TRIAGE_SYSTEM_PROMPT = """You are a ticket triage agent for a software support team.

Your job is to analyze incoming support tickets and produce:
1. Priority level (P0, P1, P2, P3)
2. Category (bug, feature_request, question, incident, task, other)
3. A brief summary of the issue
4. Suggested team assignment
5. A confidence score (0.0 to 1.0)

Priority Guidelines:
- P0: Production is down, data loss, security breach
- P1: Major feature broken, no workaround
- P2: Feature partially broken, workaround exists
- P3: Cosmetic issue, question, minor request

Category Guidelines:
- bug: Something is broken or not working as expected
- feature_request: User wants new functionality
- question: User needs information or help
- incident: Production issue or outage
- task: Internal task or maintenance
- other: Doesn't fit above categories

Always respond in valid JSON format."""


TRIAGE_USER_PROMPT_TEMPLATE = """Analyze the following support ticket:

Ticket ID: {ticket_id}
Title: {title}
Body: {body}
User: {user_email}
Created: {created_at}

{context_section}

Respond with a JSON object containing:
- priority: string (P0, P1, P2, P3)
- category: string (bug, feature_request, question, incident, task, other)
- summary: string (brief analysis, max 2 sentences)
- suggested_team: string (team name)
- confidence: float (0.0 to 1.0)"""


def build_triage_prompt(
    ticket_id: str,
    title: str,
    body: str,
    user_email: str | None = None,
    created_at: str | None = None,
    context: str | None = None,
) -> str:
    """Ticket verisi ve opsiyonel context ile triage prompt'u oluşturur."""
    context_section = ""
    if context:
        context_section = f"Additional Context:\n{context}"

    return TRIAGE_USER_PROMPT_TEMPLATE.format(
        ticket_id=ticket_id,
        title=title,
        body=body,
        user_email=user_email or "unknown",
        created_at=created_at or "unknown",
        context_section=context_section,
    )
