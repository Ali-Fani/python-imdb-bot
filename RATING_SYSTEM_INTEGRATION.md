# Enhanced IMDB Bot Rating System - Integration Guide

## Overview

This document provides comprehensive integration examples and implementation details for the enhanced multi-user rating system that uses emoji reactions for movie ratings.

## 🎯 System Features

- **Multi-User Ratings**: Collect ratings via digit emoji reactions (1️⃣-9️⃣, 🔟 for 10)
- **Real-time Averaging**: Dynamic calculation and display of community ratings
- **Duplicate Prevention**: Users can only rate each movie once
- **Scalable Architecture**: Designed for high-traffic scenarios
- **Cross-Platform**: Examples for Discord and Slack integration
- **1-10 Rating Scale**: Industry standard rating system

## 🏗️ Database Schema

### New Ratings Table

```sql
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    imdb_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one rating per user per movie per channel
    UNIQUE(user_id, imdb_id, channel_id, guild_id)
);

-- Performance indexes
CREATE INDEX idx_ratings_user_id ON ratings(user_id);
CREATE INDEX idx_ratings_imdb_id ON ratings(imdb_id);
CREATE INDEX idx_ratings_channel_id ON ratings(channel_id);
CREATE INDEX idx_ratings_guild_id ON ratings(guild_id);
CREATE INDEX idx_ratings_movie_channel ON ratings(imdb_id, channel_id, guild_id);
```

## 🔧 Core Functions

### Rating Validation & Conversion

```python
DIGIT_EMOJIS = {
    '1️⃣': 1, '2️⃣': 2, '3️⃣': 3, '4️⃣': 4,
    '5️⃣': 5, '6️⃣': 6, '7️⃣': 7, '8️⃣': 8, '9️⃣': 9,
    '🔟': 10  # Special case for 10
}

def is_valid_rating_emoji(emoji: str) -> bool:
    """Validate digit emoji for rating"""
    return emoji in DIGIT_EMOJIS

def emoji_to_rating(emoji: str) -> int | None:
    """Convert emoji to rating value"""
    return DIGIT_EMOJIS.get(emoji)

def has_user_rated(user_id: int, imdb_id: str, channel_id: int, guild_id: int) -> bool:
    """Check if user already rated this movie"""
    # Database query implementation
    pass
```

### Rating Statistics

```python
def get_movie_rating_stats(imdb_id: str, channel_id: int, guild_id: int) -> dict:
    """Calculate average rating and vote count"""
    # Returns: {"average": 7.5, "count": 12, "ratings": [8,7,6,8,9,...]}
    pass

def format_rating_display(average: float, count: int) -> str:
    """Format rating for display"""
    if count == 0:
        return "⭐ Not rated yet"
    elif count == 1:
        return f"⭐ {average} (1 vote)"
    else:
        return f"⭐ {average} ({count} votes)"
```

## 🤖 Discord Integration

### Reaction Event Handlers

```python
@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    """Handle rating reactions on movie embeds"""

    # Ignore bot reactions
    if user.bot:
        return

    # Validate reaction is on movie message
    movie_data = get_movie_from_message_id(reaction.message.id)
    if not movie_data:
        return

    # Check emoji validity
    if not is_valid_rating_emoji(str(reaction.emoji)):
        await handle_invalid_reaction(reaction, user, "Use digit emojis (0️⃣-9️⃣) to rate!")
        return

    # Prevent duplicate ratings
    if has_user_rated(user.id, movie_data["imdb_id"], reaction.message.channel.id, reaction.message.guild.id):
        await handle_duplicate_rating(reaction, user)
        return

    # Save rating
    rating_value = emoji_to_rating(str(reaction.emoji))
    success = add_or_update_rating(user.id, movie_data["imdb_id"], rating_value, reaction.message.channel.id, reaction.message.guild.id)

    if success:
        # Update embed with new stats
        await update_movie_embed(reaction.message, movie_data["imdb_id"])
    else:
        await handle_rating_save_error(reaction, user)

@bot.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):
    """Handle rating removal"""

    movie_data = get_movie_from_message_id(reaction.message.id)
    if not movie_data or not is_valid_rating_emoji(str(reaction.emoji)):
        return

    success = remove_user_rating(user.id, movie_data["imdb_id"], reaction.message.channel.id, reaction.message.guild.id)
    if success:
        await update_movie_embed(reaction.message, movie_data["imdb_id"])
```

