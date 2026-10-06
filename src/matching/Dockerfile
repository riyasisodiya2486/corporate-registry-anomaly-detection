FROM python:3.11-slim

WORKDIR /app

COPY requirements-matching.txt .
RUN pip install --no-cache-dir -r requirements-matching.txt

COPY src/matching/ ./src/matching/
COPY src/blocking/ ./src/blocking/

CMD ["python", "src/matching/run_matching.py"]