FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*  


WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PORT=8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
