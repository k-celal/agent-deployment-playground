.PHONY: help install test run-batch run-stream run-realtime run-edge run-all clean lint

help: ## Bu yardım mesajını göster
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Bağımlılıkları yükle
	pip install -r requirements.txt

test: ## Tüm testleri çalıştır
	python -m pytest batch/tests/ stream/tests/ realtime/tests/ edge/tests/ -v

test-batch: ## Sadece batch testlerini çalıştır
	python -m pytest batch/tests/ -v

test-stream: ## Sadece stream testlerini çalıştır
	python -m pytest stream/tests/ -v

test-realtime: ## Sadece realtime testlerini çalıştır
	python -m pytest realtime/tests/ -v

test-edge: ## Sadece edge testlerini çalıştır
	python -m pytest edge/tests/ -v

run-batch: ## Batch processor'ı çalıştır
	python -m batch.app.processor

run-stream: ## Stream consumer'ı çalıştır
	python -m stream.app.consumer

run-realtime: ## Real-time API sunucusunu başlat (port 8000)
	python -m realtime.app.api

run-edge: ## Edge agent'ı çalıştır
	python -m edge.app.local_agent

run-all: run-batch run-stream run-edge ## Batch, stream ve edge'i sırasıyla çalıştır (realtime ayrı çalıştırılmalı)
	@echo "Batch, Stream ve Edge tamamlandı. Real-time için: make run-realtime"

clean: ## Oluşturulan veri dosyalarını temizle
	rm -rf data/
	rm -rf edge_results/
	rm -f *.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker-build: ## Docker image'larını build et
	docker-compose build

docker-up: ## Docker ile tüm servisleri başlat
	docker-compose up

docker-down: ## Docker servislerini durdur
	docker-compose down
