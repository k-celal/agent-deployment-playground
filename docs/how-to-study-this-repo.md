# Bu Repo'yu Nasıl Çalışmalısın?

> Bu doküman, repo'dan maksimum öğrenme değeri çıkarman için bir rehberdir.

---

## Okuma Sırası

### Aşama 1: Bağlamı Anla (30 dk)

1. **README.md** — Repo'nun amacını ve genel yapıyı kavra
2. **docs/architecture-overview.md** — Sistem tasarımının büyük resmini gör
3. **docs/agent-vs-deployment-model.md** — En kritik ayrımı öğren

### Aşama 2: Ortak Katmanı İncele (45 dk)

4. **shared/schemas/** — Veri modellerini oku (Ticket, TriageResult)
5. **shared/models/base_agent.py** — Agent soyutlamasını anla
6. **shared/models/mock_llm.py** — LLM provider abstraction'ını gör
7. **shared/prompts/triage.py** — Prompt template yapısını incele
8. **shared/utils/** — Context retrieval ve inference store

### Aşama 3: Deployment Modellerini Sırayla İncele (2-3 saat)

Bu sırayla git çünkü karmaşıklık kademeli olarak artar:

9. **batch/** — En basit model, "topla-işle-yaz"
10. **stream/** — Event-driven düşünmeyi öğret
11. **realtime/** — API tabanlı, latency-critical düşünme
12. **edge/** — Kısıtlı ortamda tasarım

Her klasör için:
- Önce README.md'yi oku
- Sonra `app/` içindeki kodu incele
- Son olarak `tests/` ile davranışı doğrula

### Aşama 4: Karşılaştır ve Derinleş (1 saat)

13. **docs/tradeoffs.md** — Trade-off tablosunu çalış
14. **docs/batch-vs-stream-vs-realtime-vs-edge.md** — Detaylı karşılaştırma
15. **docs/common-production-risks.md** — Production'daki gerçek riskler
16. **docs/how-real-systems-become-hybrid.md** — Hibrit sistemler

---

## Klasörler Arası Ne Karşılaştırmalısın?

Her deployment modeline bakarken şu soruları sor:

### Input / Output

| Soru | Batch | Stream | Real-time | Edge |
|---|---|---|---|---|
| Input nereden geliyor? | ? | ? | ? | ? |
| Output nereye gidiyor? | ? | ? | ? | ? |
| Kaç input aynı anda? | ? | ? | ? | ? |

**Tabloyu kendin doldur.** Kodu okuyarak cevapları bul.

### Hata Yönetimi

- Batch'te bir ticket işlenemezse ne olur?
- Stream'de bir event tekrar gelirse ne olur (idempotency)?
- Real-time'da timeout olursa ne olur?
- Edge'de network yoksa ne olur?

### Scale

- Batch'i daha hızlı yapmak için ne yaparsın?
- Stream'de daha fazla event gelirse ne yaparsın?
- Real-time'da 10x trafik gelirse ne yaparsın?
- Edge'de 1000 cihaza deploy edersen ne değişir?

---

## Odaklanman Gereken Kavramlar

### Temel Kavramlar

- [ ] Inference Store: Agent sonuçlarının saklandığı yer
- [ ] Context Retrieval: Agent'ın karar vermek için ek bilgi çekmesi
- [ ] Agent Abstraction: İş mantığını deployment'tan ayırmak
- [ ] Idempotency: Aynı işlemin tekrar çalıştırılmasının güvenli olması
- [ ] Graceful Degradation: Sistemin kısmen çalışmaya devam etmesi

### İleri Kavramlar

- [ ] Dead Letter Queue: İşlenemeyen event'lerin ayrı yere yazılması
- [ ] Circuit Breaker: Arızalı servise çok fazla istek göndermemek
- [ ] Backpressure: Tüketici yetişemediğinde üreticiyi yavaşlatmak
- [ ] Cold Start: Servisin ilk isteğe kadar ısınma süresi
- [ ] Feature Drift: Production'da model davranışının değişmesi

---

## Pratik Egzersizler

### Egzersiz 1: Yeni Bir Agent Ekle

`shared/models/` altında yeni bir agent yaz (örn. `SentimentAgent`) ve onu 4 deployment modeline de bağla. Agent logic'in deployment'tan bağımsız olduğunu pratikte gör.

### Egzersiz 2: Gerçek LLM Bağla

`shared/models/mock_llm.py` yerine gerçek bir LLM provider (OpenAI, Anthropic) bağla. Sadece bu bir dosyayı değiştirerek tüm deployment'ların çalışmaya devam ettiğini gözlemle.

### Egzersiz 3: Hata Senaryoları

Her deployment modeline hata enjekte et:
- Batch: Input dosyasındaki bozuk kayıt
- Stream: Tekrarlayan event
- Real-time: Timeout
- Edge: Context store'a erişim yok

Sistemlerin nasıl tepki verdiğini incele.

### Egzersiz 4: Hibrit Sistem Tasarla

4 modeli birleştiren bir hibrit mimari çiz:
- Real-time API → kullanıcıya anlık cevap
- Cevabı queue'ya at → Stream consumer zenginleştirsin
- Gece batch job → istatistik ve raporlama
- Edge → offline fallback

---

## Interview / Sistem Tasarımı Çıkarımları

Bu repo'yu çalıştıktan sonra şu tarz sorulara güçlü cevap verebilmelisin:

1. **"Design a support ticket classification system"**
   - Deployment modellerini tartış, trade-off'ları açıkla

2. **"How would you scale an AI agent from 100 to 100K requests/day?"**
   - Batch → Stream → Real-time geçişini anlat

3. **"What are the trade-offs of running AI at the edge?"**
   - Latency, privacy, model size, offline capability

4. **"How do you ensure reliability in an event-driven AI system?"**
   - Idempotency, dead letter queue, retry strategy

5. **"How do you separate agent logic from infrastructure?"**
   - Abstraction, dependency injection, shared modules
