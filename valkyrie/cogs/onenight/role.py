import collections

Role = collections.namedtuple(
    'Role',
    ('name', 'name_plural', 'wake_id', 'max_count', 'ww', 'village')
)

# DOPPLEGANGER = ["Doppleganger", "Dopplegangers"]
WEREWOLF = ["Werewolf", "Werewolves"]
MINION = ["Minion", "Minions"]
MASON = ["Mason", "Masons"]
SEER = ["Seer", "Seers"]
ROBBER = ["Robber", "Robbers"]
TROUBLEMAKER = ["Troublemaker", "Troublemakers"]
DRUNK = ["Drunk", "Drunks"]
INSOMNIAC = ["Insomniac", "Insomniacs"]

TANNER = ["Tanner", "Tanners"]
HUNTER = ["Hunter", "Hunters"]

ROLES = [
    # Role(*DOPPLEGANGER, 1, 1),
    Role(*WEREWOLF, 2, 3, True, False),
    Role(*MINION, 3, 1, True, False),
    Role(*MASON, 4, 2, False, True),
    Role(*SEER, 5, 1, False, True),
    Role(*ROBBER, 6, 1, False, True),
    Role(*TROUBLEMAKER, 7, 1, False, True),
    Role(*DRUNK, 8, 1, False, True),
    Role(*INSOMNIAC, 9, 1, False, True),
    Role(*TANNER, None, 1, False, False),
    Role(*HUNTER, None, 1, False, True),
]
