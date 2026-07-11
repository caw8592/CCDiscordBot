import discord
import youtube_commands
from ids import ccusers
import random_funcs
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

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
    match(command):
        case "$play":
            await youtube_commands.play_youtube(message)
        case "$skip":
            await youtube_commands.skip_song(message)
        case "$stop":
            await youtube_commands.stop_player(message)

        case _: await message.channel.send("not a command dumbass")

client.run(os.environ["DISCORD_BOT_TOKEN"])