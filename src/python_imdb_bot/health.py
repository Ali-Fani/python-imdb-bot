"""
Health check endpoints for production monitoring
Provides HTTP endpoints for load balancer health checks
"""

import asyncio
import json
from datetime import datetime
from aiohttp import web
from .utils import supabase
from .logging_config import get_logger

log = get_logger("health")
start_time = datetime.utcnow()

class HealthCheck:
    """Health check handler for the bot"""

    def __init__(self):
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/ready', self.readiness_check)
        self.app.router.add_get('/metrics', self.metrics)

    async def health_check(self, request):
        """Basic health check - returns 200 if bot is running"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - start_time).total_seconds()
        })

    async def readiness_check(self, request):
        """Readiness check - verifies database connectivity"""
        try:
            # Test database connection
            result = supabase.table('settings').select('*').limit(1).execute()

            return web.json_response({
                "status": "ready",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            log.error("Readiness check failed", error=str(e))
            return web.json_response({
                "status": "not ready",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }, status=503)

    async def metrics(self, request):
        """Basic metrics endpoint"""
        try:
            # Get some basic stats
            settings_count = len(supabase.table('settings').select('*').execute().data)
            movies_count = len(supabase.table('movies').select('*').execute().data)
            ratings_count = len(supabase.table('ratings').select('*').execute().data)

            return web.json_response({
                "guilds_configured": settings_count,
                "movies_tracked": movies_count,
                "ratings_total": ratings_count,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            log.error("Metrics check failed", error=str(e))
            return web.json_response({
                "error": "Failed to fetch metrics",
                "details": str(e)
            }, status=500)

    async def start_server(self, host='0.0.0.0', port=8080):
        """Start the health check server"""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        log.info("Health check server started", host=host, port=port)
        return runner

# Global instance
health_check = HealthCheck()

async def start_health_server():
    """Start the health check HTTP server"""
    try:
        await health_check.start_server()
    except Exception as e:
        log.error("Failed to start health check server", error=str(e))