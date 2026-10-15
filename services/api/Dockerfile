# Stage 1 — build the Svelte frontend (svelte.config.js writes to ../services/api/static)
FROM node:22-alpine AS frontend

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

# Stage 2 — API runtime
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY contracts ./contracts
COPY services/api ./services/api
COPY --from=frontend /build/services/api/static ./services/api/static

RUN pip install --no-cache-dir .

ENV APP_ROOT=/app
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "services.api.main"]
