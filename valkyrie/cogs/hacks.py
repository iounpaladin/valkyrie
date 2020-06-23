import discord
from discord.ext import commands
import jishaku.paginators as pag


class Hacks(commands.Cog):
    @commands.command(aliases=["read", "history"])
    @commands.is_owner()
    async def read_channel(self, ctx: commands.Context, guild: int, channel: int, limit: int = 10):
        guild: discord.Guild = discord.utils.get(ctx.bot.guilds, id=guild)
        channel = discord.utils.get(await guild.fetch_channels(), id=channel)
        paginator = commands.Paginator(max_size=1985)

        async for x in channel.history(limit=limit):
            paginator.add_line(f"\t{x.author.display_name} at {x.created_at}:")
            paginator.add_line(x.content)
            # TODO: embeds?

        paginator = pag.PaginatorEmbedInterface(ctx.bot, paginator, owner=ctx.author)
        await paginator.send_to(ctx.channel)

    @commands.command()
    @commands.is_owner()
    async def read_guild(self, ctx: commands.Context, *, guild: int):
        guild = discord.utils.get(ctx.bot.guilds, id=guild)
        paginator = commands.Paginator(max_size=1985)

        for x in guild.categories:
            paginator.add_line(f"{x.name} ({x.id})")
            for j in x.text_channels:
                paginator.add_line(f"|____ {j.name} ({j.id})")

        paginator = pag.PaginatorEmbedInterface(ctx.bot, paginator, owner=ctx.author)
        await paginator.send_to(ctx.channel)


def setup(bot):
    bot.add_cog(Hacks(bot))
