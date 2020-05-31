import ast
import asyncio
import math
import operator
import pickle
import random
import re
import time

from discord.ext import commands
import lark

# PLAN (TODO)
# Hooks (from ^)
# Utils/libs

GRAMMAR = """
?value: string
          | SIGNED_NUMBER      -> number
          | "true"             -> true
          | "false"            -> false
          | "null"             -> null

string : ESCAPED_STRING

%import common.ESCAPED_STRING
%import common.SIGNED_NUMBER
%import common.WS
%ignore WS

start: expression+
?expression: literal | macro | function | name
// define: "(" "define:" name quopar expression ")"
macro: "(" name "!" (expression | name)* ")"
function: "(" name expression* ")"
name: /[a-zA-Z_\\-<>+*\\/\\^&|%=][a-zA-Z_\\-<>+*\\/\\^&|=%0-9]*/
?literal: value | quoted_expr | quopar
quoted_expr: "'" /[a-zA-Z0-9]+/
quopar: "'" "(" expression* ")"
"""

parser = lark.Lark(GRAMMAR)


class DelayedFunction:
    def __init__(self, args, code):
        self.args = args
        self.code = code

    def __call__(self, context, eval_code, *args):
        c = dict(context)
        for i in range(len(self.args)):
            c[self.args[i]] = args[i]

        return eval_code(c, self.code)


def cond(*args):
    pairs = zip(args[::2], args[1::2])
    for i in pairs:
        if i[0]: return i[1]


def find_function(ctx: commands.Context, context: dict, name: str):
    builtins = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "**": pow,
        "%": operator.mod,
        "^": operator.xor,
        "&": operator.and_,
        "|": operator.or_,
        ">>": operator.rshift,
        "<<": operator.lshift,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        '==': operator.eq,
        '!=': operator.ne,
        "log": math.log,
        "exp": math.exp,
        "sqrt": math.sqrt,
        "e": lambda: math.e,
        "pi": lambda: math.pi,
        "guild": lambda: ctx.guild,
        "id": lambda x: x.id,
        "me": lambda: ctx.me,
        "author": lambda: ctx.author,
        "message": lambda: ctx.message,
        "name": lambda x: x.name,
        "display-name": lambda x: x.display_name,
        "members": lambda x: x.members,
        "channel": lambda: ctx.channel,
        "get": lambda n: context[n],
        "define": lambda n, val: context.update([(n, val)]),
        "set": lambda n, val: context.update([(n, val)]),
        "context": lambda: context,
        "send": lambda s: asyncio.run_coroutine_threadsafe(ctx.send(s), ctx.bot.loop),
        "cond": cond,
        "randf": random.random,
        "randrange": random.randrange
    }

    if name in builtins:
        return builtins[name]
    else:
        return context.get(name)


async def save_context(context, ctx):
    data = None
    try:
        data = pickle.dumps(context)
    except (pickle.PickleError, AttributeError) as e:
        await ctx.send(f"Cannot serialize your context! Did you try to save a non-serializable variable?\nRaw: {e}")

    if data:
        try:
            with open(f"contexts/{ctx.author.id}.ctx", 'wb') as f:
                f.write(data)
        except FileNotFoundError as e:
            await ctx.send(f"File not found! Is the bot configured properly?\nRaw: {e}")


def load_context(id):
    try:
        with open(f"contexts/{id}.ctx", "rb") as f:
            ret = pickle.load(f)
    except FileNotFoundError:
        return {}
    return ret


