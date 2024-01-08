class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
class Song:
	
	def __init__(self, sid, vid):
		self.id = sid;
		snippet = dotdict(((vid.list(
			part = "snippet",
			id = self.id
		)).execute())["items"][0]["snippet"])
		self.title = snippet.title
		self.description = snippet.description
		self.thumburl = snippet.thumbnails.get("standard", {"url": ""})["url"]
		self.channelname = snippet.channelTitle
		self.url = "https://www.youtube.com/watch?v=" + self.id

class SongDataFactory:
	def __init__(self, vid):
		self.vid = vid

	def create(self, sid):
		return Song(sid, self.vid)
