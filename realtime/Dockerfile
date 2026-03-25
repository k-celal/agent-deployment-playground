FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY realtime/ ./realtime/

EXPOSE 8000

CMD ["uvicorn", "realtime.app.api:app", "--host", "0.0.0.0", "--port", "8000"]
