#!/usr/bin/env python3
"""
Main entry point for Python IMDB Bot
Adapted from Discord_Watch project structure for Coolify deployment compatibility
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports (container-compatible relative path handling)
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import bot modules
from python_imdb_bot.logging_config import setup_logging, get_logger
from python_imdb_bot.utils import validate_database_schema
from python_imdb_bot.health import start_health_server
from python_imdb_bot.rewrite import run_bot, main as bot_main
from python_imdb_bot.models import Settings

# Initialize Sentry as early as possible
settings = Settings()
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        # Enable performance monitoring
        traces_sample_rate=1.0,
        # Enable profiling for detailed performance insights
        profiles_sample_rate=1.0,
        integrations=[
            AsyncioIntegration(),
            HttpxIntegration(),
        ],
        # Capture all errors
        send_default_pii=True,
        # Environment info
        environment="production",
        release="1.0.0",
    )
    print("Sentry initialized successfully")
else:
    print("Sentry DSN not configured")

async def main():
    """Main entry point"""
    log = get_logger("main")

    # Set up logging
    setup_logging()
    log.info("Starting Python IMDB Bot")

    # Validate database schema
    try:
        validate_database_schema()
        log.info("Database schema validation passed")
    except Exception as e:
        log.error("Database schema validation failed", error=str(e))
        sys.exit(1)

    # Start health check server and bot concurrently
    try:
        # Start health check server
        health_task = asyncio.create_task(start_health_server())

        # Start Discord bot
        bot_task = asyncio.create_task(run_bot())

        # Wait for both to complete (or fail)
        await asyncio.gather(health_task, bot_task)

    except KeyboardInterrupt:
        log.info("Shutdown requested by user")
    except Exception as e:
        log.error("Application error", error=str(e))
        raise

if __name__ == "__main__":
    # Run the async application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        get_logger("main").info("Application shutdown complete")
    except Exception as e:
        get_logger("main").error("Application crashed", error=str(e))
        sys.exit(1)