import asyncio
import random
import string
from typing import List, Union, Tuple

import discord

from valkyrie.cogs.onenight.role import *


def get_role(x):
    for i in ROLES:
        if i.name == x:
            return i


class Lobby:
    message: discord.Message
    players: List[discord.User]
    roles: str
    __playercount: int
    started: bool = False
    client: discord.Client = None

    def __init__(self, msg, roles, client):
        self.message = msg
        self.roles = roles
        self.__playercount = len(roles) - 3
        self.players = []
        self.client = client

    async def add_player(self, player):
        if len(self.players) < self.__playercount:
            self.players.append(player)
            if len(self.players) == self.__playercount:
                self.started = True
                await self.start()
            return True
        else:
            return False

    async def remove_player(self, player):
        if self.started: return False
        try:
            self.players.remove(player)
            return True
        except ValueError:
            return False

    def get_max_players(self):
        return self.__playercount

    async def get_response_by(self, by: List[discord.User], in_: discord.TextChannel, extra_parse=None):
        def check(m):
            return any(map(lambda x: m.author.id == x.id, by)) and m.channel == in_

        try:
            return await self.client.wait_for('message', check=check, timeout=30)
        except:
            return

    async def start(self):
        await self.message.channel.send("== **GAME START** ==")

        # === MAIN GAME LOGIC ===
        role_obj_list = [get_role(x) for x in self.roles]
        wake_order = sorted(list(set(filter(lambda x: x.wake_id, role_obj_list))), key=lambda x: x.wake_id)
        random.shuffle(role_obj_list)

        centre = [role_obj_list.pop(), role_obj_list.pop(), role_obj_list.pop()]
        player_and_role_list: List[Tuple[Role, discord.User]] = list(zip(role_obj_list, self.players))

        for i in player_and_role_list:
            await i[1].send(f'Your secret role is {i[0].name}! (lobby id: {self.message.id})')

        await self.message.channel.send("== **DEALT ROLES** ==")

        # == NIGHT PHASE ==

        for i in wake_order:
            await self.message.channel.send(
                f"== **THE {i.name_plural.upper() if i.max_count > 1 else i.name.upper()} RISE{'' if i.max_count > 1 else 'S'} FROM THEIR SLUMBER** ==\nThey have 30 seconds to select an action."
            )

            players_for_role = [
                y[1] for y in player_and_role_list
                if y[0] == i
            ]

            if players_for_role:
                player = players_for_role[0]
                if i.name == SEER[0]:
                    message = await player.send(
                        "Please enter the number of the player you wish to see the card of, "
                        "or two numbers (space separated) if you would like to view cards from the centre."
                        f"\nPlayers (for reference): {', '.join(list(map(lambda x: '[' + str(self.players.index(x) + 1) + '] ' + x.display_name, self.players)))}")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    v = resp.content.strip(string.ascii_letters).split()

                    if len(v) > 1:  # Did they select two centre cards?
                        try:
                            a = centre[int(v[0]) - 1]
                            b = centre[int(v[1]) - 1]
                            await player.send(f"You see the following centre cards: {a.name}, {b.name}.")
                        except:
                            await player.send("Invalid selection!")
                    else:
                        try:
                            a = self.players[int(v[0]) - 1]
                            b = [
                                y[0] for y in player_and_role_list
                                if y[1].id == a.id
                            ][0]

                            await player.send(f"You see {a.display_name}'s card: {b.name}.")
                        except:
                            await player.send("Invalid selection!")

                elif i.name == WEREWOLF[0]:
                    for p in players_for_role:
                        await p.send(
                            f"You see the Werewolves are {', '.join(map(lambda x: x.display_name, players_for_role))}.")

                    if len(players_for_role) == 1:
                        message = await player.send(
                            "As the Lone Werewolf, you may peek at a centre card.")
                        resp = await self.get_response_by(players_for_role, message.channel)
                        v = resp.content.strip(string.ascii_letters)

                        try:
                            a = centre[int(v) - 1]
                            await player.send(f"You see the following centre card: {a.name}.")
                        except:
                            await player.send("Invalid selection!")
                elif i.name == MINION[0]:
                    await player.send(
                        f"You see the Werewolves are: {', '.join(map(lambda x: x.display_name, [y[1] for y in player_and_role_list if y[0].name == WEREWOLF[0]]))}.")
                elif i.name == MASON[0]:
                    for p in players_for_role:
                        await p.send(
                            f"You see the masons are {', '.join(map(lambda x: x.display_name, players_for_role))}.")
                elif i.name == ROBBER[0]:
                    message = await player.send(
                        "Select another player to swap cards with (type their number)."
                        f"\nPlayers (for reference): {', '.join(list(map(lambda x: '[' + str(self.players.index(x) + 1) + '] ' + x.display_name, self.players)))}")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    v = resp.content.strip(string.ascii_letters)

                    try:
                        a = int(v) - 1

                        b = player_and_role_list.index((i, player))

                        assert a != b

                        cache_a_role = player_and_role_list[a][0]
                        player_and_role_list[a] = (player_and_role_list[b][0], player_and_role_list[a][1])
                        player_and_role_list[b] = (cache_a_role, player_and_role_list[b][1])

                        await player.send(f"You see your role as {player_and_role_list[b][0].name}.")
                    except:
                        await player.send("Invalid selection!")
                elif i.name == TROUBLEMAKER[0]:
                    message = await player.send(
                        "Select two other players to swap cards (type their numbers, space separated)."
                        f"\nPlayers (for reference): {', '.join(list(map(lambda x: '[' + str(self.players.index(x) + 1) + '] ' + x.display_name, self.players)))}")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    v = resp.content.strip(string.ascii_letters).split()

                    try:
                        a = int(v[0]) - 1
                        b = int(v[1]) - 1

                        idx = player_and_role_list.index((i, player))

                        assert a != idx and b != idx and a != b

                        cache_a_role = player_and_role_list[a][0]
                        player_and_role_list[a] = (player_and_role_list[b][0], player_and_role_list[a][1])
                        player_and_role_list[b] = (cache_a_role, player_and_role_list[b][1])
                    except:
                        await player.send("Invalid selection!")
                elif i.name == INSOMNIAC[0]:
                    b = [
                        y[0] for y in player_and_role_list
                        if y[1].id == player.id
                    ][0]
                    await player.send(f"You see your role as {b.name}.")
                elif i.name == DRUNK[0]:
                    message = await player.send(
                        "Select a centre card to swap with.")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    v = resp.content.strip(string.ascii_letters)

                    try:
                        if v is None: v = 1
                        card = centre[int(v) - 1]
                        await player.send(f"You swap your card with centre card #{v}.")

                        player_and_role_list[player_and_role_list.index((i, player))] = (card, player)
                        centre[int(v) - 1] = i
                    except:
                        await player.send("Invalid selection!")

            await asyncio.sleep(30)

            await self.message.channel.send(
                f"== **THE {i.name_plural.upper() if i.max_count > 1 else i.name.upper()} RETURN{'' if i.max_count > 1 else 'S'} TO THEIR SLUMBER** =="
            )

        # == DAY PHASE ==

        await self.message.channel.send("== **EVERYONE AWAKENS** ==")
        await self.message.channel.send("== **BEGIN VOTING** ==")
        await self.message.channel.send(
            "Game ends once all players vote."
            "\nType `vote<number>` (e.g. `vote1`) to vote (your message will be deleted for anonymity)."
            # "\nVoting for yourself will be counted as a random vote (do not do it)."
            # "\nBe sure to vote carefully: you cannot change your vote."
            f"\nPlayers (for reference): {', '.join(list(map(lambda x: '[' + str(self.players.index(x) + 1) + '] ' + x.display_name, self.players)))}"
        )

        vote_ctr = await self.message.channel.send("The following players have voted: none yet.")

        votes = dict()

        while True:
            resp = await self.get_response_by(self.players, self.message.channel)

            try:
                await resp.delete()

                vote = int(resp.content.strip(string.ascii_letters)) - 1

                idx = player_and_role_list.index([
                    x for x in player_and_role_list
                    if x[1].id == resp.author.id
                ][0])

                if vote != idx:
                    votes[resp.author] = vote

                    await vote_ctr.edit(content=f"The following players have voted: {', '.join(map(lambda x: x.display_name, votes.keys()))}.")

                    if len(votes.keys()) >= self.__playercount:
                        break
            except:
                continue

        col = collections.Counter(votes.values())

        death = player_and_role_list[col.most_common()[0][0]]

        # == GAME END ==

        await self.message.channel.send("== **GAME END** ==")
        await self.message.channel.send(f"{death[1].display_name} has been lynched.")

        winning_team = ''

        while not winning_team:
            if death[0].name == TANNER[0]:
                winning_team = 'Tanners'
                reason = 'The Tanner has been killed'
                winners = [death[1].display_name]
            elif death[0].name == WEREWOLF[0]:
                winning_team = 'Villagers'
                reason = 'A Werewolf has been killed'
                winners = [
                    x[1].display_name for x in player_and_role_list
                    if x[0].village
                ]
            elif death[0].name == HUNTER[0]:
                await self.message.channel.send("== **THE HUNTER HAS BEEN HUNG** ==")

                await asyncio.sleep(2)

                await self.message.channel.send(f'{player_and_role_list[votes[death[1]]][1].display_name} was shot by the Hunter.')
                death = player_and_role_list[votes[death[1]]]
            else:
                winning_team = 'Werewolves'
                reason = 'A Villager has been killed'
                winners = [
                    x[1].display_name for x in player_and_role_list
                    if x[0].ww
                ]

        await asyncio.sleep(2)

        await self.message.channel.send(f"== {reason}. {winning_team} win the game. ==")
        await self.message.channel.send(f"Winners: {', '.join(winners)}.")

        await self.message.channel.send(
            f"Roles: {', '.join(map(lambda x: f'{x[1].display_name}: {x[0].name}', player_and_role_list))}.")
        # TODO: game log
