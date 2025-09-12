import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
from .logging_config import setup_logging, get_logger
from .utils import validate_database_schema
from .health import start_health_server

from .views import ChannelMenu
from .models import Settings
from .utils import (
    find_existing_movie, get_channel_id_by_guild, get_imdb_info, make_embed, parse_message,
    save_media_metadata, supabase, update_media_user_rating, validate_database_schema,
    invalidate_rating_cache
)

settings = Settings()  # type: ignore
async def channel_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    if interaction.guild is None:
        return []
    channels = interaction.guild.text_channels
    filtered = [
        ch for ch in channels
        if current.lower() in ch.name.lower()
    ]
    return [
        app_commands.Choice(name=ch.name, value=str(ch.id))
        for ch in filtered[:25]
    ]





# Explicitly configure intents for reaction events
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.reactions = True
intents.members = True  # Required for user information

bot = commands.Bot(command_prefix="!", intents=intents)

# Track bot-initiated reaction removals to prevent double-processing
bot_initiated_removals = set()
REMOVAL_COOLDOWN = 5  # seconds

def track_reaction_removal(user_id: int, message_id: int, emoji_str: str):
    """Track a bot-initiated reaction removal to prevent double-processing"""
    key = f"{user_id}:{message_id}:{emoji_str}"
    bot_initiated_removals.add(key)

    # Auto-cleanup after cooldown period
    async def cleanup():
        await asyncio.sleep(REMOVAL_COOLDOWN)
        bot_initiated_removals.discard(key)

    asyncio.create_task(cleanup())

def is_bot_initiated_removal(user_id: int, message_id: int, emoji_str: str) -> bool:
    """Check if a reaction removal was initiated by the bot"""
    key = f"{user_id}:{message_id}:{emoji_str}"
    return key in bot_initiated_removals




@bot.event
async def on_ready() -> None:  # This event is called when the bot is ready
    log = get_logger("bot")
    log.info("Bot started successfully", user=bot.user.name, user_id=bot.user.id)
    log.info("Enhanced IMDB rating system ready", guilds=len(bot.guilds))





