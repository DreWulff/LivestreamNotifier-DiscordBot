# bot.py
# Python libraries
import os
import asyncio
import requests

# Local module
import database

# External libraries
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.app_commands import Choice

# .env variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Variables for bot initialization
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)

LIVES_YT = dict()
LIVES_TW = dict()

def remove_urls(title) -> str:
    """Removes any urls present in a livestream's title."""
    if (title.find('http') > 0):
        final = ""
        split = title.split('http')
        if (len(split[0]) > 0):
            final += split[0][:-1]
        if (split[1].find(' ') > 0):
            final += split[1].split(' ')[1]
    else:
        final = title
    return final

def get_notify_message(url, title, name, channel_id) -> str:
    """Structures the message to notify channel subscribers."""
    prefix = f'## {name}\'s [stream is live]({url}) !'
    message = prefix + f'\nGo watch today\'s stream **{remove_urls(title)}**\n*Subscribers:  '
    for sub in database.get_subs(channel_id):
        message += f"<@{sub}>; "
    message += "*"
    return message

async def is_live_YT(name) -> None:
    """Checks if a YouTube channel is live."""
    global LIVES_YT, GUILD
    url = f'https://www.youtube.com/@{name}/live'
    x = requests.get(url)
    content = x.content.decode('utf8')
    title = content.split('<title>')[1].split('</title>')[0]
    aux = content.split('<link rel="canonical" href="https://www.youtube.com/')
    aux = aux[1].split('>')[0].split('?') if len(aux) > 0 else []
    is_livestream = aux.count('watch') > 0
    is_live = content.split('"status":"', maxsplit=2)[1].split('"', maxsplit=2)[0] == 'OK' if is_livestream else False
    
    if ((name not in LIVES_YT.keys()) and is_livestream and is_live):
        LIVES_YT[name] = [url, title]
        channel_data = database.get_channel_by_name(name)
        ds_channel = BOT.get_channel(channel_data[3])
        message = get_notify_message(url, title, name, channel_data[0])
        allowed_mentions = discord.AllowedMentions(roles=True)
        await ds_channel.send(message, allowed_mentions=allowed_mentions)
    elif ((name in LIVES_YT.keys()) and (not is_livestream or not is_live)):
        LIVES_YT.pop(name)

async def is_live_TW(name) -> None:
    """Checks if a Twitch channel is live."""
    global LIVES_TW
    url = f'https://www.twitch.tv/{name}'
    x = requests.get(url)
    content = x.content.decode('utf8')
    is_live = content.find('isLiveBroadcast') > 0
    if ((name not in LIVES_TW.keys()) and is_live):
        title = content.split('"VideoObject","description":"')[1].split('"')[0]
        LIVES_TW[name] = [url, title]
        channel_data = database.get_channel_by_name(name)
        ds_channel = BOT.get_channel(channel_data[3])
        message = get_notify_message(url, title, name, channel_data[0])
        allowed_mentions = discord.AllowedMentions(roles=True)
        await ds_channel.send(message, allowed_mentions=allowed_mentions)
    elif ((name in LIVES_TW.keys()) and not is_live):
        LIVES_TW.pop(name)

# Periodic check for livestreams
@tasks.loop(minutes=1)
async def check_live():
    yt_channels = [channel_row[1] for channel_row in database.get_channels("YouTube")]
    for channel in yt_channels:
        await is_live_YT(channel)
    
    tw_channels = [channel_row[1] for channel_row in database.get_channels("Twitch")]
    for channel in tw_channels:
        await is_live_TW(channel)

@check_live.before_loop
async def preparation():
    await BOT.wait_until_ready()

# Function called when bot starts
@BOT.event
async def on_ready():
    try:
        database.init_connection()
        synced = await BOT.tree.sync()
        print(f"Synced {len(synced)} commands(s).")
        check_live.start()
    except Exception as exception:
        print(exception)

# Argument descriptions for / commands
@app_commands.describe(
    platform="Platform of the channel. Twitch and YouTube supported.",
    channel="Livestreaming channel.")

# Admin / commands:
# ⭐ /add command decorators
@BOT.tree.command(name="add", description="Add a Twitch or YouTube channel to database.")
async def add(
        interaction: discord.Interaction,
        platform: str,
        channel: str):
    channels = [channel[1] for channel in database.get_channels(platform)]
    if (channel not in channels):
        database.add_channel(channel, platform, interaction.channel.id)
        url_prefix = "https://www.youtube.com/@" if platform == "YouTube" else "https://www.twitch.tv/"
        await interaction.response.send_message(f"## {platform} channel **[{channel}]({url_prefix}{channel})** registered!")
    else:
        await interaction.response.send_message("Channel is already registered!", ephemeral=True)

@add.autocomplete("platform")
async def autocomplete_platform(
    interaction: discord.Interaction,
    current: str):
    return [discord.app_commands.Choice(name="YouTube", value="YouTube"),
            discord.app_commands.Choice(name="Twitch", value="Twitch")]

# ⭐ /remove command decorators
@BOT.tree.command(name="remove", description="Remove a channel from the database.")
async def remove(
        interaction: discord.Interaction,
        channel: str):
    rows = database.get_channels()
    channel_id = int(channel)
    ids = [row[0] for row in rows]
    if (channel_id in ids):
        channel_name = database.get_channel(channel_id)[1] # Get channel's name
        database.remove_channel(channel_id)
        database.remove_subs(channel_id)
        await interaction.response.send_message(f"## Channel **{channel_name}** removed!")
    else:
        await interaction.response.send_message(f"Channel doesn't exist.", ephemeral=True)

