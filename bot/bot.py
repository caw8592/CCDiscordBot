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
            case "$error":
                raise Exception("the dumbasses are calling")
            case "$help":
                await message.channel.send("$play $skip $stop $queue $pause $resume $clear")
            case _: 
                await message.channel.send("not a command dumbass try $help")
    except Exception as e:
        traceback.print_stack()
        print(f"Error: {e}")
        await message.channel.send("u fucked up, im telling")
        await message.channel.send(f"<@{ccusers.CAIDEN}> they broke me")

client.run(os.environ["TOKEN"])