import os
from bot import bot, keep_alive

keep_alive()

bot.run(os.getenv("DISCORD_TOKEN"))
