FROM python:3.11-slim

WORKDIR /app

COPY requirements-ingestion.txt .

RUN pip install --no-cache-dir -r requirements-ingestion.txt

COPY src/ingestion/ ./src/ingestion/
COPY data/raw/ ./data/raw/

CMD ["python", "src/ingestion/load_raw.py"]