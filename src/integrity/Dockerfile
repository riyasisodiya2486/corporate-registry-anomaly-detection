FROM python:3.11-slim
WORKDIR /app
COPY requirements-integrity.txt .
RUN pip install --no-cache-dir -r requirements-integrity.txt
COPY src/integrity/ ./src/integrity/
CMD ["python", "src/integrity/log_real_flags.py"]