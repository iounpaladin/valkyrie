import ast
import asyncio
import math
import operator
import time

from discord.ext import commands
import lark

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
?expression: literal | define | function
define: "(" "define:" name quopar expression ")"
function: "(" name expression* ")"
name: /[a-zA-Z_\\-<>+*\\/\\^&|][a-zA-Z_\\-<>+*\\/\\^&|0-9]*/
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
        print(*args)
        c = dict(context)
        for i in range(len(self.args)):
            c[self.args[i]] = args[i]

        return eval_code(c, self.code)


class Cobra(commands.Cog):
    def find_function(self, ctx: commands.Context, context: dict, name: str):
        builtins = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "**": operator.pow,
            "^": operator.xor,
            "&": operator.and_,
            "|": operator.or_,
            ">>": operator.rshift,
            "<<": operator.lshift,
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
            "get": lambda name: context[name],
            "define": lambda name, val: context.update([(name, val)]),
            "context": lambda: context,
            "send": lambda s: asyncio.run_coroutine_threadsafe(ctx.send(s), ctx.bot.loop)
        }

        if name in builtins:
            return builtins[name]
        else:
            return context.get(name)

    async def eval_code(self, ctx: commands.Context, tree: lark.Tree, context, debug=False, allow_integrations=False):
        if debug and hasattr(tree, 'pretty'):
            await ctx.send(tree.pretty())

        if tree.data == "start":
            ret = None
            for exp in tree.children:
                ret = await self.eval_code(ctx, exp, context, debug, allow_integrations)
            return ret
        elif tree.data == "name":
            return tree.children[0]
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

            fn = self.find_function(ctx, context, str(tree.children[0].children[0]))
            if isinstance(fn, DelayedFunction):
                return await fn(context, lambda new_exe_ctx, code: self.eval_code(ctx, code, new_exe_ctx, debug, allow_integrations), *args)
            return fn(*args)
        elif tree.data in ["number", "string"]:
            return ast.literal_eval(tree.children[0])
        elif tree.data == "quoted_expr":
            return ast.literal_eval("'" + tree.children[0] + "'")
        else:
            return tree.data

    @commands.has_permissions(manage_server=True)
    @commands.command(aliases=["exec"])
    async def cobra(self, ctx: commands.Context, *, inp: str):
        """Mod-only command. Enables integration features such as hooks and persistence."""
        return await ctx.send("This command is not yet complete! Sorry!")
        # await self.eval_code(ctx, parser.parse(inp), {}, debug=False, allow_integrations=True)

    @commands.command(aliases=["eval"])
    async def viper(self, ctx: commands.Context, *, inp: str):
        """Evaluates Cobra code."""
        await ctx.send(await self.eval_code(ctx, parser.parse(inp), {}))

    @commands.command(aliases=["db", "debug"])
    async def diamondback(self, ctx: commands.Context, *, inp: str):
        """Debugs Cobra code."""
        start = time.time()
        await ctx.send(await self.eval_code(ctx, parser.parse(inp), {}, debug=True))
        end = time.time()
        await ctx.send(f"Execution completed in {end - start} seconds.")


def setup(bot):
    bot.add_cog(Cobra(bot))
