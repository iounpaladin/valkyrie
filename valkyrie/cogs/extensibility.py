import discord
import typing
from discord.ext import commands

from valkyrie.datastore import Datastore


async def fmt(list_, ctx: commands.Context):
    q = [((await ctx.bot.fetch_channel(x[0])).mention, x[1]) for x in list_]
    return q


class Extensibility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = Datastore('extensibility.pkl')
        # (guild_id: int) => {(hook: str) => [(where: channel), (response: str)][]}
        # TODO: autoresponder (message_contains_<xyz> => response)

    valid_hooks = """
    message_delete
    bulk_message_delete
    message_edit
    reaction_add
    reaction_remove
    reaction_clear
    guild_channel_update
    guild_channel_pins_update
    guild_integrations_update
    webhooks_update
    member_join
    member_remove
    member_update
    user_update
    guild_role_create
    guild_role_delete
    guild_role_update
    guild_emojis_update
    voice_state_update
    member_ban
    member_unban
    """.split()  # Remember to add on_ for actual event name

    def insert_array_if_not_found(self, guild_id: int):
        if self.data.get(guild_id) is None:
            self.data.set(guild_id, {})

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def when(self, ctx: commands.Context, hook: str, where: discord.TextChannel, *,
                   response: str):
        """When the event specified by `hook` is recieved, post `response` in `where`."""
        self.insert_array_if_not_found(ctx.guild.id)
        reason = self.check_hook(hook, where)
        if reason:
            return await ctx.send(f"{reason}.")

        new_arr: dict = self.data.get(ctx.guild.id)  # Guaranteed to be dict and not None
        if hook not in new_arr:
            new_arr[hook] = []

        new_arr[hook].append([where.id, response])
        self.data.set(ctx.guild.id, new_arr)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)  # Only mods can use this
    async def remove(self, ctx: commands.Context, hook: str, number: int = -1):
        """Removes a hook subscription."""
        self.insert_array_if_not_found(ctx.guild.id)
        if number == -1:
            return await ctx.send(self.data.get(ctx.guild.id).get(hook, []))
        else:
            to_set: dict = self.data.get(ctx.guild.id)
            arr: list = to_set.get(hook, [])
            try:
                arr.pop(number)
                to_set[hook] = arr
                self.data.set(ctx.guild.id, to_set)
                return await ctx.send(f"Removed hook {number}!")
            except IndexError:
                return await ctx.send(f"Cannot remove index {number} when there are only {len(arr)} hooks! "
                                      f"Remember this is 0-indexed.")

    @commands.command()
    @commands.guild_only()
    async def list(self, ctx: commands.Context):
        self.insert_array_if_not_found(ctx.guild.id)
        hash_: dict = self.data.get(ctx.guild.id)

        for i in hash_.keys():
            await ctx.send(f"{i} -> {await fmt(hash_[i], ctx)}")

    def check_hook(self, hook, where):
        if hook not in self.valid_hooks:
            return f"Hook {hook} not found!"
        elif not isinstance(where, discord.TextChannel):
            return f"{where} not a valid location!"

        return ""

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):  # author = before.author, before = before.content, after = after.content
        pass


def setup(bot: commands.Bot):
    bot.add_cog(Extensibility(bot))
