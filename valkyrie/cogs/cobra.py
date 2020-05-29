import ast
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
?expression: literal | function
function: "(" name expression* ")"
name: /[a-zA-Z_\\-<>0-9+*\\/\\^&|]+/
?literal: value | quoted_expr
quoted_expr: "'" /[a-zA-Z0-9]+/
"""

parser = lark.Lark(GRAMMAR)


class Cobra(commands.Cog):
    def find_function(self, ctx: commands.Context, name: str):
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
        }

        if name in builtins:
            return builtins[name]
        else:
            raise KeyError()

    async def eval_code(self, ctx: commands.Context, tree: lark.Tree, debug=False, allow_server_setup=False):
        if debug:
            await ctx.send(tree.pretty())

        if tree.data == "start":
            ret = None
            for exp in tree.children:
                ret = await self.eval_code(ctx, exp)
            return ret
        elif tree.data == "function":
            if len(tree.children) > 1:
                args = [
                    await self.eval_code(ctx, q)
                    for q in tree.children[1:]
                ]
            else:
                args = []
            return self.find_function(ctx, tree.children[0].children[0])(*args)
        elif tree.data in ["number", "string"]:
            return ast.literal_eval(tree.children[0])
        elif tree.data == "quoted_expr":
            return ast.literal_eval("'" + tree.children[0] + "'")
        else:
            return tree.data

    @commands.has_permissions(manage_server=True)
    @commands.command(aliases=["exec"])
    async def cobra(self, ctx: commands.Context, *, inp: str):
        """Mod-only command. Enables integration features such as autoresponding and serverwide variables."""
        await self.eval_code(ctx, parser.parse(inp), debug=False, allow_server_setup=True)

    @commands.command(aliases=["eval"])
    async def viper(self, ctx: commands.Context, *, inp: str):
        """Evaluates Cobra code."""
        await ctx.send(await self.eval_code(ctx, parser.parse(inp)))

    @commands.command(aliases=["db", "debug"])
    async def diamondback(self, ctx: commands.Context, *, inp: str):
        """Debugs Cobra code."""
        start = time.time()
        await ctx.send(await self.eval_code(ctx, parser.parse(inp), debug=True))
        end = time.time()
        await ctx.send(f"Execution completed in {end - start} seconds.")


def setup(bot):
    bot.add_cog(Cobra(bot))
