FROM python:3.11-slim
WORKDIR /app
COPY requirements-cleaning.txt .
RUN pip install --no-cache-dir -r requirements-cleaning.txt
COPY src/cleaning/ ./src/cleaning/
CMD ["python","src/cleaning/run_cleaning.py"]
