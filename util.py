from enum import Enum
from shutil import which
import subprocess
import discord
import song
from typing import Union
import radio



class Guild:
    """Represents a guild with music support"""
    def __init__(self, id):
        self.id = id
        self.mode = AudioMode.Idle
        self.playing: Union[song.Song, radio.Station] = None
        self.client: discord.VoiceClient = None
        self.queue: list[song.Song] = []
        self.looping = Loop.Disabled
        self.ytdl: subprocess.Popen = None
        self.lastNP = None
        self.allowNP = True

class Loop(Enum):
    Disabled = 0
    Enabled = 1
    Single = 2

class AudioMode(Enum):
    Idle = 0
    Youtube = 1
    Radio = 2
    

def is_tool(name): return which(name) is not None