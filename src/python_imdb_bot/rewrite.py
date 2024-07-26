import discord
from discord.ext import commands
from discord import app_commands

from .views import ChannelMenu
from .models import Settings
from .utils import find_existing_movie, get_channel_id_by_guild, get_imdb_info, make_embed, parse_message, save_media_metadata, update_media_user_rating

settings = Settings()  # type: ignore




bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@bot.event
async def on_ready() -> None:  # This event is called when the bot is ready
    print(f"Logged in as {bot.user}")





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
    if message.channel.id == channel_id.data[0]["channel_id"]:
        url_info = await parse_message(message.content)
        if url_info:
            exists_in_channel = find_existing_movie(message, url_info)
            if exists_in_channel.data:
                old_message = await message.channel.fetch_message(
                    exists_in_channel.data[0]["message_id"]
                )
                embed = old_message.embeds[0]
                if (
                    embed.fields[3].value != f"⭐ {url_info.USER_RATING}"
                    and url_info.USER_RATING is not None
                ):
                    update_media_user_rating(url_info)
                    embed.set_field_at(
                        11,
                        name="User Rating",
                        value=f"⭐ {url_info.USER_RATING}",
                        inline=True,
                    )
                    await old_message.edit(embed=embed)
                    already_exist_message = await message.channel.send(
                        "Movie already exists, User rating updated!"
                    )
                    await message.delete()
                    await already_exist_message.delete(delay=5)
                    return
            else:
                media_info = await get_imdb_info(url_info.IMDB_ID)
                if media_info:
                    embed = await make_embed(
                        media_info, url_info.USER_RATING, url_info.IMDB_URI
                    )
                    sent_message = await message.channel.send(embed=embed)
                    save_media_metadata(url_info, media_info, sent_message)
                    await message.delete()

    await bot.process_commands(message)






@bot.command()  # type: ignore
async def ping(ctx: commands.Context) -> None:
    await ctx.send(f"> Pong! {round(bot.latency * 1000)}ms")


@bot.tree.command(name="echo", description="Echoes a message.") # type: ignore
@app_commands.describe(message="The message to echo.")
async def echo(interaction: discord.Interaction, message: str) -> None:
    await interaction.response.send_message(message)


@bot.tree.command( # type: ignore
    name="setchannel", description="Set the channel to listen for messages."
)
async def setchannel(interaction: discord.Interaction):
    view = ChannelMenu(interaction.user, timeout=0)
    await interaction.response.send_message("Select a channel", view=view)


@bot.command() # type: ignore
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    """Sync commands"""
    synced = await bot.tree.sync()
    print(synced)
    await ctx.send(f"Synced {len(synced)} commands globally")


bot.run(settings.DISCORD_TOKEN)
