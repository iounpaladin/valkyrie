from typing import List

import discord
from discord import Role
from discord.ext import commands
from discord.ext.commands import Greedy


class QuickPoll(commands.Cog):
    """"""

    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def quickpoll(self, ctx: commands.Context, question: str, *options: str):
        if len(options) <= 1:
            await ctx.send('You need more than one option to make a poll!')
            return
        if len(options) > 10:
            await ctx.send('You cannot make a poll for more than 10 things!')
            return

        if len(options) == 2 and options[0] == 'yes' and options[1] == 'no':
            reactions = ['✅', '❌']
        else:
            reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']

        description = []
        for x, option in enumerate(options):
            description += '\n {} {}'.format(reactions[x], option)
        embed = discord.Embed(title=question, description=''.join(description))
        react_message = await ctx.send(embed=embed)
        for reaction in reactions[:len(options)]:
            await react_message.add_reaction(reaction)
        embed.set_footer(text='Poll ID: {}'.format(react_message.id))
        await react_message.edit(embed=embed)

    @commands.command(pass_context=True)
    async def tally(self, ctx: commands.Context, id):
        poll_message = await ctx.fetch_message(id)
        if not poll_message.embeds:
            return
        embed = poll_message.embeds[0]
        if poll_message.author != ctx.me:
            return
        if not embed.footer.text.startswith('Poll ID:'):
            return
        unformatted_options = [x.strip() for x in embed.description.split('\n')]
        opt_dict = {x[:2]: x[3:] for x in unformatted_options} if unformatted_options[0][0] == '1' \
            else {x[:1]: x[2:] for x in unformatted_options}
        # check if we're using numbers for the poll, or x/checkmark, parse accordingly
        voters = [ctx.me.id]  # add the bot's ID to the list of voters to exclude it's votes

        tally = {x: 0 for x in opt_dict.keys()}
        for reaction in poll_message.reactions:
            if reaction.emoji in opt_dict.keys():
                reactors = await reaction.users().flatten()
                for reactor in reactors:
                    if reactor.id not in voters:
                        tally[reaction.emoji] += 1
                        voters.append(reactor.id)

        output = 'Results of the poll for "{}":\n'.format(embed.title) + \
                 '\n'.join(['{}: {}'.format(opt_dict[key], tally[key]) for key in tally.keys()])
        await ctx.send(output)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def rolepoll(self, ctx: commands.Context, roles: Greedy[Role]):
        roles: List[Role] = list(roles)
        options = [x.name for x in roles]

        if len(options) > 10:
            await ctx.send('You cannot make a poll for more than 10 things!')
            return

        if any(map(lambda x: x.position >= ctx.author.top_role.position, roles)):
            return await ctx.send("You cannot make a poll for a role higher (or equal to) than your top role!")

        reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']

        description = []
        for x, option in enumerate(options):
            description += '\n {}: {}'.format(reactions[x], option)
        embed = discord.Embed(title="Select reactions to gain roles!", description=''.join(description))
        react_message = await ctx.send(embed=embed)
        for reaction in reactions[:len(options)]:
            await react_message.add_reaction(reaction)
        embed.set_footer(text='ID: {}'.format(react_message.id))
        await react_message.edit(embed=embed)

    async def check_role_add_or_remove(self, message: int, user: int, guild: int, channel: int, emoji: discord.PartialEmoji, remove: bool):
        guild: discord.Guild = await self.bot.fetch_guild(guild)
        channel: discord.TextChannel = await self.bot.fetch_channel(channel)
        member = await guild.fetch_member(user)
        msg: discord.Message = await channel.fetch_message(message)
        ctx: commands.Context = await self.bot.get_context(msg)

        if len(msg.embeds) == 0 or msg.author != ctx.me or member == ctx.me:
            return

        embed: discord.Embed = msg.embeds[0]
        content = embed.description
        maps = [x.split(': ') for x in content.split('\n') if x]
        for x in maps:
            if not len(x) > 1:
                return
        # await ctx.send(maps)
        # await ctx.send(emoji.name)
        # print(emoji.name)

        role: discord.Role = None
        role_str: str = ''

        for i in maps:
            if emoji.name in i[0]:
                role_str = i[1]
                break

        # await ctx.send(role_str)
        for i in guild.roles:
            if i.name.strip() == role_str.strip():
                role = i
                break

        if role is None:
            return

        if remove:
            await member.remove_roles(role)
        else:
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.check_role_add_or_remove(payload.message_id, payload.user_id, payload.guild_id,
                                            payload.channel_id,
                                            payload.emoji,
                                            False)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.check_role_add_or_remove(payload.message_id, payload.user_id, payload.guild_id,
                                            payload.channel_id,
                                            payload.emoji,
                                            True)


def setup(bot):
    bot.add_cog(QuickPoll(bot))
