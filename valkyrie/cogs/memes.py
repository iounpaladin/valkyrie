import requests
from discord.ext import commands


class Memes(commands.Cog):
    @commands.command()
    async def inspire(self, ctx):
        await ctx.send(requests.get("https://inspirobot.me/api?generate=true").content.decode('utf-8'))


def setup(bot):
    bot.add_cog(Memes(bot))
