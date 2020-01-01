import discord
from discord.ext import commands

from valkyrie.datastore import Datastore


class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = Datastore('starboard.pkl')  # settings is a map guild_id => hash
        # hash is of the form channel => int, bans => int[], limit => int, messages => {message_id => starboard_id}

    @commands.group()
    async def starboard(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None: return
        e = discord.Embed(colour=discord.Colour.purple())
        e.add_field(name="Limit", value=str(self.settings.get(ctx.guild.id)["limit"]))
        await ctx.send(embed=e)

    @starboard.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Mod-only: set the starboard channel"""
        if self.settings.get(ctx.guild.id) is None:
            self.settings.set(ctx.guild.id, {})

        current_hash = self.settings.get(ctx.guild.id)
        current_hash["channel"] = channel.id

        self.settings.set(ctx.guild.id, current_hash)
        return await ctx.send(f"#{channel.name} set as starboard channel.")

    @starboard.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def ban_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Mod-only: bans a channel from showing up in the starboard"""
        if self.settings.get(ctx.guild.id) is None:
            self.settings.set(ctx.guild.id, {})

        current_hash = self.settings.get(ctx.guild.id)
        if "bans" not in current_hash:
            current_hash["bans"] = []
        current_hash["bans"].append(channel.id)

        self.settings.set(ctx.guild.id, current_hash)
        return await ctx.send(f"{channel.name} banned.")

    @starboard.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def unban_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Mod-only: unbans a channel from showing up in the starboard"""
        if self.settings.get(ctx.guild.id) is None:
            self.settings.set(ctx.guild.id, {})

        current_hash = self.settings.get(ctx.guild.id)
        if "bans" not in current_hash:
            current_hash["bans"] = []

        try:
            current_hash["bans"].remove(channel.id)
        except ValueError:
            return await ctx.send("That channel was not banned!")

        self.settings.set(ctx.guild.id, current_hash)
        return await ctx.send(f"{channel.name} unbanned.")

    @starboard.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def limit(self, ctx: commands.Context, limit: int):
        """Mod-only: sets the number of stars needed"""
        if self.settings.get(ctx.guild.id) is None:
            self.settings.set(ctx.guild.id, {})

        current_hash = self.settings.get(ctx.guild.id)
        current_hash["limit"] = limit

        self.settings.set(ctx.guild.id, current_hash)
        return await ctx.send(f"{limit} is the new limit.")

    def fmt(self, s: str):
        return '\n'.join(['> ' + x for x in s.split('\n')])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, data: discord.RawReactionActionEvent):
        if self.settings.get(data.guild_id):
            if (self.settings.get(data.guild_id)["bans"] and data.channel_id in self.settings.get(data.guild_id)[
                "bans"]) \
                    or data.emoji.name != '⭐':
                return

            if "messages" not in self.settings.get(data.guild_id):
                new_ = self.settings.get(data.guild_id)
                new_["messages"] = {}
                self.settings.set(data.guild_id, new_)

            guild: discord.Guild = await self.bot.fetch_guild(data.guild_id)
            chan: discord.TextChannel = await self.bot.fetch_channel(data.channel_id)
            message: discord.Message = await chan.fetch_message(data.message_id)

            rxn = list(filter(lambda r: r.emoji == '⭐', message.reactions))[0]

            if data.message_id in self.settings.get(data.guild_id)["messages"]:
                # Edit
                dat = self.settings.get(data.guild_id)["messages"][data.message_id]
                channel: discord.TextChannel = await self.bot.fetch_channel(self.settings.get(data.guild_id)["channel"])
                msg: discord.Message = await channel.fetch_message(dat[0])
                content: str = msg.content

                star_count = int(content.split()[-2])

                content = ' '.join(content.split(' ')[:-2] + [str(rxn.count), 'stars'])

                if rxn.count > star_count:
                    await msg.edit(content=content)
            else:
                if rxn.count >= self.settings.get(data.guild_id)["limit"]:
                    msg: discord.Message = await (
                        await self.bot.fetch_channel(self.settings.get(data.guild_id)["channel"])).send(
                        f"{self.fmt(message.content)}\n- "
                        f"{message.author.display_name}, {rxn.count} stars")

                    new_ = self.settings.get(data.guild_id)
                    new_["messages"][data.message_id] = [
                        msg.id,
                        rxn.count
                    ]
                    self.settings.set(data.guild_id, new_)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Starboard(bot))
