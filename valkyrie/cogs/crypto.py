from Crypto.Hash import SHA3_224, SHA224, SHA256, SHA384, SHA512, SHA3_256, SHA3_384, SHA3_512, SHA1, MD2, MD5, \
    RIPEMD160
import argon2
import bcrypt

from discord.ext import commands


def instahash_curry(klass: type):
    def internal(text: str):
        h = klass.new()
        h.update(text.encode('utf-8'))
        return h.hexdigest()

    return internal


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ph = argon2.PasswordHasher()

        self.hash_name_to_method = {
            "argon2": lambda text: ph.hash(text),
            "bcrypt": lambda text: bcrypt.hashpw(text.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            "sha224": instahash_curry(SHA224),
            "sha256": instahash_curry(SHA256),
            "sha384": instahash_curry(SHA384),
            "sha512": instahash_curry(SHA512),
            "sha3-224": instahash_curry(SHA3_224),
            "sha3-256": instahash_curry(SHA3_256),
            "sha3-384": instahash_curry(SHA3_384),
            "sha3-512": instahash_curry(SHA3_512),
            "sha1": instahash_curry(SHA1),
            "md2": instahash_curry(MD2),
            "md5": instahash_curry(MD5),
            "ripemd160": instahash_curry(RIPEMD160),
        }

    @commands.command()
    async def hash(self, ctx: commands.Context, algo: str, *, text: str):
        """Hashes text using a given algorithm. Valid algorithms: ARGON2, BCRYPT, SHA1, SHA2, SHA3, MD2, MD5,
        and RIPEMD160. """
        method = self.hash_name_to_method.get(algo)

        if method is None:
            return await ctx.send(f"{algo} is not a valid hashing algorithm!")
        else:
            return await ctx.send(method(text))


def setup(bot):
    bot.add_cog(Crypto(bot))
