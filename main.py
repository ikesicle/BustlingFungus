import discord
from discord.ext import commands
import subprocess
import ytdata
from util import *
import song
from radio import Station
import requests
from platform import system
from os.path import isfile
import json

PATH = __file__[:-7]
YTDLP_EXEC = f"{PATH}/include/ytdlp"
OPUS_EXEC = f"{PATH}/include/libopus"
YTDLP_PLATFORMS = {
	"Linux": "yt-dlp_linux",
	"Darwin": "yt-dlp_macos"
}
YTDLP_PLATFORM_EXEC = None
description = '''A Discord bot to play Youtube Audio in VC, akin to Groovy.'''


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.messages = True
intents.voice_states = True

bot: commands.Bot = commands.Bot(command_prefix='>', description=description, intents=intents)

guilds = {}

stations: dict[str, Station] = {}

youtube = None
sf = None

async def update_np(ctx):
	cguild = extract_guild(ctx)
	if cguild.lastNP:
		try: await cguild.lastNP.delete()
		except: pass
	if cguild.allowNP and cguild.playing: cguild.lastNP = await ctx.channel.send(f"Now playing... **{cguild.playing.title}**")
	else: cguild.lastNP = None

def init_guild(_id):
	guilds[_id] = Guild(_id)
	return guilds[_id]

def play_next(guild, callback):
	if guild.playing: terminateplayback(guild)
	nextsong = guild.queue.pop(0) if len(guild.queue) > 0 else None
	if not nextsong: return
	guild.playing = nextsong
	guild.ytdl = subprocess.Popen([YTDLP_EXEC, "-f", "bestaudio/worst", "-i", nextsong.url, "-o", "-"], stdout=subprocess.PIPE)
	
	audsrc = discord.FFmpegPCMAudio(guild.ytdl.stdout, pipe=True)
	if not guild.client:
		print("Error - Guild currently has no audio client on!")
		return
	guild.client.play(audsrc, after=callback)
	# Makes special modification to player.py which allows for waiting for the first piece of audio.

def terminateplayback(guild):
	if guild.ytdl:
		guild.ytdl.kill()
		guild.ytdl.wait()
	print("YTDL terminated.")
	guild.client.stop()
	guild.ytdl = None
	guild.playing = None

def extract_guild(ctx) -> Guild:
	guild = ctx.guild.id
	cguild = guilds.get(guild, None)
	if not cguild: cguild = init_guild(guild)
	return cguild

def handle_stream_end(guild, ctx):
	if guild.looping == Loop.Single:
		guild.queue = ([guild.playing] if guild.playing else []) + guild.queue
		play_next(guild, lambda x: handle_stream_end(guild, ctx))
		return
	if guild.looping == Loop.Enabled:
		if guild.playing: guild.queue.append(guild.playing)
	play_next(guild, lambda x: handle_stream_end(guild, ctx))
	bot.loop.create_task(update_np(ctx))

@bot.event
async def on_ready():
	
	if not discord.opus.is_loaded():
		try: discord.opus.load_opus(OPUS_EXEC)
		except: raise RuntimeError(f"Tried to load Opus from {OPUS_EXEC}, but failed.")
	print(f'Logged in as {bot.user} (ID: {bot.user.id})')
	print('------')
	print('Syncing application commands...')
	await bot.tree.sync()
	print('Application commands synced!')

@bot.command()
async def play(ctx, *q):
	"""
	Searches for and plays the song [q] from Youtube, or adds it to the queue.
	"""
	voicestate = ctx.author.voice
	if not voicestate:
		await ctx.send("Author not currently in VC.")
		return
	channel = voicestate.channel
	
	cguild = extract_guild(ctx)
	if cguild.mode == AudioMode.Radio:
		await ctx.send("Bot is currently in radio mode. Call `stop`, and then try again.")
		return
	cguild.mode = AudioMode.Youtube
	if not cguild.client: cguild.client = await channel.connect()

	url = ""
	_id = ""
	
	if len(q) == 0:
		await ctx.send("Empty prompt.")
		return
	elif q[0].startswith("https://www.youtube.com/watch?v=") or q[0].startswith("https://youtu.be"):
		q = ' '.join(q)
		url = q
		_id = url[url.index("=")+1:]
	else:
		q = ' '.join(q)
		print(f"Query requested for {q}")
		_id = youtube.query(q)
		url = "https://youtube.com/watch?v=" + _id
	expected_song = sf.create(_id)
	
	await ctx.send(f"**{expected_song.title}** has been added to the queue.")
	cguild.queue.append(expected_song)
	if not cguild.playing:
		play_next(cguild, lambda x: handle_stream_end(cguild, ctx))
		await update_np(ctx)

