# Livestream Notifier: Discord Bot
## Description
A Discord bot written in Python for notifying your server whenever your favourite streamers go live.  
Commands are explained in the [Commands](#discord--commands) section, and can be seen with a brief explanation during runtime by typing `/help` in the chat of the server it is in.

## Setup
Download and extract the latest release, or clone this repository in the root folder of your installation of Unreal Tournament with the following command:

    git clone https://github.com/DreWulff/LivestreamNotifier-DiscordBot

Make sure all libraries/modules required are installed.

Create a `.env` file with the next line, replacing the values in brackets:

    DISCORD_TOKEN=[Token from your Discord bot]

To obtain the token you must first have a Discord app/bot. To get started I would recommend to follow the official Discord Developer Portal documentation in [Building your first Discord app](https://discord.com/developers/docs/quick-start/getting-started).

## Run
On the **first run** make sure to run the following command to initialize the database:

    python database.py

Afterwards all subsequent executions of the bot only require this command:

    python bot.py
  
## Docker Setup
It is highly recommended to run the app in Docker, as to avoid conflicts with different installed versions of Python and its modules.  
The container is setup to install a lightweight base image capable of running Python 3, alongside any needed modules required.

To setup and run a Docker container with the app execute the next commands:  
* `build`: This command prepares a container of name `livestream-notifier`, downloading its required images and resources, and copying the app's files into the container following the sequence defined in the `Dockerfile`.
```
docker build -t livestream-notifier .
```
* `run`: This command runs the `livestream-notifier` container.
```
docker run -d file-download-server
```

## Discord `/` Commands
* `/add [platform] [channel]`:
  * Registers a livestream `channel` in the specified `platform` for future notification.
  * The bot will periodically check if the streamer is live, and notify through a text channel.
  * Users can subscribe to the `channel` to get mentioned when stream goes live.
* `/remove [channel]`:
  * Removes a registered channel and all subscriptions to that `channel`.
* `/setchannel [channel]`:
  * Sets the current text channel as the medium of notification for specified `channel`.
* `/subscribe [channel]`:
  * Registers the user to be mentioned when `channel` goes live.
* `/unsubscribe [channel]`:
  * Removes subscription to specified `channel`.
* `/channels [platform]`:
  * Lists all registered channels from specified `platform` and their current status.
* `/mentions [channel]`:
  * Changes the notification mode of the channel between mentioning everyone connected (`@here`) or subscribers only.
* `/help`:
  * Shows the user a list of all of this bot's commands.

## Notes
* The bot checks the HTML of each channel on a **5[minute] period** to identify if the channel is live or not.

## ToDo
* Add administrator role verification for `/add`, `/remove`, `/mentions` and `/setchannel` commands.