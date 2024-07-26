import re
from .models import Settings
import discord
from .models import Media, URLInfo
import aiohttp
from urllib.parse import urlparse, parse_qs
from supabase import create_client, Client
settings = Settings()  # type: ignore

supabase_url: str = settings.SUPABASE_URL
supabase_key: str = settings.SUPABASE_KEY
supabase: Client = create_client(supabase_url, supabase_key)


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
    Retrieves IMDb information for a given IMDb ID.

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
            media = Media(**data)
            if media.Response is True:
                return media
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


async def make_embed(media: Media, user_rating: str | None, imdb_url: str) -> discord.Embed:
    """
    Creates an embed message with the IMDb information.

    Args:
        media (Media): The instance of the Media class containing the IMDb information.

    Returns:
        discord.Embed: An embed message with the IMDb information.

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
    embed.add_field(name="User Rating", value=f"⭐ {user_rating}", inline=True)
    return embed


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
    supabase.table("movies").insert(
        {
            "imdb_id": media_info.imdbID,
            "message_id": sent_message.id,
            "user_rating": (
                float(url_info.USER_RATING)
                if url_info.USER_RATING is not None
                else None
            ),
            "channel_id": sent_message.channel.id,
            "guild_id": sent_message.guild.id,
        }
    ).execute()  # This is required to process commands

def find_existing_movie(message, url_info):
    return (
                supabase.table("movies")
                .select("*")
                .eq("imdb_id", url_info.IMDB_ID)
                .eq("channel_id", message.channel.id)
                .eq("guild_id", message.guild.id if message.guild else None)
                .limit(1)
                .execute()
            )

def get_channel_id_by_guild(guild_id):
    return (
        supabase.table("settings")
        .select("channel_id")
        .eq("guild_id", guild_id)
        .limit(1)
        .execute()
    )