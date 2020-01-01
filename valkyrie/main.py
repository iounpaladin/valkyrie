import os

import discord
from discord.ext.commands import AutoShardedBot, when_mentioned_or
from jishaku.help_command import DefaultPaginatorHelp


class Bot(AutoShardedBot):
    async def on_message(self, msg: discord.Message):
        if not self.is_ready() or msg.author.bot:
            return

        ctx = await self.get_context(msg)  # Create message context
        await self.process_commands(msg)  # Resolve message


with open('../.TOKEN') as f:
    TOKEN = f.read().rstrip()

client = Bot(command_prefix=when_mentioned_or('%'),  # Set up prefix, game, and help command
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
