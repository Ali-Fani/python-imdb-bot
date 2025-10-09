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

# Import Sentry for performance monitoring
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from .views import ChannelMenu
from .models import Settings
from .utils import (
    find_existing_movie, get_channel_id_by_guild, get_imdb_info, make_embed, parse_message,
    save_media_metadata, supabase, update_media_user_rating, validate_database_schema,
    invalidate_rating_cache, get_movie_rating_stats_cached, database_keep_alive_task
)

settings = Settings()  # type: ignore
async def channel_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Provide autocomplete suggestions for channel selection.

    Args:
        interaction (discord.Interaction): The Discord interaction object
        current (str): The current input string for filtering

    Returns:
        list[app_commands.Choice[str]]: List of up to 25 channel choices matching the current input
    """
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
    """
    Track a bot-initiated reaction removal to prevent double-processing.

    This prevents the bot from processing its own reaction removals when handling
    invalid reactions or duplicate ratings.

    Args:
        user_id (int): Discord user ID
        message_id (int): Discord message ID
        emoji_str (str): The emoji that was removed
    """
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
async def on_ready() -> None:
    """
    Event handler called when the Discord bot has successfully connected and is ready.

    This event initializes the bot and logs startup information including user details
    and the number of guilds the bot is connected to. Includes Sentry performance monitoring
    if available.
    """
    if SENTRY_AVAILABLE:
        with sentry_sdk.start_transaction(op="bot.ready", name="Bot Ready Event"):
            log = get_logger("bot")
            log.info("Bot started successfully", user=bot.user.name, user_id=bot.user.id)
            log.info("Enhanced IMDB rating system ready", guilds=len(bot.guilds))
    else:
        log = get_logger("bot")
        log.info("Bot started successfully", user=bot.user.name, user_id=bot.user.id)
        log.info("Enhanced IMDB rating system ready", guilds=len(bot.guilds))





@bot.event
@commands.guild_only()
async def on_message(message: discord.Message) -> None:
    """
    Event handler for new messages in Discord guilds.

    Processes messages to detect IMDB URLs and create movie embeds with rating functionality.
    Includes Sentry performance monitoring for message processing operations.

    Args:
        message (discord.Message): The Discord message object
    """
    if SENTRY_AVAILABLE:
        with sentry_sdk.start_transaction(op="bot.message", name="Message Processing Event") as transaction:
            transaction.set_data("message_id", message.id)
            transaction.set_data("author_id", message.author.id)
            transaction.set_data("channel_id", message.channel.id)
            transaction.set_data("guild_id", message.guild.id if message.guild else None)
            await _process_message(message)
    else:
        await _process_message(message)


async def _process_message(message: discord.Message) -> None:
    """
    Process incoming Discord messages for IMDB URL detection and movie posting.

    This function handles the core bot logic:
    1. Validates the message (ignores bots, checks channel configuration)
    2. Parses messages for IMDB URLs
    3. Checks if movie already exists
    4. Fetches movie data from OMDB API
    5. Creates and posts movie embed with rating functionality

    Args:
        message (discord.Message): The Discord message to process
    """
    log = get_logger("message_handler")

    # Log message reception
    log.info("Message received",
             message_id=message.id,
             author_id=message.author.id,
             author_name=message.author.name,
             channel_id=message.channel.id,
             guild_id=message.guild.id if message.guild else None,
             content_length=len(message.content),
             has_attachments=len(message.attachments) > 0)

    if message.author.bot:  # If the message is sent by a bot, return
        log.debug("Ignoring bot message", author_id=message.author.id)
        return

    if message.guild is not None:
        guild_id = message.guild.id
    else:
        log.warning("Message received outside guild context", message_id=message.id)
        return

    channel_id = get_channel_id_by_guild(guild_id)
    log.debug("Channel configuration check",
              guild_id=guild_id,
              configured_channel=channel_id.data[0]["channel_id"] if channel_id.data else None,
              message_channel=message.channel.id)

    if channel_id.data and message.channel.id == channel_id.data[0]["channel_id"]:
        log.info("Processing message in configured channel",
                 guild_id=guild_id,
                 channel_id=message.channel.id)

        try:
            url_info = await parse_message(message.content)
            if url_info:
                log.info("IMDB URL parsed successfully",
                         imdb_id=url_info.IMDB_ID,
                         imdb_uri=url_info.IMDB_URI,
                         user_rating=url_info.USER_RATING)

                exists_in_channel = await find_existing_movie(message, url_info)
                if exists_in_channel.data:
                    # Movie already exists - inform user they can rate with reactions
                    log.info("Movie already exists in channel",
                             imdb_id=url_info.IMDB_ID,
                             existing_message_id=exists_in_channel.data[0]["message_id"])

                    already_exist_message = await message.channel.send(
                        f"Movie already exists! You can rate it using digit emojis (1️⃣-9️⃣, 🔟) on the embed message (1-10 scale)."
                    )
                    await message.delete()
                    await already_exist_message.delete(delay=5)
                    return
                else:
                    log.info("Fetching IMDB info for new movie", imdb_id=url_info.IMDB_ID)
                    media_info = await get_imdb_info(url_info.IMDB_ID)
                    if media_info:
                        log.info("IMDB info retrieved successfully",
                                 title=media_info.Title,
                                 year=media_info.Year,
                                 imdb_rating=media_info.imdbRating)

                        embed, view = await make_embed(
                            media_info, url_info.IMDB_URI, message.channel.id, message.guild.id
                        )
                        sent_message = await message.channel.send(embed=embed, view=view)
                        save_media_metadata(url_info, media_info, sent_message)
                        await message.delete()

                        log.info("Movie embed posted successfully",
                                 sent_message_id=sent_message.id,
                                 imdb_id=url_info.IMDB_ID)
                    else:
                        log.error("Failed to retrieve IMDB info", imdb_id=url_info.IMDB_ID)
                        error_msg = await message.channel.send("Movie not found or API error occurred.")
                        await error_msg.delete(delay=10)
            else:
                log.debug("Message does not contain valid IMDB URL", content_preview=message.content[:100])
        except Exception as e:
            log.error("Error processing message",
                     error=str(e),
                     message_id=message.id,
                     content_preview=message.content[:100])
            try:
                error_msg = await message.channel.send("An error occurred while processing your message.")
                await error_msg.delete(delay=10)
            except:
                pass
    else:
        log.debug("Message not in configured channel",
                  guild_id=guild_id,
                  message_channel=message.channel.id,
                  configured_channel=channel_id.data[0]["channel_id"] if channel_id.data else None)

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Handle when a user adds a reaction to a message (works without message cache)."""
    if SENTRY_AVAILABLE:
        with sentry_sdk.start_transaction(op="bot.reaction.add", name="Reaction Add Event") as transaction:
            transaction.set_data("user_id", payload.user_id)
            transaction.set_data("message_id", payload.message_id)
            transaction.set_data("channel_id", payload.channel_id)
            transaction.set_data("guild_id", payload.guild_id)
            transaction.set_data("emoji", str(payload.emoji))
            await _process_reaction_add(payload)
    else:
        await _process_reaction_add(payload)


