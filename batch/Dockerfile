FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY batch/ ./batch/
COPY examples/ ./examples/

CMD ["python", "-m", "batch.app.processor"]
