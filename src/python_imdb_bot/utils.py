import time
import logging
import sys
import json
import os
from .models import Settings
import discord
from .models import Media, URLInfo
import aiohttp
from urllib.parse import urlparse, parse_qs
from supabase import create_client, Client
import re
from .models import Settings
import discord
from .models import Media, URLInfo
import aiohttp
from urllib.parse import urlparse, parse_qs
from supabase import create_client, Client

# Redis imports (optional)
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

settings = Settings()  # type: ignore

supabase_url: str = settings.SUPABASE_URL
supabase_key: str = settings.SUPABASE_KEY
supabase: Client = create_client(supabase_url, supabase_key)

# Redis client setup
redis_client = None
if REDIS_AVAILABLE:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    try:
        redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        print(f"Warning: Failed to connect to Redis: {e}")
        redis_client = None


def get_imdb_id(url: str) -> tuple[str, str] | tuple[None, None]:
    """
    Extracts the IMDb ID and rating from the given URL.

    Args:
        url (str): The IMDb URL.

    Returns:
        tuple[str, str] | tuple[None, None]: A tuple containing the IMDb ID and rating if found,
        otherwise a tuple containing None values.

    """
    match = re.search(
        r"^https?://www\.imdb\.com/[Tt]itle[?/][a-zA-Z]+([0-9]+)/?(#(\d.\d?))?", url
    )
    if match:
        return match.group(1), match.group(3)
    return None, None


async def get_imdb_info(imdb_id: str) -> Media | None:
    """
    Retrieves IMDb information for a given IMDb ID, including trailer URL if TMDB is configured.

    Args:
        imdb_id (str): The IMDb ID of the movie or TV show.

    Returns:
        Media | None: An instance of the Media class containing the IMDb information,
                      or None if the IMDb ID is not found.

    """
    async with aiohttp.ClientSession() as session:
        url = f"http://www.omdbapi.com/?apikey={settings.OMDB_API_KEY}&i={imdb_id}"
        async with session.get(url) as response:
            data = await response.json()
            if data.get('Response') == 'True':
                media = Media(**data)

                # Try to get trailer URL from TMDB if API key is configured
                if hasattr(settings, 'TMDB_API_KEY') and settings.TMDB_API_KEY and settings.TMDB_API_KEY != 'your_tmdb_api_key_here':
                    tmdb_id = await get_tmdb_id_from_imdb(imdb_id)
                    if tmdb_id:
                        trailer_url = await get_movie_trailer(tmdb_id)
                        if trailer_url:
                            media.trailer_url = trailer_url

                return media
    return None


async def get_tmdb_id_from_imdb(imdb_id: str) -> str | None:
    """
    Get TMDB ID from IMDb ID using TMDB's find endpoint.

    Args:
        imdb_id (str): The IMDb ID (e.g., 'tt0111161')

    Returns:
        str | None: TMDB movie ID or None if not found
    """
    async with aiohttp.ClientSession() as session:
        url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={settings.TMDB_API_KEY}&external_source=imdb_id"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                movie_results = data.get('movie_results', [])
                if movie_results:
                    return str(movie_results[0]['id'])
    return None


async def get_movie_trailer(tmdb_id: str) -> str | None:
    """
    Get official trailer URL from TMDB videos endpoint.

    Args:
        tmdb_id (str): The TMDB movie ID

    Returns:
        str | None: YouTube trailer URL or None if not found
    """
    async with aiohttp.ClientSession() as session:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos?api_key={settings.TMDB_API_KEY}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                videos = data.get('results', [])

                # Find official trailer
                for video in videos:
                    if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                        key = video.get('key')
                        if key:
                            return f"https://www.youtube.com/watch?v={key}"
    return None
async def parse_message(message: str) -> URLInfo | None:
    # Regular expression to match IMDB URL and ID
    imdb_pattern = r'(https?://(?:www\.)?imdb\.com/title/(tt\d+))'
    
    # Find IMDB URL and ID
    match = re.search(imdb_pattern, message)
    if not match:
        return None
    
    imdb_url, imdb_id = match.groups()
    
    # Parse query parameters
    parsed_url = urlparse(message)
    query_params = parse_qs(parsed_url.query)
    
    # Extract rating and comment (if present)
    rating = query_params.get('rating', [None])[0]
    
    return URLInfo(IMDB_URI=imdb_url, IMDB_ID=imdb_id, USER_RATING=rating)


