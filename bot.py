# bot.py
# Python libraries
import os
import asyncio
import requests

# External libraries
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.app_commands import Choice

# .env variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ROLE_ID = int(os.getenv('DS_ROLE_ID'))
GUILD_ID = int(os.getenv('DS_GUILD_ID'))
CHAT_ID = int(os.getenv('DS_CHANNEL_ID'))

# Variables for bot initialization
INTENTS = discord.Intents.default()
BOT = commands.Bot(command_prefix="!", intents=INTENTS)
LIVE = False
LIVE_URL = 'https://www.youtube.com/@KanaImeru/live'
LIVE_TITLE = ''

def is_live():
    global LIVE_TITLE, LIVE_URL
    x = requests.get(LIVE_URL)
    content = x.content.decode('utf8')
    title = content.split('<title>')[1].split('</title>')[0]
    is_livestream = len(content.split('<link rel="canonical" href="https://www.youtube.com/')[1].split('>')[0].split('?')) > 1
    live = content.split('"status":"')[1].split('"')[0] == 'OK'
    
    if (is_livestream and live and (not LIVE)):
        LIVE_TITLE = title
        return True
    else:
        return False

def still_live():
    global LIVE_URL
    x = requests.get(LIVE_URL)
    content = x.content.decode('utf8')
    is_livestream = len(content.split('<link rel="canonical" href="https://www.youtube.com/')[1].split('>')[0].split('?')) > 1
    live = content.split('"status":"')[1].split('"')[0] == 'OK'
    if (live and is_livestream):
        return(True)
    else:
        return(False)

@tasks.loop(minutes=1)
async def check_live():
    global GUILD_ID, CHAT_ID, ROLE_ID, LIVE
    guild = BOT.get_guild(GUILD_ID)
    channel = BOT.get_channel(CHAT_ID)
    
    if ((not LIVE) and (is_live()) and (channel) and (guild)):
        role = guild.get_role(ROLE_ID).mention
        prefix = f'## Class is in session {role}' if ('PYTHON' in LIVE_TITLE) else f'## {role} rejoice! Kana is now streaming!'
        message = prefix + f'\nGo watch today\'s stream ***{LIVE_TITLE}*** at:\n\n{LIVE_URL}'
        allowed_mentions = discord.AllowedMentions(roles=True)
        await channel.send(message, allowed_mentions=allowed_mentions)
        LIVE = True

    elif (LIVE and (not still_live())):
        LIVE = False
        await channel.send("Class has ended. Good job!")

@check_live.before_loop
async def preparation():
    await BOT.wait_until_ready()

@BOT.event
async def on_ready():
    print(f'Logged in as {BOT.user.name}')
    check_live.start()

BOT.run(TOKEN)