FROM python:3.11-slim
WORKDIR /app
COPY requirements-scoring.txt .
RUN pip install --no-cache-dir -r requirements-scoring.txt
COPY src/scoring/ ./src/scoring/
COPY src/blocking/ ./src/blocking/
COPY src/matching/ ./src/matching/
CMD ["python", "src/scoring/run_features.py"]