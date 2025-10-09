# Health Check API Documentation

This document describes the HTTP health check endpoints exposed by the Python IMDB Bot for monitoring and load balancing purposes.

## Overview

The bot runs a lightweight HTTP server on port 8080 that provides three health check endpoints:

- `/health` - Basic health check
- `/ready` - Readiness check with database connectivity
- `/metrics` - Application metrics

## Endpoints

### GET /health

Basic health check endpoint that verifies the bot is running.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-12T08:00:00.123456",
  "uptime_seconds": 3600.5
}
```

**Response Fields:**
- `status` (string): Always "healthy" if the endpoint responds
- `timestamp` (string): ISO 8601 formatted timestamp
- `uptime_seconds` (number): Seconds since the bot started

### GET /ready

Readiness check that verifies both bot health and database connectivity.

**Response (200 OK):**
```json
{
  "status": "ready",
  "database": "connected",
  "timestamp": "2025-01-12T08:00:00.123456"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "not ready",
  "database": "disconnected",
  "error": "Connection timeout",
  "timestamp": "2025-01-12T08:00:00.123456"
}
```

**Response Fields:**
- `status` (string): "ready" or "not ready"
- `database` (string): "connected" or "disconnected"
- `timestamp` (string): ISO 8601 formatted timestamp
- `error` (string): Error message if database connection fails (only in error responses)

### GET /metrics

Provides basic application metrics for monitoring.

**Response (200 OK):**
```json
{
  "guilds_configured": 5,
  "movies_tracked": 120,
  "ratings_total": 450,
  "timestamp": "2025-01-12T08:00:00.123456"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Failed to fetch metrics",
  "details": "Database connection error"
}
```

**Response Fields:**
- `guilds_configured` (integer): Number of Discord guilds with configured channels
- `movies_tracked` (integer): Total number of movies stored in database
- `ratings_total` (integer): Total number of ratings across all movies
- `timestamp` (string): ISO 8601 formatted timestamp

## Usage Examples

### Docker Health Check

```yaml
# docker-compose.yml
services:
  imdb-bot:
    # ... other config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### Load Balancer Configuration

```nginx
# nginx.conf
upstream imdb_bot {
    server bot1:8080;
    server bot2:8080;
}

server {
    listen 80;
    location /health {
        proxy_pass http://imdb_bot/health;
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
}
```

### Monitoring Integration

```python
# Python monitoring script
import requests
import time

def check_health():
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_metrics():
    try:
        response = requests.get("http://localhost:8080/metrics", timeout=5)
        return response.json()
    except:
        return None
```

## Error Codes

- `200 OK`: Endpoint is healthy and responding
- `503 Service Unavailable`: Readiness check failed (database issues)
- `500 Internal Server Error`: Metrics endpoint failed to fetch data

## Security Considerations

- Health endpoints are unauthenticated and should only be exposed internally
- Use firewall rules or reverse proxy to restrict access to monitoring systems
- Consider implementing API keys for production environments

## Performance Notes

- Health checks are lightweight and designed for frequent polling
- Database queries are optimized with `LIMIT 1` to minimize load
- Endpoints use connection pooling to avoid connection overhead
- Metrics endpoint may have slight performance impact on busy systems