FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install Node.js and npm
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy dependency files and workspace structure for better layer caching
COPY uv.lock pyproject.toml ./
COPY packages/ packages/

# Install dependencies in a separate layer for better caching
# Use cache mount and install dependencies without the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    uv sync --locked --no-install-package reversible-image-modification-system

COPY . .

# Build React app
RUN cd src/web_interface && npm ci && npm run build

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 \
    uv sync --locked

RUN mkdir -p \
    /app/storage/databases \
    /app/storage/images/original \
    /app/storage/images/modified \
    /app/storage/temp \
    /app/.cache/uv \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app/storage

USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/app/.cache/uv

# Health check - will be overridden by docker-compose for specific ports
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# This one is a default - will be overridden by docker-compose for specific services
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000"]
