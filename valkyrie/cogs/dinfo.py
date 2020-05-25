import inspect
import requests
import os
from io import BytesIO

import discord
from discord.ext import commands


def fmt(d):
    return d.strftime('%A, %B %e %Y at %H:%M:%S')


class Discord_Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def avatar(self, ctx, *, user: discord.Member = None):
        """ Get the avatar of you or someone else """
        if user is None:
            user = ctx.author

        await ctx.send(f"Avatar to **{user.name}**\n{user.avatar_url_as(size=1024)}")

    @commands.command()
    @commands.guild_only()
    async def roles(self, ctx):
        """ Get all roles in current server """
        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = BytesIO(allroles.encode('utf-8'))
        await ctx.send(content=f"Roles in **{ctx.guild.name}**\n" + allroles.replace("@everyone", "everyone"))
        # , file=discord.File(data, filename=f"{'Roles'}"))

    @commands.command()
    @commands.guild_only()
    async def joinedat(self, ctx, *, user: discord.Member = None):
        """ Check when a user joined the current server """
        if user is None:
            user = ctx.author

        embed = discord.Embed(colour=user.top_role.colour.value)
        embed.set_thumbnail(url=user.avatar_url)
        embed.description = f'**{user}** joined **{ctx.guild.name}**\n{fmt(user.joined_at)}'
        await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    async def server(self, ctx):
        """ Check info about current server """
        if ctx.invoked_subcommand is None:
            findbots = sum(1 for member in ctx.guild.members if member.bot)

            embed = discord.Embed()
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.add_field(name="Server Name", value=ctx.guild.name, inline=True)
            embed.add_field(name="Server ID", value=ctx.guild.id, inline=True)
            embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
            embed.add_field(name="Bots", value=str(findbots), inline=True)
            embed.add_field(name="Owner", value=ctx.guild.owner, inline=True)
            embed.add_field(name="Region", value=ctx.guild.region, inline=True)
            embed.add_field(name="Created", value=fmt(ctx.guild.created_at), inline=True)
            await ctx.send(content=f"ℹ information about **{ctx.guild.name}**", embed=embed)

    @server.command(name="avatar", aliases=["icon"])
    @commands.guild_only()
    async def server_avatar(self, ctx):
        """ Get the current server icon """
        await ctx.send(f"Avatar of **{ctx.guild.name}**\n{ctx.guild.icon_url_as(size=1024)}")

    @commands.command()
    async def user(self, ctx, *, user: discord.User = None):
        """ Get user information """
        if user is None:
            user = ctx.author

        embed = discord.Embed(colour=user.colour)
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="Full name", value=user, inline=True)
        embed.add_field(name="Nickname", value=user.nick if hasattr(user, "nick") else "None", inline=True)
        embed.add_field(name="Account created", value=fmt(user.created_at), inline=True)

        # embed.add_field(
        #     name="Roles",
        #     value=', '.join([f"<@&{x.id}>" for x in user.roles if x is not ctx.guild.default_role]) if len(user.roles) > 1 else 'None',
        #     inline=False
        # )

        await ctx.send(content=f"ℹ About **{user.id}**", embed=embed)

    @commands.command()
    @commands.guild_only()
    async def member(self, ctx, *, user: discord.Member = None):
        """ Get user information """
        if user is None:
            user = ctx.author

        embed = discord.Embed(colour=user.top_role.colour.value)
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="Full name", value=user, inline=True)
        embed.add_field(name="Nickname", value=user.nick if hasattr(user, "nick") else "None", inline=True)
        embed.add_field(name="Account created", value=fmt(user.created_at), inline=True)
        embed.add_field(name="Joined this server", value=fmt(user.joined_at), inline=True)

        embed.add_field(
            name="Roles",
            value=', '.join([f"<@&{x.id}>" for x in user.roles if x is not ctx.guild.default_role]) if len(user.roles) > 1 else 'None',
            inline=False
        )

        await ctx.send(content=f"ℹ About **{user.id}**", embed=embed)

    # From R. Danny
    @commands.command(
        aliases=["sauce"],
        description="Use dots or spaces to find source code for subcommands, e.g. `clear info` or `clear.info`."
    )
    async def source(self, ctx, *, command=None):
        """Find my source code for a specific command."""

        source_url = "https://bitbucket.org/MAX1234/paladins-bot/src/master"
        if command is None:
            return await ctx.send("https://bitbucket.org/MAX1234/paladins-bot/src/master")

        if command == "help":
            src = type(ctx.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = ctx.bot.get_command(command.replace(".", " "))
            if obj is None:
                return await ctx.send("Could not find command.")

            # since we found the command we're looking for, presumably anyway, let's
            # try to access the code itself
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith("discord"):
            if module.startswith("jishaku"):
                source_url = "https://github.com/Gorialis/jishaku/blob/master"
                location = module.replace(".", "/") + ".py"
            else:
                location = os.path.relpath(filename).replace("\\", "/")
        else:
            location = module.replace(".", "/") + ".py"
            source_url = 'https://github.com/Rapptz/discord.py/blob/master'

        x = f"L{firstlineno}-L{firstlineno + len(lines) - 1}" if "github" in source_url else f"lines-{firstlineno}"

        final_url = f"<{source_url}/{location}#{x}>"

        await ctx.send(final_url)


def setup(bot):
    bot.add_cog(Discord_Info(bot))