async def make_embed(media: Media, imdb_url: str, channel_id: int, guild_id: int) -> tuple[discord.Embed, discord.ui.View | None]:
    """
    Creates an embed message with the IMDb information and community ratings.

    Args:
        media (Media): The instance of the Media class containing the IMDb information.
        imdb_url (str): The IMDB URL
        channel_id (int): Discord channel ID for rating context
        guild_id (int): Discord guild ID for rating context

    Returns:
        tuple[discord.Embed, discord.ui.View | None]: An embed message with the IMDb information and optional view with trailer button.

    """
    embed = discord.Embed(
        title=f"{media.Title} ({media.Year})",
        description=media.Plot,
        url=imdb_url,
        color=0x00FF00,
    )
    embed.set_image(url=media.Poster)
    embed.add_field(name="Director", value=media.Director, inline=True)
    embed.add_field(name="Writer", value=media.Writer, inline=True)
    embed.add_field(name="Actors", value=media.Actors, inline=True)
    embed.add_field(name="Rating", value=f"⭐ {media.imdbRating}", inline=True)
    embed.add_field(name="Awards", value=media.Awards, inline=True)
    embed.add_field(name="Genre", value=media.Genre, inline=True)
    embed.add_field(name="Runtime", value=media.Runtime, inline=True)
    embed.add_field(name="Language", value=media.Language, inline=True)
    embed.add_field(name="Country", value=media.Country, inline=True)
    embed.add_field(name="Released", value=media.Released, inline=True)
    embed.add_field(name="IMDb ID", value=media.imdbID, inline=True)

    # Get community rating stats with caching
    rating_stats = await get_movie_rating_stats_cached(media.imdbID, channel_id, guild_id)
    embed.add_field(name="Community Rating", value=format_rating_display(rating_stats["average"], rating_stats["count"]), inline=True)

    # Create view with trailer button if TMDB is configured and trailer is available
    view = None
    if (hasattr(settings, 'TMDB_API_KEY') and
        settings.TMDB_API_KEY and
        settings.TMDB_API_KEY != 'your_tmdb_api_key_here' and
        hasattr(media, 'trailer_url') and
        media.trailer_url):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🎬 Watch Trailer",
            url=media.trailer_url,
            style=discord.ButtonStyle.link
        ))

    return embed, view


def update_media_user_rating(url_info):
    supabase.table("movies").update(
        {
            "user_rating": (
                float(url_info.USER_RATING)
                if url_info.USER_RATING is not None
                else None
            )
        }
    ).eq("imdb_id", url_info.IMDB_ID).execute()


def save_media_metadata(url_info, media_info, sent_message):
    movie_data = {
        "imdb_id": media_info.imdbID,
        "message_id": sent_message.id,
        "channel_id": sent_message.channel.id,
        "guild_id": sent_message.guild.id,
    }

    # Only add trailer_url if TMDB is configured and trailer exists
    if (hasattr(settings, 'TMDB_API_KEY') and
        settings.TMDB_API_KEY and
        settings.TMDB_API_KEY != 'your_tmdb_api_key_here' and
        hasattr(media_info, 'trailer_url') and
        media_info.trailer_url):
        movie_data["trailer_url"] = media_info.trailer_url

    supabase.table("movies").insert(movie_data).execute()

async def find_existing_movie(message, url_info):
    """Check if movie exists and if the Discord message is still available"""
    # First check database
    result = (
        supabase.table("movies")
        .select("*")
        .eq("imdb_id", url_info.IMDB_ID)
        .eq("channel_id", message.channel.id)
        .eq("guild_id", message.guild.id if message.guild else None)
        .limit(1)
        .execute()
    )

    if not result.data:
        return result  # No movie found in database

    movie_data = result.data[0]
    message_id = movie_data.get("message_id")

    if not message_id:
        return result  # No message ID stored, treat as existing

    # Try to fetch the Discord message
    try:
        await message.channel.fetch_message(message_id)
        # Message still exists, so movie already exists
        return result
    except discord.NotFound:
        # Message was deleted, clean up database and allow re-posting
        try:
            supabase.table("movies").delete().eq("message_id", message_id).execute()
            supabase.table("ratings").delete().eq("imdb_id", url_info.IMDB_ID).eq("channel_id", message.channel.id).eq("guild_id", message.guild.id if message.guild else None).execute()
        except Exception:
            pass  # Ignore cleanup errors

        # Return empty result to allow re-posting
        return type('Result', (), {'data': None})()
    except Exception:
        # Other error (permissions, etc.), assume message exists to be safe
        return result
