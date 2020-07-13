from typing import List, Dict

import discord
from discord.ext import commands
from discord.ext.commands import Greedy

from valkyrie.cogs.onenight.lobby import Lobby, get_role
from valkyrie.cogs.onenight.role import ROLES

CHANNEL_TO_LOBBY: Dict[int, Lobby] = {

}


def create_lobby_message(lobby):
    return f"**Lobby** {lobby.message.id}.\n**Roles**: {', '.join(lobby.roles)}\n**Players**: " \
           f"{', '.join(list(map(lambda x: '[' + str(lobby.players.index(x) + 1) + '] ' + x.display_name, lobby.players)))} " \
           f"({len(lobby.players)}/{lobby.get_max_players()})"


def verify_roles(roles):
    return all(list(map(lambda x: get_role(x) is not None, roles))) and len(roles) > 5  # TODO: use max_count


class ONUW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def create_lobby(self, ctx: commands.Context, *, roles_list: str):
        global CHANNEL_TO_LOBBY

        lobby = CHANNEL_TO_LOBBY.get(ctx.channel.id)

        if lobby and lobby.completed:
            await self.destroy_lobby(ctx)

        if not lobby:
            roles = roles_list.split()
            if not verify_roles(roles):
                return await ctx.send("This role set is invalid!")

            message = await ctx.send(f'Creating lobby with roles: {", ".join(roles)} ...')
            lobby = Lobby(message, roles, self.bot)
            CHANNEL_TO_LOBBY[ctx.channel.id] = lobby

            await message.edit(content=create_lobby_message(lobby))
        else:
            await ctx.send(
                "Sorry, we currently only support one game per channel running. If you think this is a mistake, "
                "have your server owner run %destroy in this channel.")

    @commands.command(aliases=['join'])
    async def join_lobby(self, ctx: commands.Context):
        lobby = CHANNEL_TO_LOBBY.get(ctx.channel.id)
        if lobby and await lobby.add_player(ctx.author):
            await ctx.send("Joined!")
            await self.edit_lobby_message(ctx)
            await lobby.check_start()
        else:
            await ctx.send("Could not join. Is the lobby full (does it even exist)?")

    @commands.command(aliases=['leave'])
    async def leave_lobby(self, ctx: commands.Context):
        lobby = CHANNEL_TO_LOBBY.get(ctx.channel.id)
        if lobby and await lobby.remove_player(ctx.author):
            await ctx.send("Left!")
            await self.edit_lobby_message(ctx)
            if len(lobby.players) == 0:
                await self.destroy_lobby(ctx)
        else:
            await ctx.send(
                "Could not leave. Are you seated in the lobby (does it even exist)? "
                "Note: you cannot leave an in-progress lobby.")

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def destroy(self, ctx: commands.Context):
        await self.destroy_lobby(ctx)

    @commands.command()
    @commands.is_owner()
    async def _retrigger(self, ctx: commands.Context, members: Greedy[discord.Member]):
        global CHANNEL_TO_LOBBY
        roles = "Hunter Hunter Hunter Hunter Hunter Hunter".split()  # edit this to whatever role set you wanna test
        if not verify_roles(roles):
            return await ctx.send("This role set is invalid!")

        message = await ctx.send(f'Creating lobby with roles: {", ".join(roles)} ...')
        lobby = Lobby(message, roles, self.bot)
        CHANNEL_TO_LOBBY[ctx.channel.id] = lobby

        for i in members + [ctx.author]:
            await lobby.add_player(i)

        await lobby.check_start()

    async def edit_lobby_message(self, ctx):
        lobby = CHANNEL_TO_LOBBY.get(ctx.channel.id)
        message = lobby.message

        if message:
            await message.edit(content=create_lobby_message(lobby))

    async def destroy_lobby(self, ctx):
        global CHANNEL_TO_LOBBY
        lobby = CHANNEL_TO_LOBBY[ctx.channel.id]
        lobby.cancel()
        await lobby.message.delete()
        del CHANNEL_TO_LOBBY[ctx.channel.id]


def setup(bot):
    bot.add_cog(ONUW(bot))
