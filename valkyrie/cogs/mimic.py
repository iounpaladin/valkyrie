import discord
import markovify
from discord.ext import commands

from valkyrie.datastore import Datastore


class Mimic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chains = Datastore("mimic.pkl")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        id = message.author.id

        if self.chains.get(id):
            self.chains.set(id,
                            markovify.combine([markovify.NewlineText(message.content, retain_original=False, well_formed=False),
                                               markovify.NewlineText.from_json(self.chains.get(id))]).to_json()
                            )
        else:
            self.chains.set(id, markovify.NewlineText(message.content, retain_original=False, well_formed=False).to_json())

    @commands.command()
    async def mimic(self, ctx: commands.Context, user: discord.User, nsentences: int = 1):
        if self.chains.get(user.id):
            chain = markovify.Text.from_json(self.chains.get(user.id))
            return await ctx.send('. '.join([chain.make_sentence() for x in range(nsentences)]) + '.')
        else:
            return await ctx.send(f"No information on {user.display_name}. "
                                  f"In order to mimc a user, I must have seen them chat at least once.")


def setup(bot):
    bot.add_cog(Mimic(bot))
