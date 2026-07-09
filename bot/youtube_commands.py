# youtube_commands.py
import re
import asyncio
import discord

YTDL_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+", re.I)

_play_queues: dict[int, list[str]] = {}   # guild_id -> urls
_queue_tasks: dict[int, asyncio.Task] = {}  # guild_id -> player task
_current_vc: dict[int, discord.VoiceClient] = {}  # guild_id -> last vc used


def _get_guild_id(message: discord.Message) -> int | None:
    return message.guild.id if message.guild else None


def _get_vc(message: discord.Message) -> discord.VoiceClient | None:
    return message.guild.voice_client if message.guild else None


async def play_youtube(message: discord.Message):
    if not message.guild:
        return

    content = (message.content or "").strip()
    lower = content.lower()
    if not lower.startswith("$play "):
        return

    if not message.author.voice or not message.author.voice.channel:
        return await message.channel.send("join a voice channel first dumbass")

    guild_id = message.guild.id
    url = content.split(maxsplit=1)[1].strip()

    if not YTDL_REGEX.search(url):
        return await message.channel.send("**YOUTUBE** dumbass")

    # connect / move
    voice_channel = message.author.voice.channel
    vc = message.guild.voice_client

    was_playing = False
    if vc and vc.is_playing():
     was_playing = True

    if vc is None:
        vc = await voice_channel.connect()
    elif vc.channel != voice_channel:
        await vc.move_to(voice_channel)

    _current_vc[guild_id] = vc

    # enqueue
    _play_queues.setdefault(guild_id, []).append(url)

    # start player loop if needed
    task = _queue_tasks.get(guild_id)
    if task is None or task.done():
        _queue_tasks[guild_id] = asyncio.create_task(_player_loop(message.guild, message.channel))

    if was_playing:
        if len(_play_queues[guild_id]) > 1:
           await message.channel.send(f"hol' up i got {len(_play_queues[guild_id])} songs first")
        else: 
            await message.channel.send("hol' up i got a song first")
    else:
        await message.channel.send("playing your dumbass video")

async def skip_song(message: discord.Message):
    if not message.guild:
        return
    guild_id = message.guild.id
    vc = _get_vc(message)
    if not vc:
        return await message.channel.send("theres nothing in queue dumbass")
    _current_vc[guild_id] = vc
    if vc.is_playing():
        vc.stop()  # player loop will advance


async def stop_player(message: discord.Message):
    if not message.guild:
        return
    guild_id = message.guild.id
    vc = _get_vc(message)

    _play_queues[guild_id] = []

    task = _queue_tasks.pop(guild_id, None)
    if task and not task.done():
        task.cancel()

    if vc:
        vc.stop()
        if vc.is_connected():
            await vc.disconnect(force=True)

    _current_vc.pop(guild_id, None)
    await message.channel.send("cya assholes")


async def _player_loop(guild: discord.Guild, text_channel: discord.abc.Messageable):
    guild_id = guild.id

    async def yt_stream_url(url: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--js-runtimes", "node:/usr/bin/node",
            "-f", "bestaudio",
            "--no-playlist",
            "-g", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = (stderr.decode("utf-8", "ignore") or "yt-dlp failed").strip()
            raise RuntimeError(err)
        lines = stdout.decode("utf-8", "ignore").strip().splitlines()
        if not lines or not lines[0].strip():
            raise RuntimeError("i tried so hard, but i suck. please forgive me :(")
        return lines[0].strip()

    while True:
        queue = _play_queues.get(guild_id, [])
        if not queue:
            _queue_tasks.pop(guild_id, None)
            vc = guild.voice_client
            if vc and vc.is_connected():
               await vc.disconnect(force=True)
            return

        url = queue.pop(0)
        _play_queues[guild_id] = queue

        vc = guild.voice_client
        if vc is None:
            # cannot play without voice
            _play_queues[guild_id] = []
            _queue_tasks.pop(guild_id, None)
            return

        _current_vc[guild_id] = vc

        try:
            stream_url = await yt_stream_url(url)
            ffmpeg_before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            source = discord.FFmpegPCMAudio(stream_url, before_options=ffmpeg_before, options="-vn")

            if vc.is_playing():
                vc.stop()

            vc.play(source)

            while vc.is_playing():
                await asyncio.sleep(0.2)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            await text_channel.send(f"Playback error: {str(e)[:1800]}")
            # continue to next item
