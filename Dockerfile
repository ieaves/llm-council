FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    docker-cli \
 && rm -rf /var/lib/apt/lists/*

# Install uv once; reuse across builds
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend ./backend

ENV DATA_DIR=/app/data/conversations

EXPOSE 8001
CMD ["uv", "run", "python", "-m", "backend.main"]
