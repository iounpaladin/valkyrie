import re

import requests
from bs4 import BeautifulSoup as BS

content = requests.get("https://discordpy.readthedocs.io/en/latest/api.html").content
bs = BS(content)

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
""".split()

regex = re.compile(r'\(.+?\)')

if __name__ == '__main__':
    for hook in valid_hooks:
        q = bs.find('dt', {'id': f'discord.on_{hook}'}).get_text()
        args = regex.findall(q)[0][1:-1]
        args_as_map = ', '.join([f'"{x}": {x}' for x in args.split(", ")])
        print(f"""@commands.Cog.listener()
async def on_{hook}(self, {args}):
    await self.run_hook('{hook}', {{{args_as_map}}})""")