class Cobra(commands.Cog):
    async def eval_code(self, ctx: commands.Context, tree: lark.Tree, context, debug=False, allow_integrations=False):
        if tree.data == "start":
            ret = None
            for exp in tree.children:
                ret = await self.eval_code(ctx, exp, context, debug, allow_integrations)
            return ret
        elif tree.data == "name":
            return context[str(tree.children[0])]
        elif tree.data == "define":
            context[str(tree.children[0].children[0])] = DelayedFunction(
                [await self.eval_code(ctx, x, context, debug, allow_integrations)
                 for x in tree.children[1].children
                 ], tree.children[2])

            return
        elif tree.data == "quopar":
            return [
                await self.eval_code(ctx, x, context, debug, allow_integrations)
                for x in tree.children
            ]
        elif tree.data == "function":
            if len(tree.children) > 1:
                args = [
                    await self.eval_code(ctx, q, context, debug, allow_integrations)
                    for q in tree.children[1:]
                ]
            else:
                args = []

            fn = find_function(ctx, context, str(tree.children[0].children[0]))
            if isinstance(fn, DelayedFunction):
                return await fn(context, lambda new_exe_ctx, code: self.eval_code(ctx, code, new_exe_ctx, debug,
                                                                                  allow_integrations), *args)
            return fn(*args)
        elif tree.data in ["number", "string"]:
            return ast.literal_eval(tree.children[0])
        elif tree.data == "quoted_expr":
            return ast.literal_eval("'" + tree.children[0] + "'")
        elif tree.data == "macro":
            name = str(tree.children[0].children[0])

            if name == "if":
                condition = await self.eval_code(ctx, tree.children[1], context, debug, allow_integrations)
                if condition:
                    return await self.eval_code(ctx, tree.children[2], context, debug, allow_integrations)
                return await self.eval_code(ctx, tree.children[3], context, debug, allow_integrations)

            if name == "while":
                ret = None
                while await self.eval_code(ctx, tree.children[1], context, debug, allow_integrations):
                    ret = await self.eval_code(ctx, tree.children[2], context, debug, allow_integrations)

                return ret

            if name == "for":
                # new scope
                # new_context = dict(context)
                new_context = context
                ret = None
                await self.eval_code(ctx, tree.children[1], new_context, debug, allow_integrations)
                while await self.eval_code(ctx, tree.children[2], new_context, debug, allow_integrations):
                    ret = await self.eval_code(ctx, tree.children[4], new_context, debug, allow_integrations)
                    await self.eval_code(ctx, tree.children[3], new_context, debug, allow_integrations)

                return ret

            if name == "define":
                context[str(tree.children[1].children[0])] = DelayedFunction(
                    [await self.eval_code(ctx, x, context, debug, allow_integrations)
                     for x in tree.children[2].children
                     ], tree.children[3])
                return
            elif re.match("c[ad]+r", name):
                cdadr = name[-2:0:-1]
                lis = await self.eval_code(ctx, tree.children[1], context, debug, allow_integrations)

                for item in cdadr:
                    if item == 'a':
                        lis = lis[0]
                    elif item == 'd':
                        lis = lis[1:]

                return lis
            # print(tree.pretty())
        else:
            return tree.data

    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(aliases=["exec"])
    async def cobra(self, ctx: commands.Context, *, inp: str):
        """Mod-only command. Enables integration features such as hooks and persistence."""
        context = load_context(ctx.author.id)
        resp = await self.eval_code(ctx, parser.parse(inp), context, debug=False, allow_integrations=True)
        if resp:
            await ctx.send(resp)
        await save_context(context, ctx)

    @commands.command(aliases=["eval"])
    async def viper(self, ctx: commands.Context, *, inp: str):
        """Evaluates Cobra code."""
        await ctx.send(await self.eval_code(ctx, parser.parse(inp), {}))

    @commands.command(aliases=["db", "debug"])
    async def diamondback(self, ctx: commands.Context, *, inp: str):
        """Debugs Cobra code."""
        try:
            start = time.time()
            tree = parser.parse(inp)
            await ctx.send(tree.pretty())
            await ctx.send(await self.eval_code(ctx, tree, {}, debug=True))
            end = time.time()
            await ctx.send(f"Execution completed in {end - start} seconds.")
        except Exception as e:  # pylint: disable-broad-except
            # noinspection PyTypeChecker
            await ctx.send(e)


def setup(bot):
    bot.add_cog(Cobra(bot))
