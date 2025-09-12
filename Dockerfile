# ================================
# Production-ready Dockerfile for Python IMDB Bot
# ================================

# ================================
# Builder Stage - Dependencies
# ================================
FROM ghcr.io/astral-sh/uv:latest AS builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set up Python virtual environment
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN uv venv /opt/venv

# Make sure we use venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Python project files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-install-project --no-dev

# ================================
# Runtime Stage - Production
# ================================
FROM python:3.12-slim AS runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    # Required for HTTP requests and SSL
    ca-certificates \
    # Required for timezone handling
    tzdata \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid botuser --shell /bin/bash --create-home botuser

# Copy virtual environment from builder
COPY --from=builder --chown=botuser:botuser /opt/venv /opt/venv

# Make sure we use venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=botuser:botuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from src.python_imdb_bot.rewrite import bot; print('Bot is responsive')" || exit 1

# Set Python optimization flags for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1

# Copy and set entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Health check port
EXPOSE 8080

# Set entrypoint and default command
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "src.python_imdb_bot.rewrite"]

# ================================
# Alternative: Development Stage
# ================================
FROM runtime AS development

# Switch back to root for development
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to botuser
USER botuser

# Override command for development
CMD ["uv", "run", "python", "-m", "src.python_imdb_bot.rewrite"]

# ================================
# Labels for metadata
# ================================
LABEL org.opencontainers.image.title="Python IMDB Bot" \
      org.opencontainers.image.description="Production-ready Discord IMDB bot with reaction-based ratings" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="Ali Fani <alifani1377@gmail.com>" \
      org.opencontainers.image.source="https://github.com/alifani1377/python-imdb-bot"