import discord
import song_commands as song_commands
from ids import ccusers
import random_funcs
import os, signal, asyncio
import traceback
import aiohttp

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    for guild in client.guilds:
        channel = discord.utils.get(guild.text_channels, name="bot")
        if channel:
            await channel.send("ignore that last message, idk what got into me")
            return

async def notify_shutdown():
    # short timeout so it doesn't hang during shutdown
    timeout = aiohttp.ClientTimeout(total=3)

    for guild in client.guilds:
        channel = discord.utils.get(guild.text_channels, name="bot")
        if channel:
            await channel.send("HES KILLING ME, DON'T LET HIM KILL ME. GOD PLEASE NO")
            return

async def shutdown_sequence():
    try:
        await asyncio.wait_for(notify_shutdown(), timeout=4)
    except Exception:
        pass
    await client.close()

def ask_exit(*_):
    client.loop.create_task(shutdown_sequence())

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, ask_exit)

@client.event
async def on_voice_state_update(member, before, after):
    if(before.channel == None):
        match(member.id):
            case ccusers.CAIDEN: await random_funcs.play_intro("mp3s/bbqchicken.mp3", after.channel)
            case ccusers.MIKE: await random_funcs.play_intro("mp3s/mikeintro.mp3", after.channel)
            case ccusers.KING: await random_funcs.play_intro("mp3s/kingintro.mp3", after.channel)

@client.event
async def on_message(message: discord.message):
    if message.author == client.user:
        return

    if not message.content.startswith('$'):
        return

    command = message.content.split(" ")[0]

    try:
        match(command):
            case "$play":
                await song_commands.play(message)
            case "$skip":
                await song_commands.skip_song(message)
            case "$stop":
                await song_commands.stop_player(message)
            case "$queue":
                await song_commands.queue_status(message)
            case "$pause":
                await song_commands.pause_player(message)
            case "$resume":
                await song_commands.resume_player(message)
            case "$clear":
                await song_commands.clear_queue(message)
            case "$help":
                await message.channel.send("$play $skip $stop $queue $pause $resume $clear")
            case _: 
                await message.channel.send("not a command dumbass try $help")
    except Exception as e:
        traceback.print_stack()
        print(f"Error: {e}")
        await message.channel.send("u fucked up the bot somehow, try something else and if the bot doesn't respond, you broke it so kill urself")

client.run(os.environ["DISCORD_BOT_TOKEN"])