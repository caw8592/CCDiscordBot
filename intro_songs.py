import discord
import asyncio

async def play_intro(file, channel):
    vc = await channel.connect()

    source = discord.FFmpegPCMAudio(file)
    vc.play(source)
    while vc.is_playing():
         await asyncio.sleep(1)
    await vc.disconnect()