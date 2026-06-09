# Multi-stage Dockerfile for production-ready AI Knowledge Assistant API

# ================================
# Stage 1: Builder
# ================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies needed for some packages (e.g. asyncpg, psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install to a virtual env location
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ================================
# Stage 2: Runtime
# ================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime shared libraries only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy full application source
COPY . .

# Create a non-root user and set permissions
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default startup command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