def validate_database_schema():
    """
    Validate that required database tables exist by attempting to query them.

    This function checks for the existence of critical tables by performing a simple
    SELECT query. If any required table is missing, it logs a critical error and
    terminates the application to prevent runtime failures.

    Required tables:
    - movies: Stores movie metadata and Discord message associations
    - settings: Stores guild-specific channel settings

    Returns:
        bool: True if all tables exist and are accessible

    Raises:
        SystemExit: If validation fails, exits with code 1
    """
    required_tables = ['movies', 'settings']

    for table in required_tables:
        try:
            # Attempt a simple query to check table existence and accessibility
            supabase.table(table).select("*").limit(1).execute()
        except Exception as e:
            print(f"CRITICAL: Database schema validation failed: Table '{table}' is missing or inaccessible.")
            print(f"Error: {e}")
            print("Please ensure database migrations have been applied before starting the bot.")
            print("Run 'npx supabase db push' to apply migrations to your remote Supabase project.")
            sys.exit(1)

    print("INFO: Database schema validation passed.")
    return True

def is_valid_rating_emoji(emoji: str) -> bool:
    """
    Check if the emoji is a valid digit emoji for rating (0-9, 🔟 for 10).

    Args:
        emoji (str): The emoji to validate

    Returns:
        bool: True if valid rating emoji, False otherwise
    """
    return emoji in DIGIT_EMOJIS

def emoji_to_rating(emoji: str) -> int | None:
    """
    Convert a digit emoji to its rating value.

    Args:
        emoji (str): The emoji to convert

    Returns:
        int | None: The rating value (0-10) or None if invalid
    """
    return DIGIT_EMOJIS.get(emoji)

def rating_to_emoji(rating: int) -> str | None:
    """
    Convert a rating value to its corresponding emoji.

    Args:
        rating (int): The rating value (0-10)

    Returns:
        str | None: The corresponding emoji or None if invalid
    """
    return EMOJI_TO_DIGIT.get(rating)

def has_user_rated(user_id: int, imdb_id: str, channel_id: int, guild_id: int) -> bool:
    """
    Check if a user has already rated a specific movie.

    Args:
        user_id (int): Discord user ID
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        bool: True if user has already rated, False otherwise
    """
    result = supabase.table("ratings").select("id").eq("user_id", user_id).eq("imdb_id", imdb_id).eq("channel_id", channel_id).eq("guild_id", guild_id).limit(1).execute()
    return len(result.data) > 0

def add_or_update_rating(user_id: int, imdb_id: str, rating: int, channel_id: int, guild_id: int) -> bool:
    """
    Add or update a user's rating for a movie.

    Args:
        user_id (int): Discord user ID
        imdb_id (str): IMDB ID of the movie
        rating (int): Rating value (0-10)
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use upsert to handle both insert and update cases
        supabase.table("ratings").upsert(
            {
                "user_id": user_id,
                "imdb_id": imdb_id,
                "rating": rating,
                "channel_id": channel_id,
                "guild_id": guild_id,
                "updated_at": "NOW()"
            },
            on_conflict="user_id,imdb_id,channel_id,guild_id"
        ).execute()
        return True
    except Exception as e:
        print(f"Error saving rating: {e}")
        return False

def remove_user_rating(user_id: int, imdb_id: str, channel_id: int, guild_id: int) -> bool:
    """
    Remove a user's rating for a movie.

    Args:
        user_id (int): Discord user ID
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase.table("ratings").delete().eq("user_id", user_id).eq("imdb_id", imdb_id).eq("channel_id", channel_id).eq("guild_id", guild_id).execute()
        return True
    except Exception as e:
        print(f"Error removing rating: {e}")
        return False

def get_movie_rating_stats(imdb_id: str, channel_id: int, guild_id: int) -> dict:
    """
    Get rating statistics for a movie.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        dict: Dictionary containing average rating and vote count
    """
    try:
        result = supabase.table("ratings").select("rating").eq("imdb_id", imdb_id).eq("channel_id", channel_id).eq("guild_id", guild_id).execute()

        if not result.data:
            return {"average": 0.0, "count": 0, "ratings": []}

        ratings = [row["rating"] for row in result.data]
        average = sum(ratings) / len(ratings)

        return {
            "average": round(average, 1),
            "count": len(ratings),
            "ratings": ratings
        }
    except Exception as e:
        print(f"Error getting rating stats: {e}")
        return {"average": 0.0, "count": 0, "ratings": []}

