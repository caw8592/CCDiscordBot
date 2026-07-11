# youtube_commands.py
import re
import asyncio
import traceback
import discord
from urllib.parse import urlparse, parse_qs

YT_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+", re.I)
SPOTIFY_TRACK_RE = re.compile(r"^https?://open\.spotify\.com/track/([A-Za-z0-9]+)", re.I)

class MusicState:
    def __init__(self):
        self.song_queue = []
        self.queue_task = None
        self.current_vc = None
        self.playlist_enqueue_task = None
        self.stop_flag = False

_state = MusicState()

# =============================================================================
# 
# FUNCTIONS CALLED BY COMMANDS
#
# =============================================================================

async def play(message: discord.Message):
    if not message.guild:
        return

    content = (message.content or "").strip()

    if not message.author.voice or not message.author.voice.channel:
        return await message.channel.send("join a voice channel first dumbass")

    url = content.split(maxsplit=1)[1].strip()

    is_yt = YT_REGEX.search(url) is not None
    is_spotify = SPOTIFY_TRACK_RE.search(url) is not None

    if is_spotify:
        return await message.channel.send("spotify is a lil bich, so i dont support it. use youtube")
    if not is_yt:
        return await message.channel.send("only youtube dumbass")
    
    # enqueue
    kind = classify_yt_url(url)

    if kind == "video":
        # single video (your existing behavior)
        await _enqueue_one(url, message)
    else:
        await message.channel.send("queueing your dumbass playlist")
        # playlist: enqueue first item now, rest in background
        entries = _iter_yt_playlist_entries(url)  # async generator
        try:
            first_url = await anext(entries)
        except StopAsyncIteration:
            return await message.channel.send("why tf u give me an empty playlist?")

        await _enqueue_one(first_url, message)
        _state.playlist_enqueue_task = asyncio.create_task(_enqueue_rest(entries, message))

    # start player loop if needed
    task = _state.queue_task
    if task is None or task.done():
        _state.queue_task = asyncio.create_task(_player_loop(message))


async def skip_song(message: discord.Message):
    if not message.guild:
        return
    vc = _get_vc(message)
    if not vc and len(_state.song_queue) == 0:
        return await message.channel.send("theres nothing in queue dumbass")
    _state.current_vc = vc
    if vc.is_playing():
        vc.stop()  # player loop will advance


async def stop_player(message: discord.Message):
    if not message.guild:
        return
    vc = _get_vc(message)
    global _state
    task = _state.queue_task
    if task and not task.done():
        task.cancel()
    if _state.playlist_enqueue_task and not _state.playlist_enqueue_task.done():
        _state.playlist_enqueue_task.cancel()
    if vc:
        vc.stop()
        if vc.is_connected():
            await vc.disconnect(force=True)
    _state = MusicState()
    await message.channel.send("cya assholes")

async def queue_status(message: discord.Message):
    if not message.guild:
        return
    queue = _state.song_queue
    vc = _get_vc(message)

    if not vc and not queue and not (_state.playlist_enqueue_task and not _state.playlist_enqueue_task.done()):
        return await message.channel.send("theres nothing in queue")
    
    is_queueing = bool(_state.playlist_enqueue_task and not _state.playlist_enqueue_task.done())
    
    if is_queueing:
        await message.channel.send(f"the queue has {len(queue)} songs and counting")
    else:
        await message.channel.send(f"the queue has {len(queue)} songs")

async def clear_queue(message: discord.Message):
    if not message.guild:
        return
    global _state
    task = _state.queue_task
    if task and not task.done():
        task.cancel()
    if _state.playlist_enqueue_task and not _state.playlist_enqueue_task.done():
        _state.playlist_enqueue_task.cancel()
    _state.song_queue.clear()
    await message.channel.send("queues gone, thank fuck")

async def pause_player(message: discord.Message):
    vc = _get_vc(message)
    if not vc or not vc.is_playing():
        return await message.channel.send("theres nothing playing dumbass")
    vc.pause()
    await message.channel.send("i needed a smoke anyway")

async def resume_player(message: discord.Message):
    vc = _get_vc(message)
    if not vc or not vc.is_paused():
        return await message.channel.send("theres nothing paused dumbass")
    vc.resume()
    await message.channel.send("god damn it, fine")

# =============================================================================
# 
# FUNCTIONS TO GET SOURCE
#
# =============================================================================

