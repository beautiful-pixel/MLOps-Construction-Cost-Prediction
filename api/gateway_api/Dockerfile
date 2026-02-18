FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/gateway_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/gateway_api/ .

EXPOSE 8100

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
