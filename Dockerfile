FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential nano \
    && rm -rf /var/lib/apt/lists/*

RUN echo "alias ll='ls -alH'" >> /root/.bashrc

COPY requirements.txt .
COPY src ./src
COPY tests ./tests
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN pip install --no-cache-dir -r requirements.txt
