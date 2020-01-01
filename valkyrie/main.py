import os

import discord
from discord.ext.commands import AutoShardedBot, when_mentioned_or
from jishaku.help_command import DefaultPaginatorHelp

from valkyrie.data import custom_prefixes, default_prefixes
from valkyrie.datastore import Datastore


class Bot(AutoShardedBot):
    async def on_message(self, msg: discord.Message):
        if not self.is_ready() or msg.author.bot:
            return

        ctx = await self.get_context(msg)  # Create message context
        await self.process_commands(msg)  # Resolve message


with open('../.TOKEN') as f:
    TOKEN = f.read().rstrip()


async def determine_prefix(bot, message):
    guild = message.guild
    if guild:
        return custom_prefixes.get(guild.id) or default_prefixes
    else:
        return default_prefixes

client = Bot(command_prefix=determine_prefix,  # Set up prefix, game, and help command
             activity=discord.Game('%help'),
             help_command=DefaultPaginatorHelp())


@client.event
async def on_ready():  # Let user know when the bot is loaded
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


for file in os.listdir("cogs"):
    if file.endswith(".py"):
        name = file[:-3]
        client.load_extension(f"cogs.{name}")

client.load_extension("jishaku")

client.run(TOKEN)
