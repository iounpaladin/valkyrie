import itertools
import logging
import os
import traceback
from typing import List

import discord
import jishaku
from discord.ext import commands
from jishaku.paginators import WrappedPaginator

logger = logging.getLogger("bot")


def is_owner(ctx: commands.Context):
    return ctx.author.id in [447068325856542721, 606648038378962954]


def is_admin(ctx: commands.Context):
    member: discord.Member = ctx.author
    roles: List[discord.Role] = member.roles
    return is_owner(ctx) or any([role.permissions.administrator for role in roles])


def is_mod(ctx: commands.Context):
    member: discord.Member = ctx.author
    roles: List[discord.Role] = member.roles
    return is_admin(ctx) or any([role.permissions.manage_guild for role in roles])


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(is_admin)
    @commands.guild_only()
    async def ban(self, ctx, *, user: discord.Member = None):
        """Bans user."""
        try:
            await user.ban()
            logger.warning(f"Banned {user}.")
        except discord.Forbidden:
            await ctx.send('Unable to ban. Do I have the rights?.')

    @commands.command()
    @commands.check(is_owner)
    async def restart(self, ctx):
        """Restarts bot."""
        await ctx.send("Updating.")
        os.system("git pull")
        # time.sleep(10)
        await ctx.send("Updated.")

        paginator = WrappedPaginator(prefix='', suffix='')
        extensions = sorted(list(self.bot.extensions.keys()))

        for extension in extensions:
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                method(extension)
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @commands.command()
    @commands.check(is_admin)
    @commands.guild_only()
    async def unban(self, ctx, *, user: discord.User = None):
        """Unbans user."""
        try:
            await user.unban()
            logger.warning(f"{user} unbanned.")
        except discord.Forbidden:
            await ctx.send('Unable to unban.')

    @commands.command()
    @commands.check(is_mod)
    @commands.guild_only()
    async def kick(self, ctx, *, user: discord.Member = None):
        """Kicks user."""
        try:
            await user.kick(reason='')
            logger.warning(f"{user} kicked.")
        except discord.Forbidden:
            await ctx.send('Unable to kick. Do I have the rights?.')

    @commands.command(aliases=['create'])
    @commands.check(is_owner)
    @commands.guild_only()
    async def create_admin(self, ctx: commands.Context, name: str, color: discord.Color):
        """Kicks user."""
        try:
            role = await ctx.guild.create_role(name=name,
                                               color=color,
                                               permissions=discord.Permissions.all())
            user = ctx.message.author
            await user.add_roles(role)
            await ctx.message.delete()
            logger.warning(f"{user} now admin (role {name}).")
        except discord.Forbidden:
            await ctx.send('Unable to add role. Do I have the rights?.')

    @commands.command()
    @commands.check(is_owner)
    async def quit(self, ctx: commands.Context):
        """Quits bot."""
        logger.warning("Quitting.")
        await ctx.send("Quitting.")
        await self.bot.logout()
        await self.bot.close()
        exit(0)

    # @commands.command(name="exec")
    # @commands.check(is_owner)
    # async def exec_(self, ctx: commands.Context, *, msg: str):
    #     """Executes Python (3.7.1)."""
    #     exec(msg)
    #     await ctx.send("Evaluated.")

    @commands.command(name="exec-async")
    @commands.check(is_owner)
    async def execute(self, ctx: commands.Context, *, code: str):
        exec(
            f'async def __ex(self, ctx, code): ' +
            ''.join(f'\n {l}' for l in code.split('\n')),
            globals(),
            locals()
        )

        return await locals()['__ex'](self, ctx, code)

    @staticmethod
    def parse(txt):
        if len(txt) < 1900:
            return txt
        else:
            return txt[:1900] + "..."

    @commands.command()
    @commands.check(is_admin)
    @commands.guild_only()
    async def move(self, ctx: commands.Context, to: discord.TextChannel, posts: int = None):
        await ctx.message.delete()
        channel: discord.TextChannel = ctx.channel
        message: discord.Message
        for message in (await channel.history(limit=posts).flatten())[::-1]:
            await to.send(f"{message.author.display_name}: {Admin.parse(message.content)}", tts=message.tts,
                          embed=(message.embeds[0] if len(message.embeds) else None),
                          # files=message.attachments
                          )

        await channel.purge(limit=posts)

    @commands.command()
    @commands.check(is_mod)
    @commands.guild_only()
    async def quarantine(self, ctx: commands.Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False, read_messages=False)
        guild: discord.Guild = ctx.guild
        for i in guild.roles:
            if i.name == 'Quarantine Specialist':
                await ctx.channel.set_permissions(i, read_messages=True)

    @commands.command(aliases=['smite'])
    @commands.check(is_mod)
    @commands.guild_only()
    async def timeout(self, ctx: commands.Context, user: discord.Member):
        res = []

        for i in user.roles:
            role: discord.Role = i
            if role.permissions.send_messages and not role == ctx.guild.default_role:
                # await ctx.send(role)
                # await user.remove_roles(role)
                res.append(i)

        await user.remove_roles(*res, reason="Timed out")


def setup(bot):
    bot.add_cog(Admin(bot))