def format_rating_display(average: float, count: int) -> str:
    """
    Format the rating display string.

    Args:
        average (float): Average rating
        count (int): Number of votes

    Returns:
        str: Formatted rating string
    """
    if count == 0:
        return "⭐ Not rated yet"
    elif count == 1:
        return f"⭐ {average} (1 vote)"
    else:
        return f"⭐ {average} ({count} votes)"


# Enhanced caching with Redis support
_CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # Default 5 minutes

async def get_cached_rating_stats(imdb_id: str, channel_id: int, guild_id: int) -> dict | None:
    """
    Get cached rating statistics from Redis if available and not expired.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        dict | None: Cached rating stats or None if not cached/expired
    """
    if not redis_client:
        return None

    cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"Redis cache error: {e}")

    return None

async def set_cached_rating_stats(imdb_id: str, channel_id: int, guild_id: int, stats: dict):
    """
    Cache rating statistics in Redis with TTL.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID
        stats (dict): Rating statistics to cache
    """
    if not redis_client:
        return

    cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
    try:
        await redis_client.setex(cache_key, _CACHE_TTL, json.dumps(stats))
    except Exception as e:
        print(f"Redis cache set error: {e}")

async def invalidate_rating_cache(imdb_id: str, channel_id: int, guild_id: int):
    """
    Remove rating statistics from Redis cache.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID
    """
    if not redis_client:
        return

    cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
    try:
        await redis_client.delete(cache_key)
    except Exception as e:
        print(f"Redis cache delete error: {e}")

async def get_movie_rating_stats_cached(imdb_id: str, channel_id: int, guild_id: int) -> dict:
    """
    Get rating statistics with Redis caching support.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        dict: Rating statistics (average, count, ratings)
    """
    # Try Redis cache first
    cached_stats = await get_cached_rating_stats(imdb_id, channel_id, guild_id)
    if cached_stats:
        return cached_stats

    # Cache miss - fetch from database
    stats = get_movie_rating_stats(imdb_id, channel_id, guild_id)

    # Cache the result in Redis
    await set_cached_rating_stats(imdb_id, channel_id, guild_id, stats)

    return stats

# Fallback to in-memory cache if Redis is not available
_rating_cache = {}

def get_cached_rating_stats_sync(imdb_id: str, channel_id: int, guild_id: int) -> dict | None:
    """Synchronous fallback for in-memory cache"""
    cache_key = f"{imdb_id}:{channel_id}:{guild_id}"
    if cache_key in _rating_cache:
        cached_data, timestamp = _rating_cache[cache_key]
        if time.time() - timestamp < _CACHE_TTL:
            return cached_data
        else:
            del _rating_cache[cache_key]
    return None

def set_cached_rating_stats_sync(imdb_id: str, channel_id: int, guild_id: int, stats: dict):
    """Synchronous fallback for in-memory cache"""
    cache_key = f"{imdb_id}:{channel_id}:{guild_id}"
    _rating_cache[cache_key] = (stats, time.time())

def invalidate_rating_cache_sync(imdb_id: str, channel_id: int, guild_id: int):
    """Synchronous fallback for in-memory cache"""
    cache_key = f"{imdb_id}:{channel_id}:{guild_id}"
    if cache_key in _rating_cache:
        del _rating_cache[cache_key]

def get_movie_from_message_id(message_id: int) -> dict | None:
    """
    Get movie information from Discord message ID.

    Args:
        message_id (int): Discord message ID

    Returns:
        dict | None: Movie data or None if not found
    """
    try:
        result = supabase.table("movies").select("*").eq("message_id", message_id).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error getting movie from message ID: {e}")
        return None
def get_channel_id_by_guild(guild_id):
    return (
        supabase.table("settings")
        .select("channel_id")
        .eq("guild_id", guild_id)
        .limit(1)
        .execute()
    )
# Rating system utilities (1-10 scale)
DIGIT_EMOJIS = {
    '1️⃣': 1, '2️⃣': 2, '3️⃣': 3, '4️⃣': 4,
    '5️⃣': 5, '6️⃣': 6, '7️⃣': 7, '8️⃣': 8, '9️⃣': 9,
    '🔟': 10  # Special case for 10
}

EMOJI_TO_DIGIT = {v: k for k, v in DIGIT_EMOJIS.items()}