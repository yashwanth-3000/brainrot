FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY brainrot_backend ./brainrot_backend

RUN uv sync --locked --no-dev --no-editable

COPY scripts ./scripts
COPY sql ./sql
COPY supabase ./supabase

CMD ["uv", "run", "brainrot-backend"]
