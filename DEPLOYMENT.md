# 🚀 Production Deployment Guide

This guide covers deploying the enhanced Python IMDB Bot to production environments using Docker and modern best practices.

## 📋 Prerequisites

- Docker and Docker Compose
- Supabase account and project
- Discord Bot Token with proper permissions

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discord Bot   │───▶│   Supabase DB   │───▶│   Movie Data    │
│                 │    │   (PostgreSQL)  │    │   (OMDB API)    │
│ • Reaction      │    │                 │    │                 │
│   Handling      │    │ • Ratings       │    │ • Movie Info    │
│ • Embed Updates │    │ • Movies        │    │ • Posters       │
│ • Health Checks │    │ • Settings      │    │ • Cast/Plot     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Health/Metrics │
│    Endpoints    │
│                 │
│ • /health       │
│ • /ready        │
│ • /metrics      │
└─────────────────┘
```

## 🐳 Docker Deployment

### 1. Environment Setup

Create your `.env` file:

```bash
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Application Settings
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Optional: OMDB API Key (if using OMDB)
OMDB_API_KEY=your_omdb_api_key
```

### 2. Database Setup

```bash
# Apply database migrations
npx supabase db push

# Verify migrations were applied
npx supabase db diff
```

### 3. Docker Compose Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  imdb-bot:
    build: .
    env_file: .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 4. Build and Run

```bash
# Build the production image
docker-compose build

# Start the bot
docker-compose up -d

# Check logs
docker-compose logs -f imdb-bot

# Check health
curl http://localhost:8080/health
```

## 📊 Health Checks & Monitoring

### Health Endpoints

The bot exposes three health check endpoints:

```bash
# Basic health check
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": 3600}

# Readiness check (includes DB connectivity)
GET /ready
Response: {"status": "ready", "database": "connected", "timestamp": "..."}

# Metrics endpoint
GET /metrics
Response: {
    "guilds_configured": 5,
    "movies_tracked": 120,
    "ratings_total": 450,
    "timestamp": "..."
}
```

### Docker Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | ✅ | - | Discord bot token |
| `SUPABASE_URL` | ✅ | - | Supabase project URL |
| `SUPABASE_KEY` | ✅ | - | Supabase anon key |
| `LOG_LEVEL` | ❌ | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | ❌ | logs/bot.log | Log file path |
| `OMDB_API_KEY` | ❌ | - | OMDB API key for movie data |

### Discord Bot Permissions

Required Discord permissions:
- ✅ **Read Messages**
- ✅ **Send Messages**
- ✅ **Read Message History**
- ✅ **Add Reactions**
- ✅ **Manage Messages** (to remove invalid reactions)
- ✅ **Use Slash Commands**

## 📈 Scaling & Performance

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

### Caching Strategy

- **In-memory cache**: 5-minute TTL for rating statistics
- **Database indexes**: Optimized queries for high traffic
- **Connection pooling**: Efficient Supabase connections

### High Availability

```yaml
# Multiple instances with load balancer
services:
  imdb-bot-1:
    # ... config
  imdb-bot-2:
    # ... config

  load-balancer:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

## 🛠️ Troubleshooting

### Common Issues

#### Bot Not Starting
```bash
# Check logs
docker-compose logs imdb-bot

# Check environment variables
docker-compose exec imdb-bot env

# Manual health check
docker-compose exec imdb-bot curl http://localhost:8080/health
```

#### Database Connection Issues
```bash
# Test Supabase connection
docker-compose exec imdb-bot python -c "
from src.python_imdb_bot.utils import supabase
result = supabase.table('settings').select('*').limit(1).execute()
print('Connection successful' if result.data else 'Connection failed')
"
```

#### Reaction Events Not Working
```bash
# Check Discord intents
# 1. Go to Discord Developer Portal
# 2. Bot settings → Privileged Gateway Intents
# 3. Enable: Message Content Intent, Server Members Intent

# Restart bot after changing intents
docker-compose restart imdb-bot
```

### Log Analysis

```bash
# View recent logs
docker-compose logs --tail=100 imdb-bot

# Follow logs in real-time
docker-compose logs -f imdb-bot

# Search for specific errors
docker-compose logs imdb-bot | grep ERROR
```

## 🔄 Updates & Maintenance

### Zero-Downtime Updates

```bash
# Build new image
docker-compose build

# Rolling update (if running multiple instances)
docker-compose up -d --scale imdb-bot=2
docker-compose up -d --scale imdb-bot=1

# Or simple update
docker-compose up -d
```

### Database Migrations

```bash
# Apply new migrations
npx supabase migration new add_new_feature
# Edit the migration file
npx supabase db push

# Update bot with new schema
docker-compose build --no-cache
docker-compose up -d
```

## 📊 Monitoring & Metrics

### Application Metrics

```bash
# Get current stats
curl http://localhost:8080/metrics

# Response:
{
    "guilds_configured": 5,
    "movies_tracked": 120,
    "ratings_total": 450,
    "timestamp": "2025-01-12T08:00:00Z"
}
```

### Log Aggregation

```yaml
# Example: Send logs to external service
logging:
  driver: "fluentd"
  options:
    fluentd-address: "localhost:24224"
    tag: "imdb-bot"
```

## 🔐 Security Best Practices

### Docker Security

```yaml
services:
  imdb-bot:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    user: botuser
```

### Secret Management

```yaml
# Use Docker secrets instead of .env for sensitive data
secrets:
  discord_token:
    file: ./secrets/discord_token.txt
  supabase_key:
    file: ./secrets/supabase_key.txt
```

## 🚀 Advanced Deployment

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imdb-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: imdb-bot
  template:
    metadata:
      labels:
        app: imdb-bot
    spec:
      containers:
      - name: imdb-bot
        image: your-registry/imdb-bot:latest
        ports:
        - containerPort: 8080
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: imdb-bot-secrets
              key: discord-token
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy IMDB Bot
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker image
      run: |
        docker build -t your-registry/imdb-bot:${{ github.sha }} .
        docker push your-registry/imdb-bot:${{ github.sha }}
    - name: Deploy to production
      run: |
        kubectl set image deployment/imdb-bot imdb-bot=your-registry/imdb-bot:${{ github.sha }}
```

This deployment setup provides a production-ready, scalable, and maintainable infrastructure for your enhanced IMDB bot with comprehensive monitoring, health checks, and best practices for containerized deployments.