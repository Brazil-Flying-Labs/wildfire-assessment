# ── Stage 1: build ────────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1

# Install build-time dependencies (headers, compilers, dev libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gdal-bin libgdal-dev \
        libpq-dev \
        git && \
    rm -rf /var/lib/apt/lists/*

ENV GDAL_VERSION=3.6.0

COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r /requirements.txt && \
    # Strip tests, type stubs, and bytecode cache (~80 MB)
    find /install -type d -name "tests" -exec rm -rf {} + 2>/dev/null; \
    find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
    find /install -name "*.pyc" -delete 2>/dev/null; \
    true

# ── Stage 2: runtime ─────────────────────────────────────────────
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1

# Runtime-only system libs (no -dev, no build-essential, no headers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gdal-bin libgdal32 \
        libpq5 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Non-root application user (dev override may run as root for hot reload)
RUN useradd --create-home --uid 10001 appuser

COPY api api
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R appuser:appuser /api

WORKDIR /api

USER appuser

EXPOSE 8000

CMD [ "/entrypoint.sh" ]
