FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ARG VITE_API_BASE_URL=http://localhost:9000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build


FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
COPY cloud-intelligence-mcp/requirements.txt cloud-intelligence-mcp/requirements.txt

RUN pip install --no-cache-dir -r cloud-intelligence-mcp/requirements.txt \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY cloud-intelligence-mcp cloud-intelligence-mcp
COPY --from=frontend-build /app/frontend/dist frontend/dist
COPY docker/app-start.sh docker/app-start.sh

RUN chmod +x docker/app-start.sh

EXPOSE 5174 9000 8001 8000

CMD ["./docker/app-start.sh"]
