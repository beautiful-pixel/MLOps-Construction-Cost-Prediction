FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/inference_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/inference_api/main.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