async def _get_yt_song_source(url: str, channel) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--js-runtimes", "node:/usr/bin/node",
            "-f", "bestaudio",
            "--no-playlist",
            "--print", "%(title)s|%(url)s",
            "-g", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err = (stderr.decode("utf-8", "ignore") or "yt-dlp failed").strip()
            raise RuntimeError(err)

        lines = stdout.decode("utf-8", "ignore").strip().splitlines()
        lines = [l.strip() for l in lines if l.strip()]
        if not lines:
            raise RuntimeError("No playable media URL returned.")

        title = None
        stream_url = None
        for l in lines:
            if "|" in l:
                maybe_title, _ = l.split("|", 1)
                if maybe_title:
                    title = maybe_title.strip()
            else:
                stream_url = l  # likely the -g output

        if not stream_url:
            stream_url = lines[-1]

        if not title:
            title = "Unknown title"

        return stream_url, title
    except Exception as e:
        msg = str(e)
        if "not found" in msg.lower() or "404" in msg.lower():
            await channel.send("idk wtf u gave me but aint no video there")
            raise RuntimeError("Video not found.") from e
        if "drm" in msg.lower() or "protected" in msg.lower():
            await channel.send("somthing to do with drm bullshit, cant play that")
            raise RuntimeError("That video appears to be DRM-protected.") from e
        raise

async def _iter_yt_playlist_entries(playlist_url: str):
    # yt-dlp prints one URL per line for each playlist entry
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "--js-runtimes", "node:/usr/bin/node",
        "--flat-playlist",
        "--print", "%(url)s",
        playlist_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = (stderr.decode("utf-8", "ignore") or "yt-dlp failed").strip()
        raise RuntimeError(err)

    lines = stdout.decode("utf-8", "ignore").splitlines()
    for line in lines:
        entry = line.strip()
        if entry:
            yield entry

async def _enqueue_one(entry_url: str, message: discord.Message):
    vc = message.guild.voice_client
    was_playing = message.guild.voice_client is not None and vc.is_playing()
    if was_playing:
        if len(_state.song_queue) > 1:
            await message.channel.send(f"hol' up i got {len(_state.song_queue)} songs first")
        else: 
            await message.channel.send("hol' up i got a song first")
    else:
        await message.channel.send("playing your dumbass video")
        
    src, title = await _get_yt_song_source(entry_url, message.channel)
    _state.song_queue.append((src, title))


async def _enqueue_rest(it, message):
    queued_count = 0
    try:
        async for entry_url in it:
            if _state.stop_flag:
                break
            src, title = await _get_yt_song_source(entry_url, message.channel)
            _state.song_queue.append((src, title))

            queued_count += 1
            task = _state.queue_task
            if task is None or task.done():
                _state.queue_task = asyncio.create_task(_player_loop(message))
    except asyncio.CancelledError:
        return

    await message.channel.send(f"queued {queued_count+1} videos from the playlist")

# =============================================================================
# 
# PLAYER LOOP
#
# =============================================================================

async def _player_loop(message: discord.Message):
    text_channel = message.channel

    # connect / move
    voice_channel = message.author.voice.channel
    vc = message.guild.voice_client
    if vc is None:
        vc = await voice_channel.connect()
    elif vc.channel != voice_channel:
        return await message.channel.send("im busy")
    _state.current_vc = vc

    while True:
        queue_empty = (len(_state.song_queue) == 0)
        playlist_queueing = (
            _state.playlist_enqueue_task is not None and not _state.playlist_enqueue_task.done()
        )

        if queue_empty and not playlist_queueing:
            vc = _state.current_vc
            if vc and vc.is_connected():
                await vc.disconnect(force=True)
                await message.channel.send("im done playing songs, dont call me again")
            return

        queue = _state.song_queue
        try:
            item = queue.pop(0)
            ffmpeg_source, title = item
            ffmpeg_before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            source = discord.FFmpegPCMAudio(ffmpeg_source, before_options=ffmpeg_before, options="-vn")

            if vc.is_playing():
                vc.stop()

            vc.play(source)
            await text_channel.send(f"now playing: {title}")

            while vc.is_playing() or vc.is_paused():
                await asyncio.sleep(0.2)  

        except Exception as e:
            await text_channel.send(f"i dont like that song, im not playing it")
            traceback.print_stack()
            print(f"Error: {e}")
            # continue to next item


# =============================================================================
# 
# Helper Functions
#
# =============================================================================

def _get_vc(message: discord.Message) -> discord.VoiceClient | None:
    return message.guild.voice_client if message.guild else None

def classify_yt_url(url: str) -> str:
    u = url.strip()
    if not u:
        return "unknown"

    # allow bare IDs / youtu.be short links, but keep it simple/robust
    p = urlparse(u)
    host = (p.netloc or "").lower()

    # youtu.be/<id>?...  => single
    if "youtu.be" in host:
        parts = [x for x in p.path.split("/") if x]
        return "playlist" if "list=" in parse_qs(p.query) else "video"

    # youtube.com/... => check for list= first
    qs = parse_qs(p.query)
    if "list" in qs and qs["list"]:
        return "playlist"

    # also catch common playlist-style paths
    # /playlist?list=...
    if p.path.rstrip("/").endswith("/playlist"):
        return "playlist"

    # otherwise treat as single (video/channel may still be returned by your regex)
    return "video"