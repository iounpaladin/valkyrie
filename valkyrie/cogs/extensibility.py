import inspect
import json
import pickle
import string
import urllib

import discord
import typing

import requests
from discord.ext import commands
from valkyrie.datastore import Datastore

PRODUCTION = 'generic' in str(__import__('platform').platform())


if PRODUCTION:
    with open('../.GAE_TOKEN') as f:
        GAE_TOKEN = f.read().rstrip()
else:
    GAE_TOKEN = ""

endpoint = 'https://valkyrie.structbuilders.com/data'


async def fmt(list_, ctx: commands.Context):
    q = [((await ctx.bot.fetch_channel(x[0])).mention, x[1]) for x in list_]
    return q


class Extensibility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = Datastore('extensibility.pkl')
        # (guild_id: int) => {(hook: str) => [(where: channel), (response: str)][]}

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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def verify(self, ctx: commands.Context, *, email: str):
        if not PRODUCTION: return
        requests.post(endpoint + '/verify', {
            'guild_id': ctx.guild.id,
            'email': email,
            '__token': GAE_TOKEN
        })

    def check_hook(self, hook, where):
        if hook not in self.valid_hooks:
            return f"Hook {hook} not found!"
        elif not isinstance(where, discord.TextChannel):
            return f"{where} not a valid location!"

        return ""

    @staticmethod
    def canonicalize(j):
        if isinstance(j, discord.Guild):
            return j.name
        elif isinstance(j, discord.User) or isinstance(j, discord.Member):
            return f'{j.display_name} ({j.id})'
        elif isinstance(j, discord.TextChannel):
            return f'{j.name} in {j.category.name}'
        elif isinstance(j, discord.Message):
            return j.content
        elif isinstance(j, list):
            return ', '.join([Extensibility.canonicalize(x) for x in j])

    async def run_hook(self, hook_name: str, args_for_hook: dict):
        guild_id = 0
        for i in args_for_hook.values():
            if isinstance(i, discord.Guild):
                guild_id = i.id
                break
            elif isinstance(i, list):
                if hasattr(i[0], 'guild'):
                    guild_id = i[0].guild.id
                    break
            elif hasattr(i, 'guild'):
                guild_id = i.guild.id
                break

        for i, j in args_for_hook.items():
            args_for_hook[i] = Extensibility.canonicalize(j)

        # Dump to DB
        self.dump_db(hook_name, guild_id, args_for_hook)

        if self.data.get(guild_id):
            if hook_name in self.data.get(guild_id):
                for hook in self.data.get(guild_id)[hook_name]:
                    await (
                        await self.bot.fetch_channel(hook[0])) \
                        .send(
                        string.Template(hook[1])
                            .safe_substitute(args_for_hook)
                    )

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        await self.run_hook('message_delete', {"message": message, "author": message.author})

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        await self.run_hook('bulk_message_delete', {"messages": messages})

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.run_hook('message_edit', {"before": before, "after": after, "member": before.author})

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        await self.run_hook('reaction_add', {"reaction": reaction, "user": user})

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        await self.run_hook('reaction_remove', {"reaction": reaction, "user": user})

    @commands.Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        await self.run_hook('reaction_clear', {"message": message, "reactions": reactions})

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        await self.run_hook('guild_channel_update', {"before": before, "after": after})

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        await self.run_hook('guild_channel_pins_update', {"channel": channel, "last_pin": last_pin})

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild):
        await self.run_hook('guild_integrations_update', {"guild": guild})

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        await self.run_hook('webhooks_update', {"channel": channel})

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.run_hook('member_join', {"member": member})

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.run_hook('member_remove', {"member": member})

#    @commands.Cog.listener()
#    async def on_member_update(self, before, after):
#        await self.run_hook('member_update', {"before": before, "after": after})

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        await self.run_hook('user_update', {"before": before, "after": after})

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.run_hook('guild_role_create', {"role": role})

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.run_hook('guild_role_delete', {"role": role})

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self.run_hook('guild_role_update', {"before": before, "after": after})

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        await self.run_hook('guild_emojis_update', {"guild": guild, "before": before, "after": after})

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await self.run_hook('voice_state_update', {"member": member, "before": before, "after": after})

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.run_hook('member_ban', {"guild": guild, "user": user})

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.run_hook('member_unban', {"guild": guild, "user": user})

    def dump_db(self, table, guild_id, args):
        requests.post(endpoint, {
            'table': table,
            'guild_id': guild_id,
            'args': urllib.parse.urlencode(args),
            '__token': GAE_TOKEN
        })


def setup(bot: commands.Bot):
    z = Extensibility(bot)
    bot.add_cog(z)
