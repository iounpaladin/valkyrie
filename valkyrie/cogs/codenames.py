import asyncio
import random
from typing import List

import discord
from discord.ext import commands


def format_words(words, markers):
    rows = list(zip(words[::5], words[1::5], words[2::5], words[3::5], words[4::5]))

    out = "```"
    longest = max(map(len, words))

    for y in range(5):
        row = rows[y]
        for x in range(5):
            out += f'[{markers[y][x]}] {row[x].ljust(longest + 2)}'

        out += '\n'

    out += "```"

    return out


def generate_key(words, blu_first):
    blu_quota = 9 if blu_first else 8
    red_quota = 17 - blu_quota
    assassin_quota = 1
    blu_words = []
    red_words = []

    arr = [['W' for x in range(5)] for y in range(5)]

    while blu_quota:
        x, y = (random.randrange(0, 5), random.randrange(0, 5))
        if arr[y][x] == 'W':
            arr[y][x] = 'B'
            blu_words.append(words[x + 5 * y])
            blu_quota -= 1

    while red_quota:
        x, y = (random.randrange(0, 5), random.randrange(0, 5))
        if arr[y][x] == 'W':
            arr[y][x] = 'R'
            red_words.append(words[x + 5 * y])
            red_quota -= 1

    while assassin_quota:
        x, y = (random.randrange(0, 5), random.randrange(0, 5))
        if arr[y][x] == 'W':
            arr[y][x] = 'A'
            assassin_quota -= 1

    return arr, blu_words, red_words


def format_wordlist(blu_words, red_words, blu_guessed, red_guessed):
    who_goes_first = ("Blu" if len(blu_words) > len(red_words) else "Red") + " Team goes first."
    blu_line = "Blu words: " + ' '.join([('~~' + word + '~~' if blu_guessed[word] else word) for word in blu_words]) \
               + f" ({len(blu_words) - sum(blu_guessed.values())}/{len(blu_words)} remain)"
    red_line = "Red words: " + ' '.join([('~~' + word + '~~' if red_guessed[word] else word) for word in red_words]) \
               + f" ({len(red_words) - sum(red_guessed.values())}/{len(red_words)} remain)"
    return f"{who_goes_first}\n{blu_line}\n{red_line}"


