# Terimler Sözlüğü (Glossary)

> Bu doküman, repo'da ve genel AI/MLOps mühendisliğinde sıkça karşılaşılan terimleri açıklar.

---

## A

### Agent
Bir amacı gerçekleştirmek için araçlar (tools), bağlam (context) ve akıl yürütme (reasoning) kullanan AI sistemi. Sadece chatbot değildir — ticket sınıflandırma, veri zenginleştirme, karar destek gibi görevleri de yapabilir.

### Agent Abstraction
Agent'ın iş mantığını, çalıştırıldığı ortamdan (deployment) ayıran yazılım tasarım deseni. Bu repo'da `shared/models/base_agent.py` bu rolü üstlenir.

---

## B

### Backpressure
Tüketici (consumer) üreticinin (producer) hızına yetişemediğinde, üreticiyi yavaşlatma mekanizması. Stream sistemlerinde kritiktir. Yoksa queue şişer ve sistem çöker.

### Batch Processing
Verilerin toplu olarak (bulk) işlenmesi modeli. Veriler biriktirilir, belirli aralıklarla (örn. saatlik, günlük) toplu olarak işlenir. Yüksek throughput, yüksek latency.

---

## C

### Circuit Breaker
Arızalı bir servise sürekli istek göndermek yerine, belirli sayıda başarısız denemeden sonra "devreyi kesen" pattern. Servise dinlenme süresi tanır.

### Cold Start
Bir servisin ilk isteğe kadar olan hazırlanma süresi. Serverless ortamlarda (Lambda, Cloud Functions) belirgindir. Model yükleme süresi cold start'ı artırır.

### Context Retrieval
Agent'ın karar vermeden önce ek bilgi çekmesi. Örnekler: geçmiş ticket'lar, knowledge base, kullanıcı profili. RAG (Retrieval-Augmented Generation) buna bir yaklaşımdır.

### Consumer
Queue veya event bus'tan mesaj/event okuyan bileşen. Stream mimarisinin temel yapı taşı.

---

## D

### Dead Letter Queue (DLQ)
İşlenemeyen mesajların/event'lerin yönlendirildiği özel queue. Hata analizi ve tekrar deneme için kullanılır. Bir "çöp kutusu" değil, bir "soruşturma alanı"dır.

### Deployment Model
Agent'ın nasıl çalıştırıldığını, tetiklendiğini ve ölçeklendiğini belirleyen mimari karar. Bu repo'da 4 model gösterilir: batch, stream, real-time, edge.

---

## E

### Edge Computing
Hesaplamanın merkezi sunucular yerine verinin kaynağına yakın (cihaz üzeri, yerel ağ) yapılması. Düşük latency, privacy ve offline çalışma avantajları sunar.

### Edge Inference
ML/AI model çıkarımının (inference) cihaz üzerinde yapılması. Model boyutu, bellek ve işlem gücü kısıtları altında çalışır.

### Event-Driven Architecture
Sistemlerin event'ler (olaylar) üzerinden iletişim kurduğu mimari stil. Bir bileşen event üretir, diğer bileşenler bu event'e tepki verir. Stream processing'in temelidir.

---

## F

### Feature Drift
Production'da model girişlerinin (feature'ların) zamanla dağılımının değişmesi. Model doğruluğunun düşmesine neden olabilir. Monitoring gerektirir.

---

## G

### Graceful Degradation
Bir bileşen arızalandığında sistemin tamamen çökmek yerine azaltılmış işlevsellikle çalışmaya devam etmesi. Edge'de kritiktir: LLM çalışmazsa kural tabanlı fallback devreye girer.

---

## H

### Hallucination
LLM'in gerçekte olmayan bilgiyi güvenle üretmesi. Real-time deployment'ta özellikle risklidir çünkü cevap anında kullanıcıya gider. Doğrulama mekanizmaları gerektirir.

### Horizontal Scaling
Kapasiteyi artırmak için daha fazla makine/instance ekleme. "Daha güçlü makine" yerine "daha fazla makine" yaklaşımı. Batch worker'ları ve stream consumer'ları genellikle horizontal scale edilir.

