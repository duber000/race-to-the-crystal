# Race to the Crystal - Unified Server Dockerfile
# Supports both desktop clients (TCP) and web clients (HTTP/WebSocket/Mercure)

FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_VERSION=0.4.0 \
    # Default server ports
    TCP_PORT=8888 \
    HTTP_PORT=8080 \
    # Mercure configuration (override these at runtime)
    MERCURE_HUB_URL=http://localhost:3000/.well-known/mercure \
    MERCURE_PUBLISHER_JWT="" \
    MERCURE_TOPIC_PREFIX=https://api.game.com/game

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Copy source code
COPY game/ game/
COPY client/ client/
COPY shared/ shared/
COPY server/ server/
COPY network/ network/
COPY web_server/ web_server/
COPY docs/ docs/

# Install Python dependencies
RUN uv sync --frozen

# Expose ports
# 8888: TCP port for desktop clients
# 8080: HTTP/WebSocket port for web clients
EXPOSE 8888 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${HTTP_PORT}/ || exit 1

# Default command: run unified server
CMD ["uv", "run", "race-server", "--unified", "--host", "0.0.0.0", "--port", "8888", "--http-port", "8080"]
