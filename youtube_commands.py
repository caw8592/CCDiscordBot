import discord
import yt_dlp
import asyncio

queue = []
skip = False
stop = False

async def play_youtube(message: discord.message):
     url = message.content.split(" ")[1]
     
     if(check_queue_empty()):
          await message.channel.send("playing ur dumbass video")
     else:
          await message.channel.send("queuing ur dumbass video")

     ydl_opts = {
          'format': 'bestaudio/best',
          'quiet': True,
     }

     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
          info = ydl.extract_info(url, download=False)
          audio_url = info['url']

     if(check_queue_empty()):
          add_queue(audio_url)
          channel = message.author.voice.channel
          vc = await channel.connect()
          await play_queue(vc, message.channel)
     else:
          add_queue(audio_url)

def check_queue_empty():
     return len(queue) == 0

def add_queue(audio_url):
     queue.append(audio_url)

def remove_song():
     queue.pop(0)

async def play_queue(vc, message_channel):
     global skip
     global stop
     while(len(queue) > 0):
          ffmpeg_options = {'options': '-vn'}
          vc.play(discord.FFmpegPCMAudio(queue[0], **ffmpeg_options))
          while vc.is_playing():
               if(stop):
                    stop = False
                    vc.stop()
                    await vc.disconnect()
                    return
               if(skip):
                    skip = False
                    vc.stop()
                    break
               await asyncio.sleep(1)
          remove_song()
          await message_channel.send("playing ur next dumbass video")
     await vc.disconnect()

def skip_song():
     global skip 
     skip = True     

def stop_player():
     global stop 
     stop = True