---

## I

### Idempotency
Aynı işlemin birden fazla kez çalıştırılmasının, tek kez çalıştırılmasıyla aynı sonucu vermesi. Stream processing'te kritiktir çünkü event'ler tekrar gönderilebilir (at-least-once delivery).

### Inference
ML/AI modelinin girişe (input) karşı tahmin/çıktı üretmesi. "Training" öğrenme aşaması, "inference" uygulama aşamasıdır.

### Inference Store
Agent'ın ürettiği sonuçların (inference result) saklandığı depolama sistemi. Veritabanı, dosya sistemi veya cache olabilir. Bu repo'da SQLite ile simüle edilir.

---

## L

### Latency
Bir isteğin gönderilmesinden cevabın alınmasına kadar geçen süre. Real-time'da milisaniye, batch'te saatler olabilir. "Latency budget" her bileşene ayrılan süre dilimidir.

### Load Balancer
Gelen istekleri birden fazla sunucuya dağıtan bileşen. Real-time deployment'ta scale ve availability için kullanılır.

---

## M

### Mock
Test veya geliştirme amaçlı gerçek bileşenin yerine geçen sahte implementasyon. Bu repo'da `MockLLM` gerçek LLM yerine deterministic yanıtlar döner.

---

## O

### Observability
Bir sistemin dışarıdan bakarak iç durumunun anlaşılabilmesi. Üç ayağı: logging (ne oldu?), metrics (ne kadar?), tracing (nasıl aktı?). Tüm deployment modellerinde kritiktir.

### Orchestration
Birden fazla bileşenin koordineli çalıştırılması. Örneğin: "önce context çek, sonra LLM'e gönder, sonra sonucu kaydet" akışının yönetimi.

---

## P

### Partition
Stream'de veriyi paralel işlenebilir parçalara ayırma. Kafka'da partition, her biri farklı consumer'a atanabilir. Throughput artırmanın temel yoludur.

### Provider Abstraction
LLM veya diğer dış servislerin arkasına interface koyarak değiştirilebilir hale getirme. Bu repo'da `BaseLLM` sınıfı bu abstraction'ı sağlar.

---

## Q

### Queue
Mesajların sırayla tutulduğu ve tüketildiği veri yapısı. Kafka, RabbitMQ, SQS gibi sistemlerle implement edilir. Üretici ve tüketiciyi birbirinden ayırır (decoupling).

---

## R

### Rate Limiting
Belirli bir zaman diliminde kabul edilen istek sayısını sınırlama. API'leri aşırı yükten korur. LLM API'lerinin çoğunda token/dakika limiti vardır.

### Retry Strategy
Başarısız işlemleri tekrar deneme stratejisi. Basit retry, exponential backoff, jitter ekleme gibi yaklaşımlar vardır.

---

## S

### Scale (Ölçekleme)
Sistemin artan yükü karşılayabilecek şekilde büyütülmesi. Vertical (daha güçlü makine) veya horizontal (daha fazla makine) olabilir.

### Stream Processing
Verilerin sürekli akan bir akış (stream) olarak, geldiği anda işlenmesi. Batch'in tersi: veri biriktirilmez, geldiğinde işlenir.

---

## T

### Throughput
Birim zamanda işlenen iş miktarı. "Saniyede kaç ticket işlenir?" sorusunun cevabı. Batch yüksek throughput, düşük latency; real-time düşük latency, orta throughput sunar.

### Timeout
Bir işlemin belirli sürede tamamlanmaması durumunda iptal edilmesi. Real-time'da kritiktir: LLM 30 saniye düşünürse kullanıcı bekleyemez.

### Triage
Gelen taleplerin öncelik ve kategoriye göre sınıflandırılması. Bu repo'nun use-case'i "ticket triage" — destek taleplerini sınıflandırma.

---

## W

### Worker
Arka planda iş yapan süreç. Batch'te birden fazla worker paralel çalışabilir. Stream'de consumer worker olarak da adlandırılır.
