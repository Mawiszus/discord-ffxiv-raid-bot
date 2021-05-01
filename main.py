import raidbot.bot as bot
from dotenv import load_dotenv
import os

if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot.run(TOKEN)

