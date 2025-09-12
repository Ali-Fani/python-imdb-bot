"""
Production-ready logging configuration for Python IMDB Bot
Provides structured logging with JSON output and proper log levels
"""

import sys
import logging
import structlog
from pathlib import Path
from loguru import logger
from .models import Settings

settings = Settings()

def setup_logging():
    """Configure structured logging for production use"""

    # Remove default handlers
    logging.getLogger().handlers.clear()

    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure loguru for human-readable console output
    logger.remove()  # Remove default handler

    # Console handler with colors for development
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL.upper(),
        colorize=True,
    )

    # File handler for production logs
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    # Discord.py specific logging
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)

    # Supabase specific logging
    supabase_logger = logging.getLogger('supabase')
    supabase_logger.setLevel(logging.WARNING)

    # HTTP request logging
    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.WARNING)

    logger.info("Logging system initialized", level=settings.LOG_LEVEL, log_file=str(log_file))


def get_logger(name: str):
    """Get a configured logger instance"""
    return structlog.get_logger(name)


# Global logger instance
log = get_logger(__name__)