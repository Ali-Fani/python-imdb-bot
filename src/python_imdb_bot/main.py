# """This module contains the main functionality of the IMDb bot."""
# This is old module that replaced with rewrite its just here for now and will be removed later
# import logging
# import discord
# from supabase import create_client, Client
# from .models import Settings
# from discord.ext import commands
# from discord.components import SelectMenu,SelectOption
# settings = Settings()  # type: ignore
# supabase_url: str = settings.SUPABASE_URL
# supabase_key: str = settings.SUPABASE_KEY
# supabase: Client = create_client(supabase_url, supabase_key)

# DISCORD_BOT_TOKEN = settings.DISCORD_TOKEN
# OMDB_API_KEY = settings.OMDB_API_KEY

# handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

# intents = discord.Intents.default()
# intents.message_content = True
# bot = commands.Bot(command_prefix="!",intents=intents)
# tree = bot.tree
# client = discord.Client(intents=intents)



# @client.event
# async def on_message(message: discord.Message):
#     """
#     Handles the event when a message is received.

#     This function checks if the message was sent by the bot itself, and if it was sent in the
#     designated channel. If both conditions are met, it extracts the IMDb ID and user rating from the
#     message content, retrieves the IMDb information using the `get_imdb_info` function, and creates
#     an embed message with the retrieved information. If the IMDb information is not found, it sends
#     a message indicating that the movie was not found.

#     Args:
#         message (discord.Message): The message object received.

#     Returns:
#         None
#     """
#     # Ignore messages sent by the bot itself
#     if message.author == client.user:
#         return

#     # Check if the message was sent in the designated channel
#     if message.channel.id == settings.CHANNEL_ID:
#         # Get the IMDb ID and user rating from the message content
#         imdb_id, user_rating = get_imdb_id(message.content)
#         logging.info("IMDB ID: %s, User Rating: %s", imdb_id, user_rating)
#         # Check if the IMDb ID exists
#         if imdb_id:
#             response = (
#                 supabase.table("movies")
#                 .select("*")
#                 .eq("imdb_id", imdb_id)
#                 .limit(1)
#                 .execute()
#             )
#             if response.data:
#                 old_message = await message.channel.fetch_message(
#                     response.data[0]["message_id"]
#                 )
#                 embed = old_message.embeds[0]
#                 if (
#                     embed.fields[3].value != f"⭐ {user_rating}"
#                     and user_rating is not None
#                 ):
#                     supabase.table("movies").update(
#                         {
#                             "user_rating": (
#                                 float(user_rating) if user_rating is not None else None
#                             )
#                         }
#                     ).eq("imdb_id", imdb_id).execute()
#                     embed.set_field_at(
#                         3, name="User Rating", value=f"⭐ {user_rating}", inline=True
#                     )
#                     await old_message.edit(embed=embed)
#                     already_exist_message = await message.channel.send(
#                         "Movie already exists, User rating updated!"
#                     )
#                     await message.delete()
#                     await already_exist_message.delete(delay=5)
#                     return
#                 already_exist_message = await message.channel.send(
#                     "Movie already exists"
#                 )
#                 await message.delete()
#                 await already_exist_message.delete(delay=5)
#                 return
#             # Retrieve the IMDb information using the IMDb ID
#             info = await get_imdb_info(imdb_id)
#             # Check if the IMDb information was found
#             if info:
#                 # Create an embed message with the retrieved information
#                 # - refactor creating embed message to a separate function
#                 embed = discord.Embed(
#                     title=f"{info.Title} ({info.Year})",  # Set the title of the embed
#                     description=info.Plot,  # Set the description of the embed
#                     color=discord.Color.blue(),  # Set the color of the embed
#                     # url=url.split("#")[0]
#                 )
#                 embed.add_field(
#                     name="Rating", value=f"⭐ {info.imdbRating}", inline=True
#                 )  # Add a field for the rating
#                 embed.add_field(
#                     name="Genre", value=info.Genre, inline=True
#                 )  # Add a field for the genre
#                 embed.add_field(
#                     name="Type", value=info.Type, inline=True
#                 )  # Add a field for the type

#                 # Add a field for the user rating if it exists

#                 embed.add_field(
#                     name="User Rating",
#                     value=f"⭐ {user_rating or "Not Rated yet"}",
#                     inline=True,
#                 )

#                 # Add a field for the total seasons if the type is a series
#                 if info.Type == "series":
#                     embed.add_field(
#                         name="Total Seasons", value=info.totalSeasons, inline=True
#                     )

#                 embed.add_field(
#                     name="Runtime", value=info.Runtime, inline=True
#                 )  # Add a field for the runtime
#                 embed.add_field(
#                     name="Rated", value=info.Rated, inline=True
#                 )  # Add a field for the rating
#                 embed.set_author(
#                     name=message.author.display_name, icon_url=message.author.avatar
#                 )  # Set the author of the embed
#                 embed.add_field(name="IMDB ID", value=info.imdbID, inline=True)
#                 embed.set_footer(
#                     text="Powered by OMDB API"
#                 )  # Set the footer of the embed

#                 # Set the image of the embed if it exists
#                 if info.Poster:
#                     embed.set_image(url=info.Poster)

#                 # Send the embed message in the channel
#                 sent_message = await message.channel.send(embed=embed)
#                 supabase.table("movies").insert(
#                     {
#                         "imdb_id": imdb_id,
#                         "message_id": sent_message.id,
#                         "user_rating": (
#                             float(user_rating) if user_rating is not None else None
#                         ),
#                     }
#                 ).execute()
#                 await message.delete()

#             else:
#                 # Send a message indicating that the movie was not found
#                 await message.channel.send("Movie not found")
# class MySelect(discord.ui.View):
#     @discord.ui.select(placeholder="Choose a channel",options=[discord.SelectOption(label="test",value="test")])
#     async def select_channel(self,select:discord.ui.Select,interaction:discord.Interaction):
#         await interaction.response.send_message("You selected test",ephemeral=True)


# @bot.tree.command(name="setchannel",description="set_channel")
# @commands.has_permissions(administrator=True)
# async def set_channel(interation:discord.Interaction):
#     await interation.response.send_message("You selected test",ephemeral=True)
#     # text_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel)]
#     # options = [SelectOption(label=channel.name, value=str(channel.id)) for channel in text_channels]
#     # message_with_selects = await ctx.send("Test",view=MySelect())
#     # if ctx.guild is not None:
#     #     guild_id = ctx.guild.id
#     #     supabase.table("settings").upsert({"channel_id": ctx.channel.id,"guild_id":guild_id}).execute()
#     #     await ctx.send(f"Channel set to {ctx.channel.mention}")
#     # else:
#     #     # Handle the case when the command is not executed in a guild context
#     #     await ctx.send(f"Command must be executed in a guild context")

# client.run(DISCORD_BOT_TOKEN, log_handler=handler, log_level=logging.INFO)