### Error Handling

```python
async def handle_invalid_reaction(reaction, user, message):
    """Handle invalid reactions"""
    try:
        await reaction.remove(user)
        warning = await reaction.message.channel.send(f"{user.mention}, {message}")
        await warning.delete(delay=5)
    except discord.Forbidden:
        # Bot lacks permissions
        logger.warning("Cannot remove reaction: insufficient permissions")

async def handle_duplicate_rating(reaction, user):
    """Handle duplicate rating attempts"""
    await reaction.remove(user)
    warning = await reaction.message.channel.send(
        f"{user.mention}, you can only rate this movie once! Remove your existing rating first."
    )
    await warning.delete(delay=10)
```

## 📱 Slack Integration

### Bolt Framework Implementation

```python
from slack_bolt import App

class SlackMovieBot:
    def __init__(self, app_token, bot_token):
        self.app = App(token=bot_token)
        self.setup_reaction_handlers()

    def setup_reaction_handlers(self):
        @self.app.event("reaction_added")
        def handle_reaction_added(event, say, logger):
            """Handle rating reactions in Slack"""

            reaction = event['reaction']
            user_id = event['user']
            channel_id = event['item']['channel']
            timestamp = event['item']['ts']

            # Validate reaction is on movie message
            movie_data = self.get_movie_from_timestamp(channel_id, timestamp)
            if not movie_data:
                return

            # Check emoji validity (Slack uses different emoji names)
            if not self.is_valid_slack_emoji(reaction):
                self.handle_invalid_reaction(event, "Use number emojis (one, two, etc.) to rate!")
                return

            # Prevent duplicates
            if self.has_user_rated(user_id, movie_data['imdb_id'], channel_id):
                self.handle_invalid_reaction(event, "You can only rate once per movie!")
                return

            # Save rating
            rating_value = self.slack_emoji_to_rating(reaction)
            success = self.save_rating(user_id, movie_data['imdb_id'], rating_value, channel_id)

            if success:
                self.update_message_rating(channel_id, timestamp, movie_data['imdb_id'])
                self.send_ephemeral_message(user_id, channel_id, f"Rating saved: {rating_value}/10")

        @self.app.event("reaction_removed")
        def handle_reaction_removed(event, say, logger):
            """Handle rating removal in Slack"""

            reaction = event['reaction']
            user_id = event['user']
            channel_id = event['item']['channel']
            timestamp = event['item']['ts']

            movie_data = self.get_movie_from_timestamp(channel_id, timestamp)
            if not movie_data or not self.is_valid_slack_emoji(reaction):
                return

            success = self.remove_rating(user_id, movie_data['imdb_id'], channel_id)
            if success:
                self.update_message_rating(channel_id, timestamp, movie_data['imdb_id'])
```

### Slack Emoji Mapping

```python
SLACK_EMOJI_MAPPING = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'keycap_ten': 10,
    # Add more mappings as needed
}
```

## ⚡ Scalability Features

### Caching Layer

```python
class RatingCache:
    """Redis/in-memory caching for high-traffic scenarios"""

    def __init__(self, redis_client=None, ttl_seconds=300):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.local_cache = {}

    async def get_rating_stats(self, imdb_id: str, channel_id: int, guild_id: int) -> dict:
        """Get cached rating statistics"""
        cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"

        # Try Redis first, then local cache, then database
        cached_data = await self._get_cache(cache_key)
        if cached_data:
            return cached_data

        # Cache miss - fetch from database
        stats = await self._fetch_from_database(imdb_id, channel_id, guild_id)
        await self._set_cache(cache_key, stats)
        return stats

    async def invalidate_rating_cache(self, imdb_id: str, channel_id: int, guild_id: int):
        """Invalidate cache when ratings change"""
        cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
        await self._delete_cache(cache_key)
```

