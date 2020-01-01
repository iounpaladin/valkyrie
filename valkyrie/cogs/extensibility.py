from discord.ext import commands


class Extensibility(commands.Cog):
    pass


def setup(bot: commands.Bot):
    bot.add_cog(Extensibility(bot))
