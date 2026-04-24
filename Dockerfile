# ─────────────────────────────────────────────────────────────
# Stage 1: Build Vue frontend
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Stage 2: FastAPI application
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy compiled Vue SPA from Stage 1
COPY --from=frontend-builder /frontend/dist ./static

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