@bot.event
@commands.guild_only()
async def on_message(
    message: discord.Message,
) -> None:  # This event is called when a message is sent
    if message.author.bot:  # If the message is sent by a bot, return
        return

    if message.guild is not None:
        guild_id = message.guild.id
    channel_id = get_channel_id_by_guild(guild_id)
    print(f"DEBUG: Guild ID: {guild_id}, Channel ID data: {channel_id.data}")
    if channel_id.data and message.channel.id == channel_id.data[0]["channel_id"]:
        url_info = await parse_message(message.content)
        if url_info:
            exists_in_channel = await find_existing_movie(message, url_info)
            if exists_in_channel.data:
                # Movie already exists - inform user they can rate with reactions
                already_exist_message = await message.channel.send(
                    f"Movie already exists! You can rate it using digit emojis (1️⃣-9️⃣, 🔟) on the embed message (1-10 scale)."
                )
                await message.delete()
                await already_exist_message.delete(delay=5)
                return
            else:
                media_info = await get_imdb_info(url_info.IMDB_ID)
                if media_info:
                    embed, view = await make_embed(
                        media_info, url_info.IMDB_URI, message.channel.id, message.guild.id
                    )
                    sent_message = await message.channel.send(embed=embed, view=view)
                    save_media_metadata(url_info, media_info, sent_message)
                    await message.delete()

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Handle when a user adds a reaction to a message (works without message cache)."""
    print(f"DEBUG: Raw reaction added by user {payload.user_id} to message {payload.message_id}")

    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        print("DEBUG: Ignoring bot's own reaction")
        return

    # Get the channel and check if it's a configured channel
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    # Check if this channel is configured for the bot
    guild_id = payload.guild_id
    channel_data = supabase.table("settings").select("channel_id").eq("guild_id", guild_id).execute()
    if not channel_data.data or channel_data.data[0]["channel_id"] != payload.channel_id:
        return

    # Check if the reaction is on a movie embed message
    movie_data = get_movie_from_message_id(payload.message_id)
    if not movie_data:
        print(f"DEBUG: Message {payload.message_id} is not a movie message")
        return

    print(f"DEBUG: Found movie data for IMDB ID: {movie_data['imdb_id']}")

    # Validate the emoji
    emoji_str = str(payload.emoji)
    print(f"DEBUG: Validating emoji: '{emoji_str}'")

    if not is_valid_rating_emoji(emoji_str):
        print(f"DEBUG: Invalid emoji '{emoji_str}', removing reaction")
        # Track this as a bot-initiated removal
        track_reaction_removal(payload.user_id, payload.message_id, emoji_str)

        # Remove invalid reaction
        try:
            # Use the bot's HTTP method to remove the reaction directly
            await bot.http.remove_reaction(
                payload.channel_id,
                payload.message_id,
                payload.emoji._as_reaction(),
                payload.user_id
            )

            warning_msg = await channel.send(
                f"<@{payload.user_id}>, please use digit emojis (1️⃣-9️⃣, 🔟) to rate movies (1-10 scale)!"
            )
            await warning_msg.delete(delay=5)
        except discord.Forbidden:
            print("DEBUG: Bot doesn't have permission to remove reactions or send messages")
            # Fallback: try to send warning without removing reaction
            try:
                warning_msg = await channel.send(
                    f"<@{payload.user_id}>, please use valid rating emojis (1️⃣-9️⃣, 🔟) and remove your invalid reaction manually."
                )
                await warning_msg.delete(delay=10)
            except:
                pass
        except Exception as e:
            print(f"ERROR: Failed to remove invalid reaction: {e}")
            # Fallback: try alternative method
            try:
                message = await channel.fetch_message(payload.message_id)
                # Try to find and remove the reaction
                for reaction in message.reactions:
                    if str(reaction.emoji) == str(payload.emoji):
                        # Get user from cache or fetch
                        user = message.guild.get_member(payload.user_id)
                        if not user:
                            user = bot.get_user(payload.user_id)
                        if user:
                            await reaction.remove(user)
                            print(f"DEBUG: Successfully removed invalid reaction using fallback method")
                            break
            except Exception as e2:
                print(f"ERROR: Fallback reaction removal also failed: {e2}")
        return

    # Check if user already rated
    has_rated = has_user_rated(payload.user_id, movie_data["imdb_id"], payload.channel_id, guild_id)
    print(f"DEBUG: User {payload.user_id} has rated movie {movie_data['imdb_id']}: {has_rated}")

    if has_rated:
        print("DEBUG: User already rated, removing reaction")
        # Track this as a bot-initiated removal
        track_reaction_removal(payload.user_id, payload.message_id, emoji_str)

        # Remove the reaction and send warning
        try:
            # Use the bot's HTTP method to remove the reaction directly
            await bot.http.remove_reaction(
                payload.channel_id,
                payload.message_id,
                payload.emoji._as_reaction(),
                payload.user_id
            )

            warning_msg = await channel.send(
                f"<@{payload.user_id}>, you can only rate this movie once! Remove your previous rating first if you want to change it."
            )
            await warning_msg.delete(delay=5)
        except discord.Forbidden:
            print("DEBUG: Bot doesn't have permission to manage reactions")
            # Fallback: try to send warning without removing reaction
            try:
                warning_msg = await channel.send(
                    f"<@{payload.user_id}>, you can only rate this movie once! Please remove your reaction manually."
                )
                await warning_msg.delete(delay=10)
            except:
                pass
        except Exception as e:
            print(f"ERROR: Failed to handle duplicate rating: {e}")
            # Fallback: try alternative method
            try:
                message = await channel.fetch_message(payload.message_id)
                # Try to find and remove the reaction
                for reaction in message.reactions:
                    if str(reaction.emoji) == str(payload.emoji):
                        # Get user from cache or fetch
                        user = message.guild.get_member(payload.user_id)
                        if not user:
                            user = bot.get_user(payload.user_id)
                        if user:
                            await reaction.remove(user)
                            print(f"DEBUG: Successfully removed duplicate reaction using fallback method")
                            break
            except Exception as e2:
                print(f"ERROR: Fallback reaction removal also failed: {e2}")
        return

    # Convert emoji to rating and save
    rating_value = emoji_to_rating(emoji_str)
    print(f"DEBUG: Converted emoji '{emoji_str}' to rating value: {rating_value}")

    if rating_value is not None:
        print(f"DEBUG: Saving rating {rating_value} for user {payload.user_id}")
        success = add_or_update_rating(
            payload.user_id,
            movie_data["imdb_id"],
            rating_value,
            payload.channel_id,
            guild_id
        )
        print(f"DEBUG: Rating save result: {success}")

        if success:
            print("DEBUG: Rating saved successfully, updating embed")
            # Fetch message and update embed
            try:
                message = await channel.fetch_message(payload.message_id)
                # Invalidate cache and update the embed with new rating stats
                invalidate_rating_cache(movie_data["imdb_id"], payload.channel_id, guild_id)
                await update_movie_embed(message, movie_data["imdb_id"])
                print("DEBUG: Embed updated successfully")
            except Exception as e:
                print(f"ERROR: Failed to update embed: {e}")
        else:
            print("DEBUG: Failed to save rating")
    else:
        print(f"DEBUG: Could not convert emoji '{emoji_str}' to rating value")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Handle when a user removes a reaction from a message (works without message cache)."""
    print(f"DEBUG: Raw reaction removed by user {payload.user_id} from message {payload.message_id}")

    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        return

    # Check if this removal was initiated by the bot (to prevent double-processing)
    emoji_str = str(payload.emoji)
    if is_bot_initiated_removal(payload.user_id, payload.message_id, emoji_str):
        print(f"DEBUG: Ignoring bot-initiated reaction removal for user {payload.user_id}")
        return

    # Get the channel and check if it's a configured channel
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    # Check if this channel is configured for the bot
    guild_id = payload.guild_id
    channel_data = supabase.table("settings").select("channel_id").eq("guild_id", guild_id).execute()
    if not channel_data.data or channel_data.data[0]["channel_id"] != payload.channel_id:
        return

    # Check if the reaction is on a movie embed message
    movie_data = get_movie_from_message_id(payload.message_id)
    if not movie_data:
        return

    # Only process if it's a valid rating emoji
    if not is_valid_rating_emoji(emoji_str):
        return

    print(f"DEBUG: User-initiated rating removal for movie: {movie_data['imdb_id']}")

    # Remove the user's rating (only if it's user-initiated)
    success = remove_user_rating(
        payload.user_id,
        movie_data["imdb_id"],
        payload.channel_id,
        guild_id
    )

    if success:
        print("DEBUG: Rating removed successfully, updating embed")
        # Fetch message and update embed
        try:
            message = await channel.fetch_message(payload.message_id)
            # Invalidate cache and update the embed with new rating stats
            invalidate_rating_cache(movie_data["imdb_id"], payload.channel_id, guild_id)
            await update_movie_embed(message, movie_data["imdb_id"])
            print("DEBUG: Embed updated successfully")
        except Exception as e:
            print(f"ERROR: Failed to update embed after rating removal: {e}")
    else:
        print("DEBUG: Failed to remove rating")