async def _process_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    """
    Process reaction additions for movie rating functionality.

    Handles the core rating system logic:
    1. Validates reaction emoji and user permissions
    2. Checks for duplicate ratings
    3. Saves rating to database
    4. Updates movie embed with new statistics

    Args:
        payload (discord.RawReactionActionEvent): The raw reaction event payload
    """
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

    # Validate the emoji - only allow rating emojis (1️⃣-9️⃣, 🔟)
    emoji_str = str(payload.emoji)
    print(f"DEBUG: Validating emoji: '{emoji_str}'")

    if not is_valid_rating_emoji(emoji_str):
        print(f"DEBUG: Invalid emoji '{emoji_str}', removing reaction")
        # Track this as a bot-initiated removal to prevent double-processing
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

    # Convert emoji to rating value and save to database
    rating_value = emoji_to_rating(emoji_str)
    print(f"DEBUG: Converted emoji '{emoji_str}' to rating value: {rating_value}")

    if rating_value is not None:
        print(f"DEBUG: Saving rating {rating_value} for user {payload.user_id}")
        # Use upsert to handle both insert and update cases
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
                await invalidate_rating_cache(movie_data["imdb_id"], payload.channel_id, guild_id)
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
    if SENTRY_AVAILABLE:
        with sentry_sdk.start_transaction(op="bot.reaction.remove", name="Reaction Remove Event") as transaction:
            transaction.set_data("user_id", payload.user_id)
            transaction.set_data("message_id", payload.message_id)
            transaction.set_data("channel_id", payload.channel_id)
            transaction.set_data("guild_id", payload.guild_id)
            transaction.set_data("emoji", str(payload.emoji))
            await _process_reaction_remove(payload)
    else:
        await _process_reaction_remove(payload)


