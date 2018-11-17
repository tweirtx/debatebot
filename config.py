import json
import os


class Config:
    CONFIG = {
        'discord_token': "Put Discord API Token here.",
        'db_url': "sqlite:///debatebot.db"
    }
    CONFIG_FILE = 'config.json'

    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            CONFIG.update(json.load(f))

    with open('config.json', 'w') as f:
        json.dump(CONFIG, f, indent='\t')
