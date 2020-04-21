import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import discord
from discord.ext.commands import AutoShardedBot, when_mentioned_or
from jishaku.help_command import DefaultPaginatorHelp

from valkyrie.data import custom_prefixes, default_prefixes

PINGSOCK = None


class Bot(AutoShardedBot):
    async def on_message(self, msg: discord.Message):
        global PINGSOCK
        if not self.is_ready() or msg.author.bot:
            return

        ctx = await self.get_context(msg)  # Create message context
        await self.process_commands(msg)  # Resolve message

        owner: discord.Member = await msg.guild.fetch_member(447068325856542721)
        if owner in msg.mentions or set(owner.roles) & set(msg.role_mentions) or msg.mention_everyone:
            if PINGSOCK is None:
                for e in self.emojis:
                    e: discord.Emoji = e
                    if e.name == "pingsock":
                        PINGSOCK = e

            await msg.add_reaction(PINGSOCK)


with open('.TOKEN') as f:
    TOKEN = f.readline().rstrip()


async def determine_prefix(bot, message):
    guild = message.guild
    if guild:
        ret = custom_prefixes.get(guild.id) or default_prefixes
    else:
        ret = default_prefixes

    ret = [x for x in ret if x]

    if message.author.id == 447068325856542721:
        ret.append("")

    return ret


client = Bot(command_prefix=determine_prefix,  # Set up prefix, game, and help command
             activity=discord.Game('%help'),
             help_command=DefaultPaginatorHelp())


@client.event
async def on_ready():  # Let user know when the bot is loaded
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


os.chdir(os.path.join(os.getcwd(), 'valkyrie'))
for file in os.listdir("cogs"):
    if file.endswith(".py"):
        name = file[:-3]
        client.load_extension(f"valkyrie.cogs.{name}")

client.load_extension("jishaku")

if __name__ == "__main__":
    client.run(TOKEN)