@bot.tree.command()
async def play(intr, query: str):
	"""
	Searches for and plays the song [query] from Youtube, or adds it to the queue.
	"""
	ctx = await commands.Context.from_interaction(intr)
	voicestate = ctx.author.voice
	if not voicestate:
		await ctx.send("Author not currently in VC.")
		return
	channel = voicestate.channel
	
	cguild = extract_guild(ctx)
	if cguild.mode == AudioMode.Radio:
		await ctx.send("Bot is currently in radio mode. Call `stop`, and then try again.")
		return
	if not cguild.client: cguild.client = await channel.connect()
	cguild.mode = AudioMode.Youtube
	url = ""
	_id = ""
	
	if len(query) == 0:
		await ctx.send("Empty prompt.")
		return
	elif query.startswith("https://www.youtube.com/watch?v=") or query.startswith("https://youtu.be"):
		url = query
		_id = url[url.index("=")+1:]
	else:
		print(f"Query requested for {query}")
		_id = youtube.query(query)
		url = "https://youtube.com/watch?v=" + _id
	print(url)
	expected_song = sf.create(_id)
	print("Fetch success!")
	
	await ctx.send(f"**{expected_song.title}** has been added to the queue.")
	cguild.queue.append(expected_song)
	if not cguild.playing:
		play_next(cguild, lambda x: handle_stream_end(cguild, ctx))
		await update_np(ctx)

@bot.hybrid_command()
async def queue(ctx):
	"""
	View the current bot queue.
	"""
	cguild = extract_guild(ctx)
	ret = f"Currently in queue... ({len(cguild.queue)})"
	index = 1
	for i in cguild.queue: 
		ret += f"\n{index}: **{i.title}** by **{i.channelname}**"
		index += 1
	await ctx.send(ret)

@bot.hybrid_command()
async def skip(ctx):
	"""
	Skip the currently playing song.
	"""
	cguild = extract_guild(ctx)
	if cguild.playing:
		await ctx.send(f"Skipping **{cguild.playing.title}**...")
		if cguild.looping == Loop.Enabled:
			print("Adding a new song on stream end")
			cguild.queue.append(cguild.playing)
		terminateplayback(cguild)
	else:
		await ctx.send("I'm not even playing anything!")

@bot.hybrid_command()
async def loop(ctx, state):
	"""
	Set looping state. Valid parameters are (none/all/one) or similar terms.
	"""
	cguild = extract_guild(ctx)
	state = state.lower()
	if state in ("0", "off", "disable", "none"): 
		cguild.looping = Loop.Disabled
		await ctx.send("Looping is now disabled")
	elif state in ("1", "on", "all", "queue"): 
		cguild.looping = Loop.Enabled
		await ctx.send("Looping is now enabled for the queue.")
	elif state in ("2", "one", "single"): 
		cguild.looping = Loop.Single
		await ctx.send("Looping is now enabled for the current song.")
	else:
		await ctx.send("Invalid Parameter. Use (none/all/one)")

@bot.hybrid_command(aliases=("nowplaying", "current"))
async def np(ctx):
	"""
	Get the currently playing song.
	"""
	cguild = extract_guild(ctx)
	if (cguild.playing):
		if cguild.mode == AudioMode.Radio:
			await cguild.playing.send_embed(ctx)
			return
		emb = discord.Embed(
			colour=discord.Colour.green(),
			title=cguild.playing.title,
			description="By " + cguild.playing.channelname,
			url=cguild.playing.url
		)
		emb.set_image(url = cguild.playing.thumburl)
		await ctx.send(embed=emb)
		return
	await ctx.send("I'm not playing anything!!!")

@bot.hybrid_command(aliases=("dc", "disconnect"))
async def stop(ctx):
	"""
	Stop playback and leave the channel.
	"""
	cguild = extract_guild(ctx)
	print("Trying to execute stop function...")
	cguild.playing = None
	terminateplayback(cguild)
	if cguild.client: await cguild.client.disconnect()
	cguild.client = None
	cguild.queue = []
	cguild.looping = Loop.Disabled
	cguild.mode = AudioMode.Idle
	await ctx.send("Disconnected active client(s) and stopped playback.")

@bot.hybrid_command(aliases=("rm", "del"))
async def remove(ctx, index: int):
	"""
	Remove the song at index [index].
	"""
	cguild = extract_guild(ctx)
	try: index = int(index)
	except:
		await ctx.send("Invalid index number!")
		return
	if index > len(cguild.queue) or index < 1:
		if len(cguild.queue) == 0: await ctx.send(f"There's nothing in the queue to remove!")
		else: await ctx.send(f"Invalid index! Value must be between **1** and **{len(cguild.queue)}**")
	removed = cguild.queue.pop(index-1)
	await ctx.send(f"Removed **{removed.title}** at position **{index}**.")

@bot.hybrid_command(aliases=("insert",))
async def move(ctx, frm: int, to: int):
	"""
	Move from index [frm] to [to].
	"""
	cguild = extract_guild(ctx)
	if frm > len(cguild.queue) or frm < 1:
		if len(cguild.queue) == 0: await ctx.send(f"There's nothing in the queue to move!")
		else: await ctx.send(f"Invalid index! Value must be between **1** and **{len(cguild.queue)}**")
	to = max(1, min(to, len(cguild.queue)))
	moving = cguild.queue.pop(frm-1)
	# [ 1 2 3 4 5 ] 4 -> 2
	# [ 1 2 3 5 ]
	# [ 1 2 3 4 5 ]
	cguild.queue.insert(to-1, moving)
	await ctx.send(f"Moved **{moving.title}** from position **{frm}** to **{to}**.")

