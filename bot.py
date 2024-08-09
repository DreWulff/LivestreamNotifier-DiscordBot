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

def get_notify_message(url, title, name, channel_id, mention_everyone) -> str:
    """Structures the message to notify channel subscribers."""
    prefix = f'## {name}\'s [stream is live]({url}) !'
    message = prefix + f'\nGo watch today\'s stream **{remove_urls(title)}**\n*'
    if (mention_everyone):
        message += '@here get in here!'
    else:
        message += 'Subscribers:  '
        for sub in database.get_subs(channel_id):
            message += f"<@{sub}>; "
    message += "*"
    return message

async def register_channel_status(name, title, url, is_live) -> None:
    """Handles the actions to be realized when a stream is found to go online/offline."""
    ch_id, ch_name, platform, dschannel_id, mentions, status, ch_title, flag = database.get_channel_by_name(name)
    if (not bool(status) and is_live):
        message = get_notify_message(url, title, name, ch_id, bool(mentions))
        database.update_int_value('channels', 'islive', True, 'id', ch_id)
        database.update_str_value('channels', 'livetitle', title, 'id', ch_id)
        database.update_int_value('channels', 'deleteflag', False, 'id', ch_id)
        ds_channel = await BOT.fetch_channel(dschannel_id)
        allowed_mentions = discord.AllowedMentions(roles=True)
        await ds_channel.send(message, allowed_mentions=allowed_mentions)
    elif (bool(status) and is_live):
        database.update_int_value('channels', 'deleteflag', False, 'id', ch_id)
    elif (bool(status) and not is_live):
        if (bool(flag)):
            database.update_int_value('channels', 'islive', False, 'id', ch_id)
            database.update_str_value('channels', 'livetitle', None, 'id', ch_id)
            database.update_int_value('channels', 'deleteflag', False, 'id', ch_id)
        else:
            database.update_int_value('channels', 'deleteflag', True, 'id', ch_id)

async def is_live_YT(name) -> None:
    """Checks if a YouTube channel is live."""
    url = f'https://www.youtube.com/@{name}/live'
    x = requests.get(url)
    content = x.content.decode('utf8')
    title = content.split('<title>')[1].split('</title>')[0]
    aux = content.split('<link rel="canonical" href="https://www.youtube.com/')
    aux = aux[1].split('>')[0].split('?') if len(aux) > 0 else []
    is_livestream = aux.count('watch') > 0
    is_live = content.split('"status":"', maxsplit=2)[1].split('"', maxsplit=2)[0] == 'OK' if is_livestream else False
    await register_channel_status(name, title, url, is_live)

async def is_live_TW(name) -> None:
    """Checks if a Twitch channel is live."""
    url = f'https://www.twitch.tv/{name}'
    x = requests.get(url)
    content = x.content.decode('utf8')
    is_live = content.find('"isLiveBroadcast":true') > 0
    title = content.split('"VideoObject","description":"')[1].split('"')[0] if is_live else ""
    await register_channel_status(name, title, url, is_live)

# Periodic check for livestreams
@tasks.loop(minutes=5)
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
        database.update_int_value("channels", "dschannel", interaction.channel.id, "id", channel_id)
        channel_name = database.get_channel(channel_id)[1]
        await interaction.response.send_message(f"{channel_name}'s livestreams will be notified here!")

@setchannel.autocomplete("channel")
async def autocomplete_setchannel_channel(
    interaction: discord.Interaction,
    current: str):
    channels = database.get_channels()
    channels = [discord.app_commands.Choice(name=channel[1], value=str(channel[0])) for channel in channels]
    return channels

# ⭐ /mentions decorators
@BOT.tree.command(name="mentions", description="Sets whether the notification will mention everyone or only the subscribers.")
async def mentions(
        interaction: discord.Interaction,
        channel: str,
        mode: str): # True: Mention everyone; False: Mention subscribers only
    channel_id = int(channel)
    rows = database.get_channels()
    ids = [row[0] for row in rows]
    mode_bool = True if mode == 'Everyone' else False
    if (channel_id not in ids):
        await interaction.response.send_message("Channel doesn't exist!", ephemeral=True)
    else:
        database.update_int_value("channels", "everyone", mode_bool, "id", channel_id)
        channel_name = database.get_channel(channel_id)[1]
        if (mode_bool):
            await interaction.response.send_message(f"## {channel_name} will now be notified to everyone!")
        else:
            await interaction.response.send_message(f"## {channel_name} will now only be notified to subscribers!")

@mentions.autocomplete("channel")
async def autocomplete_mentions_channel(
    interaction: discord.Interaction,
    current: str):
    channels = database.get_channels()
    channels = [discord.app_commands.Choice(name=channel[1], value=str(channel[0])) for channel in channels]
    return channels

@mentions.autocomplete("mode")
async def autocomplete_mentions_mode(
    interaction: discord.Interaction,
    current: str):
    modes = [
        discord.app_commands.Choice(name='Everyone', value='Everyone'),
        discord.app_commands.Choice(name='Subscribers only', value='Subscribers only')]
    return modes

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
    if (platform.lower() == "youtube"):
        url = "https://www.youtube.com/@{name}/live"
    elif (platform.lower() == "twitch"):
        url = "https://www.twitch.tv/{name}"
    else:
        await interaction.response.send_message("Invalid platform name.", ephemeral=True)
        return None
    channels = database.get_channels(platform)
    # channel = [name, status, url, title]
    channels = [[channel[1], bool(channel[5]), url.format(name=channel[1]), channel[6]] for channel in channels]
    channel_list = "# Channels:"
    for channel in channels:
        status = f"[{remove_urls(channel[3])}](<{channel[2]}>)" if channel[1] else "offline"
        channel_list += f"\n* **{channel[0]}**: {status}"
    await interaction.response.send_message(channel_list, ephemeral=True)
    

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
                                            "* `/channels [platform]`:\n"+
                                            "   * Lists all registered channels from specified `platform` and their current status.\n" +
                                            "* `/mentions [channel]`:\n"+
                                            "   * Changes the notification mode of the channel between mentioning everyone connected (`@here`) or subscribers only.\n" +
                                            "* `/help`:\n"+
                                            "   * Shows the user a list of all of this bot's commands.",
                                            ephemeral=True)

BOT.run(TOKEN)