@remove.autocomplete("channel")
async def autocomplete_allchannels(
    interaction: discord.Interaction,
    current: str):
    channels = database.get_channels()
    channels = [discord.app_commands.Choice(name=channel[1], value=str(channel[0])) for channel in channels]
    return channels

# ⭐ /setchannel decorators
@BOT.tree.command(name="setchannel", description="Set current Discord text channel to post notifications when channel goes live.")
async def setchannel(
        interaction: discord.Interaction,
        channel: str):
    channel_id = int(channel)
    rows = database.get_channels()
    ids = [row[0] for row in rows]
    if (channel_id not in ids):
        await interaction.response.send_message("Channel doesn't exist!", ephemeral=True)
    else:
        database.update_post_channel(interaction.channel.id, channel_id)
        channel_name = database.get_channel(channel_id)[1]
        await interaction.response.send_message(f"{channel_name}'s livestreams will be notified here!")

@setchannel.autocomplete("channel")
async def autocomplete_setchannel_channel(
    interaction: discord.Interaction,
    current: str):
    channels = database.get_channels()
    channels = [discord.app_commands.Choice(name=channel[1], value=str(channel[0])) for channel in channels]
    return channels

# ⭐ /subscribe decorators
@BOT.tree.command(name="subscribe", description="Subscribe to specified channel.")
async def subscribe(
        interaction: discord.Interaction,
        channel: str):
    channel_id = int(channel)
    if (interaction.user.id in database.get_subs(channel)):
        await interaction.response.send_message("You are already subscribed to this channel!", ephemeral=True)
    else:
        database.add_sub(interaction.user.id, channel_id)
        channel_name = database.get_channel(channel_id)[1]
        await interaction.response.send_message(f"Succesfully subscribed to {channel_name}!", ephemeral=True)

@subscribe.autocomplete("channel")
async def autocomplete_sub_channel(
        interaction: discord.Interaction,
        current: str):
    channels = database.get_unsubd(interaction.user.id)
    channels = [discord.app_commands.Choice(name=channel[1], value=str(channel[0])) for channel in channels]
    return channels

# ⭐ /unsubscribe decorators
@BOT.tree.command(name="unsubscribe", description="Unsubscribe to specified channel.")
async def unsubscribe(
        interaction: discord.Interaction,
        channel: str):
    channel_id = int(channel)
    if (channel_id in [row[0] for row in database.get_subd(interaction.user.id)]):
        database.remove_sub(interaction.user.id, channel_id)
        channel_name = database.get_channel(channel_id)[1]
        await interaction.response.send_message(f"Succesfully unsubscribed to {channel_name}!", ephemeral=True)
    else:
        await interaction.response.send_message("You are not subscribed to this channel.", ephemeral=True)

@unsubscribe.autocomplete("channel")
async def autocomplete_unsub_channel(
    interaction: discord.Interaction,
    current: str):
    channels = database.get_subd(interaction.user.id)
    channels = [discord.app_commands.Choice(name=channel[1], value=str(channel[0])) for channel in channels]
    return channels

# ⭐ /channels decorators
@BOT.tree.command(name="channels", description="Show the list of channels available.")
async def channels(
        interaction: discord.Interaction,
        platform: str):
    if (platform.lower() in ["youtube", "twitch"]):
        channels = database.get_channels(platform)
        channels = [channel[1] for channel in channels]
        channel_list = "# Channels:"
        for channel in channels:
            lives = dict(LIVES_TW, **LIVES_YT)
            status = f"[{remove_urls(lives[channel][1])}](<{lives[channel][0]}>)" if (channel in lives) else "offline"
            channel_list += f"\n* **{channel}**: {status}"
        await interaction.response.send_message(channel_list, ephemeral=True)
    else:
        await interaction.response.send_message("Invalid platform name.", ephemeral=True)

@channels.autocomplete("platform")
async def autocomplete_channels_platform(
    interaction: discord.Interaction,
    current: str):
    return [discord.app_commands.Choice(name="YouTube", value="YouTube"),
            discord.app_commands.Choice(name="Twitch", value="Twitch")]

# /help command decorators
@BOT.tree.command(name="help", description="Give a list of the available commands")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message("* `/add [platform] [channel]`:\n"+
                                            "   * Registers a livestream `channel` in the specified `platform` for future notification.\n"+
                                            " * The bot will periodically check if the streamer is live, and notify through a text channel.\n"+
                                            " * Users can subscribe to the `channel` to get mentioned when stream goes live.\n"+
                                            "* `/remove [channel]`:\n"+
                                            "   * Removes a registered channel and all subscriptions to that `channel`.\n"+
                                            "* `/setchannel [channel]`:\n"+
                                            "   * Sets the current text channel as the medium of notification for specified `channel`.\n"+
                                            "* `/subscribe [channel]`:\n"+
                                            "   * Registers the user to be mentioned when `channel` goes live.\n"+
                                            "* `/unsubscribe [channel]`:\n"+
                                            "   * Removes subscription to specified `channel`.\n" +
                                            "* `/getchannels [platform]`:\n"+
                                            "   * Lists all registered channels from specified `platform` and their current status.\n" +
                                            "* `/help`:\n"+
                                            "   * Shows the user a list of all of this bot's commands.",
                                            ephemeral=True)

BOT.run(TOKEN)