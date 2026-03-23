"""
Real-time API — FastAPI tabanlı anlık ticket triage servisi.

Bu modül, real-time deployment modelinin ana bileşenidir.
Kullanıcıdan gelen HTTP isteğini alır, agent'ı çalıştırır
ve sonucu anında döner.

Real-time processing şu durumlarda kullanılır:
- Kullanıcı doğrudan etkileşim halindeyse (chatbot, form)
- Anlık cevap gerekiyorsa (< 500ms ideal)
- Request/response pattern uygunsa
- Sonucun hemen gösterilmesi gerekiyorsa

Production'da dikkat edilecekler:
- Timeout management (LLM çağrısı çok uzun sürerse?)
- Rate limiting (aşırı istek koruması)
- Circuit breaker (bağımlı servis çökerse?)
- Caching (aynı/benzer soru tekrar gelirse?)
- Health check endpoint (load balancer için)
- Graceful shutdown (in-flight request'leri tamamla)
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from shared.models.base_agent import BaseTriageAgent
from shared.models.mock_llm import MockLLM
from shared.schemas.result import TriageResult
from shared.schemas.ticket import Ticket
from shared.types.enums import Category, Priority
from shared.utils.context import ContextProvider
from shared.utils.store import InferenceStore

logger = logging.getLogger(__name__)

agent: BaseTriageAgent | None = None
store: InferenceStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.

    Startup'ta agent ve store'u initialize et.
    Shutdown'da temizlik yap.

    Production'da burada:
    - DB connection pool başlatılır
    - Model yüklenir (warm-up)
    - Health check ayarlanır
    """
    global agent, store

    logger.info("Initializing real-time triage service...")

    llm = MockLLM(latency_ms=50.0)
    context = ContextProvider()
    agent = BaseTriageAgent(
        llm=llm, context_provider=context, deployment_mode="realtime"
    )
    store = InferenceStore(db_path="data/realtime_inference.db")

    logger.info("Real-time triage service ready.")
    yield
    logger.info("Shutting down real-time triage service.")


app = FastAPI(
    title="Ticket Triage API",
    description="Real-time AI-powered ticket triage service. "
                "Part of agent-deployment-playground educational repository.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response Modelleri ---

class TriageRequest(BaseModel):
    """API'ye gelen triage isteği."""
    ticket_id: str = Field(..., description="Ticket ID")
    title: str = Field(..., description="Ticket başlığı")
    body: str = Field(..., description="Ticket detayı")
    user_email: Optional[str] = Field(None, description="Kullanıcı email")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticket_id": "TICKET-1234",
                    "title": "Login page returns 500",
                    "body": "When I try to login with Chrome, I get a 500 error.",
                    "user_email": "user@example.com"
                }
            ]
        }
    }


class TriageResponse(BaseModel):
    """API'nin döndüğü triage sonucu."""
    ticket_id: str
    priority: Priority
    category: Category
    summary: str
    confidence: float
    suggested_team: Optional[str]
    processing_time_ms: float


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    store_count: int


# --- Endpoints ---

@app.post("/triage", response_model=TriageResponse)
async def triage_ticket(request: TriageRequest):
    """
    Ticket'ı analiz et ve triage sonucunu döndür.

    Bu endpoint real-time deployment'ın kalbidir:
    - İstek gelir
    - Agent anında çalışır
    - Sonuç anında döner

    Production'da bu endpoint'e:
    - Rate limiting eklenir (ör: 100 req/min)
    - Timeout eklenir (ör: 5 saniye)
    - Authentication eklenir
    - Response caching yapılabilir
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    ticket = Ticket(
        id=request.ticket_id,
        title=request.title,
        body=request.body,
        user_email=request.user_email,
    )

    result = agent.process(ticket)

    # Opsiyonel: Sonucu inference store'a da kaydet (audit trail)
    if store is not None:
        store.save(result)

    return TriageResponse(
        ticket_id=result.ticket_id,
        priority=result.priority,
        category=result.category,
        summary=result.summary,
        confidence=result.confidence,
        suggested_team=result.suggested_team,
        processing_time_ms=result.processing_time_ms or 0.0,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Load balancer bu endpoint'i kullanarak servisin
    sağlıklı olup olmadığını kontrol eder. Sağlıksız
    instance'lar trafikten çıkarılır.
    """
    return HealthResponse(
        status="healthy" if agent is not None else "unhealthy",
        service="ticket-triage-realtime",
        timestamp=datetime.now(UTC).isoformat(),
        store_count=store.count() if store else 0,
    )


@app.get("/results/{ticket_id}")
async def get_result(ticket_id: str):
    """Daha önce işlenmiş bir ticket'ın sonucunu sorgula."""
    if store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    result = store.get(ticket_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No result found for {ticket_id}")

    return result


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """
    Her response'a processing time header'ı ekle.

    Production'da latency tracking için kullanılır.
    Monitoring sistemi bu header'ı okuyarak
    latency metriklerini toplar.
    """
    start_time = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start_time) * 1000
    response.headers["X-Processing-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


def run_server():
    """API sunucusunu başlat."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [REALTIME] %(levelname)s %(message)s",
    )

    logger.info("=" * 60)
    logger.info("REAL-TIME API SERVER STARTING")
    logger.info("=" * 60)

    uvicorn.run(
        "realtime.app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