def to_color(key, words, guess):
    a = words.index(guess)

    return {
        'W': "an Innocent Bystander",
        'R': "a Red Spy",
        'B': "a Blu Spy",
        'A': "The Assassin"
    }[key[a // 5][a % 5]]


class Codenames(commands.Cog):
    @commands.command()
    async def codenames(self, ctx: commands.Context, redvc: discord.VoiceChannel, bluvc: discord.VoiceChannel,
                        gamevc: discord.VoiceChannel, redchat: discord.TextChannel, bluchat: discord.TextChannel,
                        spymaster_chat: discord.TextChannel,
                        red_leader: discord.Member, blu_leader: discord.Member,
                        players: commands.Greedy[discord.Member]):
        everyone = ctx.guild.roles[0]
        red = await ctx.guild.create_role(colour=discord.Colour.red(), name="Red Team")
        redspymaster = await ctx.guild.create_role(colour=discord.Colour.red(), name="Red Spymaster")
        blu = await ctx.guild.create_role(colour=discord.Colour.blue(), name="Blu Team")
        bluspymaster = await ctx.guild.create_role(colour=discord.Colour.blue(), name="Blu Spymaster")

        await red_leader.add_roles(redspymaster)
        await blu_leader.add_roles(bluspymaster)

        random.shuffle(players)
        redteam = players[::2]
        bluteam = players[1::2]

        for b in bluteam:
            await b.add_roles(blu)

        for r in redteam:
            await r.add_roles(red)

        # Channel Overrides
        await redvc.set_permissions(everyone, connect=False)
        await redvc.set_permissions(red, connect=True)
        await redvc.set_permissions(redspymaster, connect=True)
        await bluvc.set_permissions(everyone, connect=False)
        await bluvc.set_permissions(blu, connect=True)
        await bluvc.set_permissions(bluspymaster, connect=True)

        await redchat.set_permissions(everyone, read_messages=False)
        await redchat.set_permissions(red, read_messages=True)
        await bluchat.set_permissions(everyone, read_messages=False)
        await bluchat.set_permissions(blu, read_messages=True)

        await spymaster_chat.set_permissions(everyone, read_messages=False)
        await spymaster_chat.set_permissions(redspymaster, read_messages=True)
        await spymaster_chat.set_permissions(bluspymaster, read_messages=True)

        with open('wordlist.txt') as f:
            words = list(map(str.strip, random.sample(f.readlines(), 25)))

        blu_first = random.random() > 0.5  # Does blue go first?
        markers = [['U' for x in range(5)] for y in
                   range(5)]  # Markers: U = unguessed, W = white, B = blue, R = red, A = assassin
        key, blu_words, red_words = generate_key(words, blu_first)
        # Key: the Spymaster key; blu_words: list of blue words; red_words: list of red words
        blu_guessed = {x: False for x in blu_words}  # Map corresponding to each blue word and if it has been guessed
        red_guessed = {x: False for x in red_words}  # "" but for red

        board1 = await redchat.send(format_words(words, markers))
        board2 = await bluchat.send(format_words(words, markers))
        await spymaster_chat.send(format_words(words, key))
        wordlist_msg = await spymaster_chat.send(format_wordlist(blu_words, red_words, blu_guessed, red_guessed))

        turn = blu_first  # Blu = 1, red = 0
        game_over = False
        winner = "Red"

        while not game_over:
            await ctx.channel.send(
                f"It is {['Red', 'Blu'][turn]} Team's turn. Spymaster, please provide a clue in the Spymaster chat.")

            def check(m):
                return m.author == (blu_leader if turn else red_leader) and m.channel == spymaster_chat

            clue_valid = False

            while not clue_valid:
                msg: discord.Message = await ctx.bot.wait_for('message', check=check)  # Read and clean clue
                clue = msg.clean_content.strip()
                try:
                    clue_valid = len(clue.split()) == 2 and int(clue.split()[1]) > -1
                except:
                    pass

            current_guessers: List[discord.Member]
            guessing_channel: discord.TextChannel

            if turn:  # Blue's turn?
                await bluchat.send(f"Your clue is {clue}!")
                try:
                    await blu_leader.edit(mute=True, voice_channel=bluvc)
                except:
                    pass

                for b in bluteam:
                    try:
                        await b.edit(voice_channel=bluvc)
                    except:
                        pass

                current_guessers = bluteam
                guessing_channel = bluchat
            else:
                await redchat.send(f"Your clue is {clue}!")
                try:
                    await red_leader.edit(mute=True, voice_channel=redvc)
                except:
                    pass

                for r in redteam:
                    try:
                        await r.edit(voice_channel=redvc)
                    except:
                        pass

                current_guessers = redteam
                guessing_channel = redchat

            turn_ended = False
            guesses = int(clue.split()[1])
            guesses_left = (guesses + 1 if guesses else 2 ** 31 - 1)
            while not turn_ended and guesses_left:
                # Await guess
                def check2(m):
                    return m.author in current_guessers and m.channel.id == guessing_channel.id

                msg: discord.Message = await ctx.bot.wait_for('message', check=check2)  # Read and clean clue
                guess = msg.clean_content.strip()

                if guess in words:
                    guesses_left -= 1

                    idx = words.index(guess)
                    markers[idx // 5][idx % 5] = key[idx // 5][idx % 5]
                    res = to_color(key, words, guess)
                    await ctx.channel.send(f"{'Blu' if turn else 'Red'} Team guesses {guess}. It is {res}. (They have {guesses_left} guesses left).")

                    if "Innocent" in res:
                        turn_ended = True
                    if ("Blu" in res and not turn) or ("Red" in res and turn):
                        turn_ended = True
                    if "Assassin" in res:
                        game_over = True
                        turn_ended = True
                        winner = ("Red" if turn else "Blu")

                    if "Blu" in res:
                        blu_guessed[guess] = True
                    elif "Red" in res:
                        red_guessed[guess] = True

                    await wordlist_msg.edit(content=format_wordlist(blu_words, red_words, blu_guessed, red_guessed))
                    await board1.edit(content=format_words(words, markers))
                    await board2.edit(content=format_words(words, markers))

            for g in players + [blu_leader, red_leader]:
                await g.edit(voice_channel=gamevc, mute=False)

            # End of turn cleanup
            turn = not turn
            if all(blu_guessed.values()):
                game_over = True
                winner = "Blu"
            elif all(red_guessed.values()):
                game_over = True
                winner = "Red"

        await ctx.channel.send(f"Good game! {winner} has won.")

        await red.delete()
        await blu.delete()
        await redspymaster.delete()
        await bluspymaster.delete()


def setup(bot):
    bot.add_cog(Codenames(bot))