@bot.hybrid_command()
async def skipto(ctx, to: int):
	"""
	Skip to the song playing at the target index.
	"""
	cguild = extract_guild(ctx)
	try: to = int(to)
	except:
		await ctx.send("Invalid index number!")
		return
	if to > len(cguild.queue) or to < 1:
		if len(cguild.queue) == 0: await ctx.send(f"There's nothing to skip to!")
		else: await ctx.send(f"Invalid index! Value must be between **1** and **{len(cguild.queue)}**")
		return
	removed = cguild.queue[:to-1]
	cguild.queue = cguild.queue[to-1:]
	await ctx.send(f"Skipped over **{len(removed)+1}** song(s).")
	if cguild.looping == Loop.Enabled:
		cguild.queue.append(cguild.playing)
		cguild.queue += removed
	terminateplayback(cguild)

@bot.hybrid_command()
async def silence(ctx):
	"""
	Silences track updates for the current guild.
	"""
	cguild = extract_guild(ctx)
	cguild.allowNP = not cguild.allowNP
	await ctx.send(f"Track updates are now **{'silenced' if not cguild.allowNP else 'unsilenced'}**.\nUse `silence` again to {'unsilence' if not cguild.allowNP else 'silence'}.")
	
@bot.hybrid_command()
async def radio(ctx, station: str):
	guild = extract_guild(ctx)
	if guild.mode == AudioMode.Youtube:
		await ctx.send("Bot is currently in Youtube mode. Call `stop`, then try this command again.")
		return
	guild.mode = AudioMode.Radio
	voicestate = ctx.author.voice
	if not voicestate:
		await ctx.send("Author not currently in VC.")
		return
	if station not in stations:
		retstr = "Invalid station! Valid stations are..."
		for st in stations.keys(): retstr += f"\n- **{st}**: {stations[st].name}"
		await ctx.send(retstr)
		return
	staobj = stations[station]
	channel = voicestate.channel
	if not guild.client: guild.client = await channel.connect()
	if guild.playing: terminateplayback(guild)
	audsrc = discord.FFmpegPCMAudio(staobj.url)
	guild.playing = staobj
	guild.client.play(audsrc)
	await ctx.send(f"Now playing... **{staobj.name}**")


if __name__ == "__main__":
	if system() in YTDLP_PLATFORMS:
		YTDLP_PLATFORM_EXEC = YTDLP_PLATFORMS[system()]
		print(f"Platform configured to {system()}")
	else:
		print(f"Error: System {system()} not supported.")
		quit()
	
	if not isfile(f"{PATH}/config.json"): raise FileNotFoundError("Required config file \"config.json\" does not exist.")
	with open(f"{PATH}/config.json", "r") as configfile:
		try: configjson = json.loads(configfile.read())
		except: raise RuntimeError("Loaded configuration file contained invalid JSON.")
		if "token" not in configjson: raise KeyError(f"Required bot token entry \"token\" not found in config.json.")
		token = configjson["token"]
		if "servicefile" not in configjson:raise KeyError(f"Required service file path entry \"servicefile\" not found in config.json.")
		if not isfile(f"{PATH}/{configjson['servicefile']}"): raise FileNotFoundError(f"Specified service file \"{configjson['servicefile']}\" does not exist.")
		youtube = ytdata.YoutubeQuerier(f"{PATH}/{configjson['servicefile']}")
		sf = song.SongDataFactory(youtube.client.videos())

	
	if not isfile(f"{PATH}/stations.json"): print("Warning: stations.json does not exist. No stations will be added.")
	with open(f"{PATH}/stations.json", "r") as stationsfile:
		stationsjson: dict = json.loads(stationsfile.read())
		for _id in stationsjson:
			try: stations[_id] = Station(stationsjson[_id]["name"], stationsjson[_id]["url"])
			except Exception: print(f"Warning: Malformed station entry for {_id}, ignoring.")
		print(f"Loaded {len(stations)} custom stations.")

	ytdlpversion: requests.Response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
	if (ytdlpversion.status_code == 200):
		ytdlpversion: dict = ytdlpversion.json()
		print(f"Latest YTDLP version is [ {ytdlpversion['name']} ]")
		found: bool = False
		for asset in ytdlpversion["assets"]:
			if asset["name"] == YTDLP_PLATFORM_EXEC:
				if subprocess.run(["curl", "-L", "-o", YTDLP_EXEC, asset['browser_download_url']], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL).returncode == 0:
					print("YTDLP updated.")
				else: 
					print("Error: An unknown problem occurred while trying to download the latest executable.")
					print("Warning: Unable to fetch the latest YTDLP release, defaulting to previously downloaded version.")
				found = True
				break
		if not found:
			print(f"Error: Unable to find the desired release executable [ {YTDLP_PLATFORM_EXEC} ] in the latest YTDLP releases.")
			print("Warning: Unable to fetch the latest YTDLP release, defaulting to previously downloaded version.")
	else:
		print("Warning: Unable to fetch the latest YTDLP release, defaulting to previously downloaded version.")
	
	bot.run(token)
