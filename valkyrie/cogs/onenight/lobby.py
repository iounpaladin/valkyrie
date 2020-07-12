import asyncio
import random
import string
from typing import List, Union, Tuple

import discord
from discord.ext import commands

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
    task = None

    def __init__(self, msg, roles, client):
        self.message = msg
        self.roles = roles
        self.__playercount = len(roles) - 3
        self.players = []
        self.client = client
        self.completed = False
        self.game_log = []

    async def add_player(self, player):
        if len(self.players) < self.__playercount:
            self.players.append(player)
            return True
        else:
            return False

    async def check_start(self):
        if len(self.players) == self.__playercount:
            self.started = True
            self.task = self.client.loop.create_task(self.start())

    async def remove_player(self, player):
        if self.started: return False
        try:
            self.players.remove(player)
            return True
        except ValueError:
            return False

    def get_max_players(self):
        return self.__playercount

    def cancel(self):
        if self.task: self.task.cancel()
        self.task = None

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
        initial_player_and_role_list: List[Tuple[Role, discord.User]] = list(zip(role_obj_list, self.players))

        for i in player_and_role_list:
            await i[1].send(f'Your secret role is {i[0].name}! (lobby id: {self.message.id})')

        await self.message.channel.send("== **DEALT ROLES** ==")
        self.game_log.append(f"Roles dealt: {', '.join(map(lambda x: f'{x[1].display_name}: {x[0].name}', player_and_role_list))}")

        # == NIGHT PHASE ==

        for i in wake_order:
            await self.message.channel.send(
                f"== **THE {i.name_plural.upper() if i.max_count > 1 else i.name.upper()} RISE{'' if i.max_count > 1 else 'S'} FROM THEIR SLUMBER** ==\nThey have 30 seconds to select an action."
            )

            players_for_role = [
                y[1] for y in initial_player_and_role_list
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
                    if resp is None:
                        await player.send("You made no selection!")
                    else:
                        v = resp.content.strip(string.ascii_letters).split()

                        if len(v) > 1:  # Did they select two centre cards?
                            try:
                                a = centre[int(v[0]) - 1]
                                b = centre[int(v[1]) - 1]
                                await player.send(f"You see the following centre cards: {a.name}, {b.name}.")
                                self.game_log.append(f"The Seer ({player.display_name}) peeks at {a.name} ({int(v[0])}) and {b.name} ({int(v[1])}) in the centre.")
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
                                self.game_log.append(f"The Seer ({player.display_name}) peeks at {a.display_name}'s card and sees {b.name}")
                            except:
                                await player.send("Invalid selection!")

                elif i.name == WEREWOLF[0]:
                    for p in players_for_role:
                        await p.send(
                            f"You see the Werewolves are {', '.join(map(lambda x: x.display_name, players_for_role))}.")

                    self.game_log.append(f"The Werewolves see each other: {', '.join(map(lambda x: x.display_name, players_for_role))}")

                    if len(players_for_role) == 1:
                        message = await player.send(
                            "As the Lone Werewolf, you may peek at a centre card.")
                        resp = await self.get_response_by(players_for_role, message.channel)
                        if resp is None:
                            await player.send("You made no selection!")
                        else:
                            v = resp.content.strip(string.ascii_letters)

                            try:
                                a = centre[int(v) - 1]
                                await player.send(f"You see the following centre card: {a.name}.")
                                self.game_log.append(f"The Lone Werewolf peeks at the centre card {a.name} ({int(v)})")
                            except:
                                await player.send("Invalid selection!")
                elif i.name == MINION[0]:
                    await player.send(
                        f"You see the Werewolves are: {', '.join(map(lambda x: x.display_name, [y[1] for y in initial_player_and_role_list if y[0].name == WEREWOLF[0]]))}.")
                    self.game_log.append(f"The Minion ({player.display_name}) sees the Werewolves: {', '.join(map(lambda x: x.display_name, [y[1] for y in initial_player_and_role_list if y[0].name == WEREWOLF[0]]))}")
                elif i.name == MASON[0]:
                    for p in players_for_role:
                        await p.send(
                            f"You see the masons are {', '.join(map(lambda x: x.display_name, players_for_role))}.")
                    self.game_log.append(f"The Masons see each other: {', '.join(map(lambda x: x.display_name, players_for_role))}")
                elif i.name == ROBBER[0]:
                    message = await player.send(
                        "Select another player to swap cards with (type their number)."
                        f"\nPlayers (for reference): {', '.join(list(map(lambda x: '[' + str(self.players.index(x) + 1) + '] ' + x.display_name, self.players)))}")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    if resp is None:
                        await player.send("You made no selection!")
                    else:
                        v = resp.content.strip(string.ascii_letters)

                        try:
                            a = int(v) - 1

                            b = player_and_role_list.index((i, player))

                            assert a != b

                            cache_a_role = player_and_role_list[a][0]
                            player_and_role_list[a] = (player_and_role_list[b][0], player_and_role_list[a][1])
                            player_and_role_list[b] = (cache_a_role, player_and_role_list[b][1])

                            await player.send(f"You see your role as {player_and_role_list[b][0].name}.")
                            self.game_log.append(f"The Robber ({player.display_name}) swaps their card with {player_and_role_list[a][1].display_name} and receives {cache_a_role.name}")
                        except:
                            await player.send("Invalid selection!")
                elif i.name == TROUBLEMAKER[0]:
                    message = await player.send(
                        "Select two other players to swap cards (type their numbers, space separated)."
                        f"\nPlayers (for reference): {', '.join(list(map(lambda x: '[' + str(self.players.index(x) + 1) + '] ' + x.display_name, self.players)))}")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    if resp is None:
                        await player.send("You made no selection!")
                    else:
                        v = resp.content.strip(string.ascii_letters).split()

                        try:
                            a = int(v[0]) - 1
                            b = int(v[1]) - 1

                            idx = player_and_role_list.index((i, player))

                            assert a != idx and b != idx and a != b

                            cache_a_role = player_and_role_list[a][0]
                            player_and_role_list[a] = (player_and_role_list[b][0], player_and_role_list[a][1])
                            player_and_role_list[b] = (cache_a_role, player_and_role_list[b][1])

                            self.game_log.append(f"The Troublemaker ({player.display_name}) swaps the cards of {player_and_role_list[a][1]} (had {cache_a_role.name}) and {player_and_role_list[b][1]} (had {player_and_role_list[a][0]}).")
                        except:
                            await player.send("Invalid selection!")
                elif i.name == INSOMNIAC[0]:
                    b = [
                        y[0] for y in player_and_role_list
                        if y[1].id == player.id
                    ][0]
                    await player.send(f"You see your role as {b.name}.")
                    self.game_log.append(f"The Insomniac ({player.display_name}) sees themselves: {b.name}")
                elif i.name == DRUNK[0]:
                    message = await player.send(
                        "Select a centre card to swap with.")
                    resp = await self.get_response_by(players_for_role, message.channel)
                    if resp is None:
                        v = random.choice([1, 2, 3])
                    else:
                        v = resp.content.strip(string.ascii_letters)

                    try:
                        card = centre[int(v) - 1]
                        await player.send(f"You swap your card with centre card #{v}.")

                        player_and_role_list[player_and_role_list.index((i, player))] = (card, player)
                        centre[int(v) - 1] = i

                        self.game_log.append(f"The Drunk ({player.display_name}) swaps their card to {card.name} ({int(v)})")
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
        deaths = [death]

        # == GAME END ==

        await self.message.channel.send("== **GAME END** ==")
        await self.message.channel.send(f"{death[1].display_name} has been killed.")
        vote_block = ""

        for v in votes.keys():
            vote_block += f"+ {v.display_name} (voted for {col[self.players.index(v)]} time{'' if col[self.players.index(v)] == 1 else 's'}) voted for {self.players[votes[v]].display_name}\n"

        await self.message.channel.send(vote_block)
        # await self.message.channel.send(votes)
        # await self.message.channel.send(col)

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
                await self.message.channel.send("== **THE HUNTER HAS BEEN KILLED** ==")

                await asyncio.sleep(2)

                await self.message.channel.send(f'{player_and_role_list[votes[death[1]]][1].display_name} was shot by the Hunter.')
                death = player_and_role_list[votes[death[1]]]
                if death not in deaths:
                    deaths.append(death)
                else:  # The only way for this to happen is if two Hunters kill each other (?)
                    await self.message.channel.send("But they were already dead!")
                    winning_team = 'Werewolves'
                    reason = 'Multiple villagers have been killed'
                    winners = [
                        x[1].display_name for x in player_and_role_list
                        if x[0].ww
                    ]
            else:
                winning_team = 'Werewolves'
                reason = 'A Villager has been killed'
                winners = [
                    x[1].display_name for x in player_and_role_list
                    if x[0].ww
                ]

        await asyncio.sleep(2)

        await self.message.channel.send(f"== {reason}. {winning_team} win the game. ==")

        if len(deaths) == self.__playercount:
            await self.message.channel.send("The Village has been massacred.")

        await self.message.channel.send(f"Winners: {', '.join(winners)}.")

        await self.message.channel.send(
            f"Roles: {', '.join(map(lambda x: f'{x[1].display_name}: {x[0].name}', player_and_role_list))}.")

        self.completed = True

        await self.message.channel.send(f"== **GAME LOG** ==")
        await self.message.channel.send("\n".join(map(lambda x: f"{x[0]}. {x[1]}", enumerate(self.game_log))))
