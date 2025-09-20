# -------- Stage 1: Build frontend --------
FROM node:20-slim AS frontend-builder
WORKDIR /app/web

ENV NEXT_TELEMETRY_DISABLED=1

COPY ./web/package.json ./web/package-lock.json ./
RUN npm ci

COPY ./web ./
RUN npm run build

# -------- Stage 2: Backend + Frontend Runner --------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV API_PORT=8000
ENV UI_PORT=80

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY ./api ./api

RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

COPY --from=frontend-builder /app/web/public ./public
COPY --from=frontend-builder /app/web/.next/standalone ./
COPY --from=frontend-builder /app/web/.next/static ./.next/static

EXPOSE ${API_PORT}
EXPOSE ${UI_PORT}

RUN apt-get update && apt-get install -y dumb-init && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

CMD ["sh", "-c", "PORT=$UI_PORT node server.js & uvicorn api.main:app --host 0.0.0.0 --port $API_PORT"]