### Database Optimization

- **Indexes**: Optimized for common query patterns
- **Connection Pooling**: Reuse database connections
- **Batch Operations**: Group multiple rating updates
- **Read Replicas**: Separate read/write databases for high traffic

## 🔒 Security & Permissions

### Rate Limiting

```python
class RateLimiter:
    """Prevent spam and abuse"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(self, user_id: int, action: str) -> bool:
        """Check if user is within rate limits"""
        key = f"rate_limit:{user_id}:{action}"
        count = await self.redis.incr(key)

        if count == 1:
            await self.redis.expire(key, 60)  # 1 minute window

        return count <= 10  # Max 10 actions per minute
```

### Input Validation

```python
def validate_rating_input(rating: int) -> bool:
    """Validate rating value"""
    return isinstance(rating, int) and 0 <= rating <= 10

def sanitize_emoji_input(emoji: str) -> str:
    """Sanitize emoji input to prevent injection"""
    return emoji.strip()[:50]  # Max length limit
```

## 📊 Monitoring & Analytics

### Metrics Collection

```python
class RatingMetrics:
    """Collect usage metrics"""

    def __init__(self, metrics_client):
        self.client = metrics_client

    async def record_rating_event(self, event_type: str, data: dict):
        """Record rating events for analytics"""
        await self.client.increment(f"rating.{event_type}", data)

    async def get_popular_movies(self, limit: int = 10) -> list:
        """Get most rated movies"""
        # Implementation for analytics queries
        pass
```

## 🚀 Deployment Considerations

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/imdb_bot

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Platform tokens
DISCORD_TOKEN=your_discord_bot_token
SLACK_APP_TOKEN=your_slack_app_token
SLACK_BOT_TOKEN=your_slack_bot_token

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=10

# Cache settings
CACHE_TTL_SECONDS=300
```

### Health Checks

```python
async def health_check():
    """System health monitoring"""
    checks = {
        'database': await check_database_connection(),
        'cache': await check_cache_connection(),
        'discord_api': await check_discord_api(),
        'slack_api': await check_slack_api()
    }
    return all(checks.values()), checks
```

## 🔄 Migration Strategy

### Database Migration Steps

1. **Backup existing data**
2. **Create new ratings table**
3. **Migrate existing single ratings (if any)**
4. **Update application code**
5. **Deploy with feature flag**
6. **Monitor and rollback if needed**

### Zero-Downtime Deployment

```python
# Feature flag implementation
class FeatureFlags:
    COMMUNITY_RATING_ENABLED = os.getenv('COMMUNITY_RATING_ENABLED', 'false').lower() == 'true'

# Conditional logic in handlers
if FeatureFlags.COMMUNITY_RATING_ENABLED:
    await handle_community_rating(reaction, user)
else:
    await handle_legacy_rating(reaction, user)
```

## 📚 Usage Examples

### Basic Rating Flow

1. User posts IMDB URL in designated channel
2. Bot fetches movie data and creates embed
3. Users react with digit emojis (0️⃣-9️⃣)
4. Bot validates reaction and saves rating
5. Embed updates with new average rating
6. Users can remove reactions to change rating

### Advanced Features

- **Bulk Operations**: Handle multiple reactions simultaneously
- **Webhook Integration**: Send rating updates to external systems
- **Export Functionality**: Export rating data for analysis
- **Moderation Tools**: Admin commands to manage ratings

This enhanced rating system provides a robust, scalable solution for community-driven movie ratings with comprehensive error handling and cross-platform support.