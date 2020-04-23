from discord.ext import commands


class ONUW(commands.Cog):
    pass


def setup(bot):
    bot.add_cog(ONUW(bot))
