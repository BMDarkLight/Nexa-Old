# -------- Stage 1: Build frontend --------
FROM node:20-slim AS frontend-builder

WORKDIR /app/web

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

COPY --from=frontend-builder /app/web/.next ./.next
COPY --from=frontend-builder /app/web/public ./public
COPY --from=frontend-builder /app/web/package.json ./package.json
COPY --from=frontend-builder /app/web/node_modules ./node_modules

EXPOSE ${API_PORT}
EXPOSE ${UI_PORT}

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port $API_PORT & node node_modules/next/dist/bin/next start -p $UI_PORT"]