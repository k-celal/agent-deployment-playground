# Agent Deployment Playground

> **Aynı AI agent use-case'inin batch, stream, real-time ve edge deployment modellerinde nasıl tasarlanıp çalıştırıldığını öğreten eğitim reposu.**

⚠️ **Bu repo tek bir ürün değildir.** Amacı, bir AI mühendisinin deployment mimarilerini, trade-off'ları ve runtime pattern'lerini derinlemesine anlamasını sağlamaktır.

---

## Bu Repo Ne Öğretir?

Bir AI agent sistemi yazmak ile onu **nasıl deploy ettiğin** çok farklı disiplinlerdir. Çoğu eğitim materyali agent logic'e odaklanır ama gerçek dünyada karşılaştığın soruların büyük kısmı deployment katmanındadır:

- Latency mi, throughput mu önemli?
- Veri batch halinde mi geliyor, sürekli mi akıyor?
- Kullanıcı anlık cevap mı bekliyor, offline mı çalışacak?
- Sistem scale edilebilir mi? Maliyeti ne?

Bu repo, **tek bir use-case** (ticket-triage-agent) üzerinden 4 farklı deployment modelini karşılaştırır:

| Deployment Tipi | Ne Zaman Kullanılır | Gerçek Dünya Örneği |
|---|---|---|
| **Batch** | Veri toplu geliyorsa, anlık cevap gerekmiyorsa | Gece çalışan ticket zenginleştirme |
| **Stream** | Veri sürekli akıyorsa, event-driven işleme gerekiyorsa | Akan ticket update'lerini izleme |
| **Real-time** | Kullanıcı anlık cevap bekliyorsa | Chatbot / API assistant |
| **Edge** | Düşük latency, privacy veya offline gerekiyorsa | Cihaz üzeri sınıflandırma |

---

## Use-Case: Ticket Triage Agent

Tüm 4 deployment modeli aynı iş mantığını kullanır:

```
Input (ticket/event/request)
    → Context Retrieval (geçmiş ticket'lar, KB, kullanıcı bilgisi)
        → Reasoning (öncelik belirleme, kategorizasyon, özet)
            → Output (sonuç depolama veya response dönme)
```

### Her Modelde Ne Olur?

- **Batch:** Bir klasördeki/veritabanındaki ticket'ları toplu okur, agent ile işler, sonuçları inference store'a yazar.
- **Stream:** Bir queue/event bus'tan gelen ticket event'lerini birer birer tüketir, işler, sonucu yazar.
- **Real-time:** Bir HTTP API üzerinden gelen anlık isteği alır, agent'ı çalıştırır, sonucu hemen döner.
- **Edge:** Lokal/cihaz üzeri sınırlı kaynaklarla çalışır, basitleştirilmiş agent mantığı kullanır.

---

## Dizin Yapısı

```
agent-deployment-playground/
├── README.md                  # Bu dosya
├── requirements.txt           # Python bağımlılıkları
├── docker-compose.yml         # Tüm servisleri ayağa kaldırma
├── Makefile                   # Kolay komutlar
│
├── docs/                      # Eğitim dokümanları
│   ├── architecture-overview.md
│   ├── batch-vs-stream-vs-realtime-vs-edge.md
│   ├── tradeoffs.md
│   ├── glossary.md
│   ├── how-to-study-this-repo.md
│   ├── agent-vs-deployment-model.md
│   ├── common-production-risks.md
│   └── how-real-systems-become-hybrid.md
│
├── shared/                    # Ortak agent mantığı ve şemalar
│   ├── schemas/               # Pydantic modelleri
│   ├── models/                # Agent soyutlamaları
│   ├── prompts/               # Prompt template'leri
│   ├── types/                 # Tip tanımları
│   └── utils/                 # Yardımcı fonksiyonlar
│
├── batch/                     # Batch deployment
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
│
├── stream/                    # Stream deployment
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
│
├── realtime/                  # Real-time deployment
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
│
├── edge/                      # Edge deployment
│   ├── app/
│   ├── tests/
│   ├── simulation/
│   └── README.md
│
└── examples/                  # Örnek veri
    ├── requests/
    ├── events/
    └── outputs/
```

---

## Hızlı Başlangıç

### Gereksinimler

- Python 3.11+
- Docker & Docker Compose (opsiyonel)

### Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/YOUR_USER/agent-deployment-playground.git
cd agent-deployment-playground

# Virtual environment oluştur
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### Her Modu Çalıştırma

```bash
# Batch: toplu ticket işleme
make run-batch

# Stream: event-driven işleme
make run-stream

# Real-time: API servisi başlat
make run-realtime

# Edge: yerel simülasyon
make run-edge

# Testleri çalıştır
make test
```

### Docker ile

```bash
docker-compose up
```

---

## Karşılaştırma Tablosu

| Özellik | Batch | Stream | Real-time | Edge |
|---|---|---|---|---|
| **Latency** | Yüksek (dakika-saat) | Orta (saniye) | Düşük (ms) | Çok düşük (ms) |
| **Throughput** | Çok yüksek | Yüksek | Orta | Düşük |
| **Ölçeklenme** | Horizontal (worker) | Partition-based | Load balancer | Cihaz başına |
| **Maliyet** | Düşük (off-peak) | Orta | Yüksek (her zaman açık) | Cihaz maliyeti |
| **Karmaşıklık** | Düşük | Orta-Yüksek | Orta | Yüksek (kısıtlar) |
| **Veri Erişimi** | Tam (bulk) | Event-scoped | Request-scoped | Sınırlı/lokal |
| **Hata Yönetimi** | Retry batch | Idempotent replay | Request retry | Graceful degrade |
| **Kullanım Alanı** | Raporlama, enrichment | Monitoring, alerting | Chatbot, API | Offline, privacy |

---

## Production'da Gerçek Sistemler Hibrit'tir

Gerçek dünyada tek bir deployment modeli yetmez. Çoğu production sistemi birden fazla modeli birleştirir:

```
┌─────────────────────────────────────────────┐
│              Hibrit Mimari Örneği            │
│                                             │
│  Real-time API ──→ Anlık kullanıcı cevabı   │
│       │                                     │
│       ▼                                     │
│  Stream Worker ──→ Event'leri işle          │
│       │                                     │
│       ▼                                     │
│  Batch Job ──────→ Gece toplu enrichment    │
│                                             │
│  Edge Device ────→ Offline sınıflandırma    │
└─────────────────────────────────────────────┘
```

---

## Öğrenme Rehberi

Bu repo'yu nasıl çalışacağın hakkında detaylı rehber: [docs/how-to-study-this-repo.md](docs/how-to-study-this-repo.md)

### Önerilen Okuma Sırası

1. Bu README'yi oku
2. [docs/architecture-overview.md](docs/architecture-overview.md) — Sistem tasarımını anla
3. [docs/agent-vs-deployment-model.md](docs/agent-vs-deployment-model.md) — Agent logic vs deployment farkı
4. `shared/` klasörünü incele — Ortak soyutlamalar
5. `batch/` → `stream/` → `realtime/` → `edge/` sırasıyla ilerle
6. [docs/tradeoffs.md](docs/tradeoffs.md) — Trade-off'ları karşılaştır
7. [docs/how-real-systems-become-hybrid.md](docs/how-real-systems-become-hybrid.md) — Gerçek dünya

---

## Katkıda Bulunma

Bu bir eğitim reposudur. Yeni deployment pattern'leri, daha iyi açıklamalar veya ek diyagramlar ile katkıda bulunabilirsiniz.

---

## Lisans

MIT License
