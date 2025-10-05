import time
import logging
import sys
import json
import os
import asyncio
from pathlib import Path
from .models import Settings
import discord
from .models import Media, URLInfo
import aiohttp
from urllib.parse import urlparse, parse_qs
from supabase import create_client, Client
import re
from bs4 import BeautifulSoup

# Import logger
from .logging_config import get_logger

# TinyDB imports (required - already installed)
try:
    from tinydb import TinyDB, Query
    from tinydb.table import Document
    TINYDB_AVAILABLE = True
except ImportError:
    TINYDB_AVAILABLE = False
    TinyDB = None
    Query = None
    Document = None

settings = Settings()  # type: ignore

supabase_url: str = settings.SUPABASE_URL
supabase_key: str = settings.SUPABASE_KEY
supabase: Client = create_client(supabase_url, supabase_key)

# TinyDB client setup
tinydb_client = None
if TINYDB_AVAILABLE:
    # Use a cache file in the data directory
    cache_dir = Path(settings.LOG_FILE).parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "rating_cache.json"
    try:
        tinydb_client = TinyDB(cache_file)
        # Create index on cache_key for better performance
        tinydb_client.table('cache').insert(Document({}, doc_id=0))  # Ensure table exists
    except Exception as e:
        print(f"Warning: Failed to initialize TinyDB cache: {e}")
        tinydb_client = None


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
                # Handle missing poster from OMDB
                if data.get('Poster') == 'N/A':
                    data['Poster'] = None

                media = Media(**data)

                # If poster is still None, try scraping from IMDb
                if not media.Poster:
                    scraped_poster = await get_poster_from_imdb(imdb_id)
                    if scraped_poster:
                        media.Poster = scraped_poster

                # Try to get trailer URL from TMDB if API key is configured
                if hasattr(settings, 'TMDB_API_KEY') and settings.TMDB_API_KEY and settings.TMDB_API_KEY != 'your_tmdb_api_key_here':
                    tmdb_id = await get_tmdb_id_from_imdb(imdb_id)
                    if tmdb_id:
                        trailer_url = await get_movie_trailer(tmdb_id)
                        if trailer_url:
                            media.trailer_url = trailer_url

                return media
    return None