async def update_movie_embed(message: discord.Message, imdb_id: str):
    """Update the movie embed with current rating statistics."""
    try:
        # Get current rating stats
        rating_stats = get_movie_rating_stats(imdb_id, message.channel.id, message.guild.id)

        # Update the embed field
        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "Community Rating":
                embed.set_field_at(
                    i,
                    name="Community Rating",
                    value=format_rating_display(rating_stats["average"], rating_stats["count"]),
                    inline=True
                )
                break

        await message.edit(embed=embed)
    except Exception as e:
        print(f"Error updating movie embed: {e}")
@bot.command() # type: ignore
@commands.is_owner()
async def test_reactions(ctx: commands.Context):
    """Test reaction removal functionality"""
    test_embed = discord.Embed(
        title="🧪 Reaction Test",
        description="React with 1️⃣ to test the system!",
        color=0x00FF00
    )
    test_embed.add_field(name="Instructions", value="React with 1️⃣ and then try reacting again to test duplicate prevention.", inline=False)

    test_msg = await ctx.send(embed=test_embed)
    # Store test message info for debugging
    print(f"DEBUG: Created test message {test_msg.id} in channel {ctx.channel.id}")


@bot.command() # type: ignore
@commands.is_owner()
async def debug_ratings(ctx: commands.Context, message_id: int = None):
    """Debug command to check ratings for a movie message"""
    try:
        if message_id:
            # Get ratings for specific message
            movie_data = get_movie_from_message_id(message_id)
            if movie_data:
                rating_stats = get_movie_rating_stats(movie_data["imdb_id"], ctx.channel.id, ctx.guild.id)
                embed = discord.Embed(
                    title="🎬 Rating Debug Info",
                    color=0x00FF00
                )
                embed.add_field(name="IMDB ID", value=movie_data["imdb_id"], inline=True)
                embed.add_field(name="Message ID", value=str(message_id), inline=True)
                embed.add_field(name="Average Rating", value=f"{rating_stats['average']}", inline=True)
                embed.add_field(name="Vote Count", value=str(rating_stats["count"]), inline=True)
                embed.add_field(name="Individual Ratings", value=str(rating_stats["ratings"])[:1000], inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No movie found for that message ID")
        else:
            # List all movies in this channel
            movies_result = supabase.table("movies").select("*").eq("channel_id", ctx.channel.id).eq("guild_id", ctx.guild.id).execute()
            if movies_result.data:
                embed = discord.Embed(
                    title="🎬 Movies in this channel",
                    color=0x00FF00
                )
                for movie in movies_result.data[:10]:  # Limit to 10
                    rating_stats = get_movie_rating_stats(movie["imdb_id"], ctx.channel.id, ctx.guild.id)
                    embed.add_field(
                        name=f"{movie['imdb_id']}",
                        value=f"⭐ {rating_stats['average']} ({rating_stats['count']} votes)\nMessage: {movie['message_id']}",
                        inline=False
                    )
                await ctx.send(embed=embed)
            else:
                await ctx.send("📭 No movies found in this channel")

    except Exception as e:
        await ctx.send(f"❌ Debug error: {str(e)}")


# Import additional functions
from .utils import (
    is_valid_rating_emoji,
    emoji_to_rating,
    has_user_rated,
    add_or_update_rating,
    remove_user_rating,
    get_movie_rating_stats,
    format_rating_display,
    get_movie_from_message_id
)






@bot.command()  # type: ignore
async def ping(ctx: commands.Context) -> None:
    await ctx.send(f"> Pong! {round(bot.latency * 1000)}ms")


@bot.tree.command(name="echo", description="Echoes a message.") # type: ignore
@app_commands.describe(message="The message to echo.")
async def echo(interaction: discord.Interaction, message: str) -> None:
    await interaction.response.send_message(message)


@app_commands.guild_only()
@bot.tree.command(
    name="setchannel",
    description="Set the channel to listen for messages."
)
@app_commands.autocomplete(channel=channel_autocomplete)
@app_commands.describe(channel="The text channel to set for listening.")
async def setchannel(interaction: discord.Interaction, channel: str):
    channel_id = int(channel)
    supabase.table("settings").upsert(
        {"channel_id": channel_id, "guild_id": interaction.guild_id}
    ).execute()
    await interaction.response.send_message(f"Channel set to <#{channel_id}>")


@bot.command() # type: ignore
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    """Sync commands"""
    synced = await bot.tree.sync()
    print(synced)
    await ctx.send(f"Synced {len(synced)} commands globally")


async def run_bot():
    """Run the Discord bot"""
    try:
        log = get_logger("bot")
        log.info("Starting Discord bot")
        await bot.start(settings.DISCORD_TOKEN)
    except Exception as e:
        log.error("Bot crashed", error=str(e))
        raise

def main():
    """Main entry point for the IMDB bot"""
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

    # Start both health check server and bot concurrently
    async def run_services():
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
            log.error("Service error", error=str(e))
            raise

    # Run the async services
    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        log.info("Application shutdown complete")
    except Exception as e:
        log.error("Application crashed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
