FROM python:3.11-slim

WORKDIR /app

COPY requirements-graph.txt .
RUN pip install --no-cache-dir -r requirements-graph.txt

COPY src/graph/ ./src/graph/

CMD ["python", "src/graph/run_clustering.py"]