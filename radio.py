import discord
class Station:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.shorthand = name.split(" ")[0].lower()
    async def send_embed(self, ctx):
        filename = f"{self.shorthand}.png"
        thumbimage = discord.File(f"image/{filename}", filename )
        ret = discord.Embed(
			colour=discord.Colour.green(),
			title=self.name
		)
        ret.set_image(url=f"attachment://{filename}")
        await ctx.send(file=thumbimage, embed=ret)