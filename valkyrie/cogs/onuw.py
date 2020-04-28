from typing import List

import discord
from discord.ext import commands
from discord.ext.commands import Greedy

from valkyrie.cogs.onenight.lobby import Lobby, get_role
from valkyrie.cogs.onenight.role import ROLES

LOBBY: Lobby = None
LOBBY_MESSAGE: discord.Message = None


def create_lobby_message(lobby):
    return f"**Lobby** {lobby.message.id}.\n**Roles**: {', '.join(lobby.roles)}\n**Players**: " \
           f"{', '.join(list(map(lambda x: '[' + str(lobby.players.index(x) + 1) + '] ' + x.display_name, lobby.players)))} " \
           f"({len(lobby.players)}/{lobby.get_max_players()})"


def verify_roles(roles):
    return all(list(map(lambda x: get_role(x) is not None, roles)))  # TODO: use max_count


class ONUW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def create_lobby(self, ctx: commands.Context, *, roles_list: str):
        global LOBBY, LOBBY_MESSAGE
        if not LOBBY:
            roles = roles_list.split()
            if not verify_roles(roles):
                return await ctx.send("This role set is invalid!")

            LOBBY_MESSAGE = await ctx.send(f'Creating lobby with roles: {", ".join(roles)} ...')
            LOBBY = Lobby(LOBBY_MESSAGE, roles, self.bot)

            await LOBBY_MESSAGE.edit(content=create_lobby_message(LOBBY))
        else:
            await ctx.send(
                "Sorry, we currently only support one game running on the bot. If you think this is a mistake, have an admin run %destroy.")

    @commands.command(aliases=['join'])
    async def join_lobby(self, ctx: commands.Context):
        if LOBBY and await LOBBY.add_player(ctx.author):
            await ctx.send("Joined!")
            await self.edit_lobby_message(ctx)
        else:
            await ctx.send("Could not join. Is the lobby full (does it even exist)?")

    @commands.command(aliases=['leave'])
    async def leave_lobby(self, ctx: commands.Context):
        if LOBBY and await LOBBY.add_player(ctx.author):
            await ctx.send("Left!")
            await self.edit_lobby_message(ctx)
        else:
            await ctx.send(
                "Could not leave. Are you seated in the lobby (does it even exist)? Note: you cannot leave an in-progress lobby.")

    @commands.command()
    @commands.is_owner()
    async def destroy(self, ctx: commands.Context):
        global LOBBY, LOBBY_MESSAGE
        LOBBY = None
        await LOBBY_MESSAGE.delete()
        LOBBY_MESSAGE = None

    @commands.command()
    @commands.is_owner()
    async def _retrigger(self, ctx: commands.Context, members: Greedy[discord.Member]):
        global LOBBY, LOBBY_MESSAGE
        roles = "Werewolf Werewolf Seer Tanner Hunter Robber".split()
        if not verify_roles(roles):
            return await ctx.send("This role set is invalid!")

        LOBBY_MESSAGE = await ctx.send(f'Creating lobby with roles: {", ".join(roles)} ...')
        LOBBY = Lobby(LOBBY_MESSAGE, roles, self.bot)

        for i in members + [ctx.author]:
            await LOBBY.add_player(i)

    async def edit_lobby_message(self, ctx):
        if LOBBY_MESSAGE:
            await LOBBY_MESSAGE.edit(content=create_lobby_message(LOBBY))


def setup(bot):
    bot.add_cog(ONUW(bot))
