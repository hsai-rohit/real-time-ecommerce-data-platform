FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion/ ingestion/
COPY validation/ validation/
COPY scripts/ scripts/

CMD ["python", "scripts/run_ingestion.py"]
