import discord
from discord.ext import commands
from discord.ext.commands import CommandInvokeError

from valkyrie.data import default_prefixes, custom_prefixes


class Prefixes(commands.Cog):
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def prefix(self, ctx, *, prefixes=""):
        """Sets the prefix(es) of this bot in this guild"""
        me: discord.Member = ctx.me
        try:
            await ctx.guild.me.edit(nick=me.name + f' [{", ".join(prefixes.split() or default_prefixes)}]')
        except:
            return await ctx.send("Failed! Is that prefix too long?")

        custom_prefixes.set(ctx.guild.id, prefixes.split() or default_prefixes)
        await ctx.send("Prefixes set!")


def setup(bot: commands.Bot):
    bot.add_cog(Prefixes(bot))
