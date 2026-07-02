# ------------------------------- Builder Stage ------------------------------ #
FROM python:3.14-bookworm AS builder

# Install uv — statically linked binary, no apt dependencies needed
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install deps from lockfile (cache uv downloads for faster rebuilds).
# This is a flat Shiny app, so only install dependencies, not a package.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


## ------------------------------ Production Stage ---------------------------- ##
FROM python:3.14-slim-bookworm AS production

WORKDIR /app

# Install Chromium for kaleido PNG export (sandbox disabled by default in choreographer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Non-root runtime user (UID 1000, matching Hugging Face Spaces' expected user).
RUN useradd --create-home --uid 1000 appuser

# Environment set-up
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy only what the app needs at runtime
COPY --chown=appuser:appuser app.py ./app.py
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser md_files ./md_files
COPY --chown=appuser:appuser data ./data
COPY --chown=appuser:appuser logos ./logos
COPY --chown=appuser:appuser _brand.yml ./_brand.yml
COPY --chown=appuser:appuser README.md ./README.md

USER appuser

# HF Spaces ignores health checks, but this matters if deployed elsewhere (Cloud Run, ECS, etc.)
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860')"

# Requirement for deployment at hf
EXPOSE 7860
CMD ["shiny", "run", "app.py", "--host", "0.0.0.0", "--port", "7860"]