async def _process_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    """
    Process reaction removals for movie rating functionality.

    Handles rating removal when users remove their reactions:
    1. Validates the reaction was user-initiated (not bot-initiated)
    2. Removes the rating from database
    3. Updates movie embed with new statistics

    Args:
        payload (discord.RawReactionActionEvent): The raw reaction removal event payload
    """
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
            await invalidate_rating_cache(movie_data["imdb_id"], payload.channel_id, guild_id)
            await update_movie_embed(message, movie_data["imdb_id"])
            print("DEBUG: Embed updated successfully")
        except Exception as e:
            print(f"ERROR: Failed to update embed after rating removal: {e}")
    else:
        print("DEBUG: Failed to remove rating")


async def update_movie_embed(message: discord.Message, imdb_id: str):
    """
    Update the movie embed with current rating statistics.

    Retrieves the latest rating statistics from cache/database and updates
    the "Community Rating" field in the Discord embed.

    Args:
        message (discord.Message): The Discord message containing the movie embed
        imdb_id (str): The IMDB ID of the movie to update ratings for
    """
    try:
        # Get current rating stats with caching
        rating_stats = await get_movie_rating_stats_cached(imdb_id, message.channel.id, message.guild.id)

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


@bot.command() # type: ignore
@commands.is_owner()
async def test_error(ctx: commands.Context) -> None:
    """Test Sentry error reporting by raising an exception"""
    try:
        # This will cause an error to test Sentry
        raise ValueError("Test error for Sentry integration")
    except Exception as e:
        # Re-raise to let Sentry catch it
        raise e


@bot.command() # type: ignore
@commands.is_owner()
async def test_performance(ctx: commands.Context) -> None:
    """Test Sentry performance monitoring"""
    import asyncio

    if SENTRY_AVAILABLE:
        with sentry_sdk.start_transaction(op="test.performance", name="Performance Test Transaction") as transaction:
            transaction.set_data("user_id", ctx.author.id)
            transaction.set_data("channel_id", ctx.channel.id)
            transaction.set_data("guild_id", ctx.guild.id if ctx.guild else None)

            # Simulate some work
            await asyncio.sleep(0.1)

            await ctx.send("Performance test completed - check Sentry for transaction data")
    else:
        await ctx.send("Sentry not available")


async def run_bot():
    """
    Start and run the Discord bot.

    Initializes the bot connection to Discord using the configured token.
    This function handles the bot's main event loop and connection management.

    Raises:
        Exception: If bot fails to start or encounters a critical error
    """
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

            # Start database keep-alive task
            keep_alive_task = asyncio.create_task(database_keep_alive_task())

            # Wait for all tasks to complete (or fail)
            await asyncio.gather(health_task, bot_task, keep_alive_task)

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