async def get_poster_from_imdb(imdb_id: str) -> str | None:
    """
    Scrape poster URL from IMDb page as fallback when OMDB doesn't have it.

    Args:
        imdb_id (str): The IMDb ID (e.g., 'tt0111161')

    Returns:
        str | None: Poster URL or None if not found
    """
    log = get_logger("imdb_scraper")

    async with aiohttp.ClientSession() as session:
        url = f"https://www.imdb.com/title/{imdb_id}/"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Look for og:image meta tag
                    og_image = soup.find('meta', property='og:image')
                    if og_image and og_image.get('content'):
                        poster_url = og_image['content']
                        log.info("Poster found via IMDb scraping", imdb_id=imdb_id, poster_url=poster_url)
                        return poster_url

                    log.debug("No og:image found in IMDb page", imdb_id=imdb_id)
                else:
                    log.warning("Failed to fetch IMDb page", imdb_id=imdb_id, status=response.status)
        except Exception as e:
            log.error("Error scraping IMDb for poster", imdb_id=imdb_id, error=str(e))

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
    log = get_logger("message_parser")

    log.debug("Parsing message for IMDB URL", message_length=len(message))

    # Regular expression to match IMDB URL and ID
    imdb_pattern = r'(https?://(?:www\.)?imdb\.com/title/(tt\d+))'

    # Find IMDB URL and ID
    match = re.search(imdb_pattern, message)
    if not match:
        log.debug("No IMDB URL found in message")
        return None

    imdb_url, imdb_id = match.groups()
    log.info("IMDB URL found and parsed",
             imdb_id=imdb_id,
             imdb_url=imdb_url)

    # Parse query parameters
    parsed_url = urlparse(message)
    query_params = parse_qs(parsed_url.query)

    # Extract rating and comment (if present)
    rating = query_params.get('rating', [None])[0]

    if rating:
        log.info("User rating found in URL", rating=rating)

    url_info = URLInfo(IMDB_URI=imdb_url, IMDB_ID=imdb_id, USER_RATING=rating)
    log.debug("URL parsing completed successfully", has_rating=rating is not None)

    return url_info


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
    if media.Poster:
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
    Get cached rating statistics from TinyDB if available and not expired.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        dict | None: Cached rating stats or None if not cached/expired
    """
    log = get_logger("cache")

    if not tinydb_client:
        log.debug("TinyDB client not available, skipping cache lookup")
        return None

    cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
    try:
        table = tinydb_client.table('cache')
        query = Query()
        result = table.get(query.cache_key == cache_key)

        if result:
            # Check if cache entry is still valid (TTL)
            cached_time = result.get('timestamp', 0)
            if time.time() - cached_time < _CACHE_TTL:
                log.info("Cache hit for rating stats",
                         imdb_id=imdb_id,
                         channel_id=channel_id,
                         guild_id=guild_id,
                         cache_key=cache_key)
                return result['data']
            else:
                # Cache expired, remove it
                table.remove(doc_ids=[result.doc_id])
                log.debug("Cache expired and removed",
                         imdb_id=imdb_id,
                         channel_id=channel_id,
                         guild_id=guild_id,
                         cache_key=cache_key)

        log.debug("Cache miss for rating stats",
                 imdb_id=imdb_id,
                 channel_id=channel_id,
                 guild_id=guild_id,
                 cache_key=cache_key)
    except Exception as e:
        log.error("TinyDB cache error during get operation",
                 error=str(e),
                 imdb_id=imdb_id,
                 channel_id=channel_id,
                 guild_id=guild_id,
                 cache_key=cache_key)

    return None

async def set_cached_rating_stats(imdb_id: str, channel_id: int, guild_id: int, stats: dict):
    """
    Cache rating statistics in TinyDB with TTL.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID
        stats (dict): Rating statistics to cache
    """
    log = get_logger("cache")

    if not tinydb_client:
        log.debug("TinyDB client not available, skipping cache set")
        return

    cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
    try:
        table = tinydb_client.table('cache')
        query = Query()

        # Remove any existing entry for this cache key
        table.remove(query.cache_key == cache_key)

        # Insert new cache entry
        cache_entry = {
            'cache_key': cache_key,
            'data': stats,
            'timestamp': time.time(),
            'imdb_id': imdb_id,
            'channel_id': channel_id,
            'guild_id': guild_id
        }

        table.insert(cache_entry)
        log.info("Cache set for rating stats",
                 imdb_id=imdb_id,
                 channel_id=channel_id,
                 guild_id=guild_id,
                 cache_key=cache_key,
                 ttl=_CACHE_TTL,
                 average=stats.get("average"),
                 count=stats.get("count"))
    except Exception as e:
        log.error("TinyDB cache error during set operation",
                 error=str(e),
                 imdb_id=imdb_id,
                 channel_id=channel_id,
                 guild_id=guild_id,
                 cache_key=cache_key)

async def invalidate_rating_cache(imdb_id: str, channel_id: int, guild_id: int):
    """
    Remove rating statistics from TinyDB cache.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID
    """
    log = get_logger("cache")

    if not tinydb_client:
        log.debug("TinyDB client not available, skipping cache invalidation")
        return

    cache_key = f"rating_stats:{imdb_id}:{channel_id}:{guild_id}"
    try:
        table = tinydb_client.table('cache')
        query = Query()
        removed_docs = table.remove(query.cache_key == cache_key)
        log.info("Cache invalidated for rating stats",
                 imdb_id=imdb_id,
                 channel_id=channel_id,
                 guild_id=guild_id,
                 cache_key=cache_key,
                 deleted=len(removed_docs) > 0)
    except Exception as e:
        log.error("TinyDB cache error during delete operation",
                 error=str(e),
                 imdb_id=imdb_id,
                 channel_id=channel_id,
                 guild_id=guild_id,
                 cache_key=cache_key)

async def get_movie_rating_stats_cached(imdb_id: str, channel_id: int, guild_id: int) -> dict:
    """
    Get rating statistics with TinyDB caching support.

    Args:
        imdb_id (str): IMDB ID of the movie
        channel_id (int): Discord channel ID
        guild_id (int): Discord guild ID

    Returns:
        dict: Rating statistics (average, count, ratings)
    """
    log = get_logger("cache")

    # Clean up expired cache entries periodically (simple approach)
    await cleanup_expired_cache_entries()

    # Try TinyDB cache first
    cached_stats = await get_cached_rating_stats(imdb_id, channel_id, guild_id)
    if cached_stats:
        return cached_stats

    # Cache miss - fetch from database
    log.debug("Fetching rating stats from database (cache miss)",
             imdb_id=imdb_id,
             channel_id=channel_id,
             guild_id=guild_id)

    stats = get_movie_rating_stats(imdb_id, channel_id, guild_id)

    # Cache the result in TinyDB
    await set_cached_rating_stats(imdb_id, channel_id, guild_id, stats)

    return stats


async def cleanup_expired_cache_entries():
    """
    Remove expired cache entries from TinyDB.
    This is called periodically to maintain cache cleanliness.
    """
    if not tinydb_client:
        return

    try:
        table = tinydb_client.table('cache')
        current_time = time.time()

        # Find all expired entries
        query = Query()
        expired_entries = table.search(query.timestamp < (current_time - _CACHE_TTL))

        if expired_entries:
            # Remove expired entries
            doc_ids_to_remove = [doc.doc_id for doc in expired_entries]
            table.remove(doc_ids=doc_ids_to_remove)

            log = get_logger("cache")
            log.debug("Cleaned up expired cache entries", count=len(expired_entries))

    except Exception as e:
        log = get_logger("cache")
        log.error("Error during cache cleanup", error=str(e))


async def keep_database_alive():
    """
    Perform a simple database query to prevent Supabase free plan suspension.
    This function queries the settings table to keep the database active.
    """
    log = get_logger("keep_alive")

    try:
        # Simple query to keep database active - count settings records
        result = supabase.table("settings").select("id", count="exact").limit(1).execute()
        log.info("Database keep-alive query executed successfully",
                settings_count=result.count if hasattr(result, 'count') else 'unknown')
        return True
    except Exception as e:
        log.error("Database keep-alive query failed", error=str(e))
        return False


async def database_keep_alive_task():
    """
    Background task that runs periodically to keep the Supabase database alive.
    Runs every 6 hours to prevent free plan suspension.
    """
    log = get_logger("keep_alive")

    # Run every 6 hours (21600 seconds) - Supabase free plan suspends after ~7 days
    KEEP_ALIVE_INTERVAL = 6 * 60 * 60  # 6 hours in seconds

    log.info("Starting database keep-alive task", interval_hours=KEEP_ALIVE_INTERVAL/3600)

    while True:
        try:
            success = await keep_database_alive()
            if success:
                log.debug("Database keep-alive successful")
            else:
                log.warning("Database keep-alive failed - will retry on next interval")

        except Exception as e:
            log.error("Unexpected error in keep-alive task", error=str(e))

        # Wait for next interval
        await asyncio.sleep(KEEP_ALIVE_INTERVAL)

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