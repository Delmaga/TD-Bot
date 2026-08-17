import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True          # nécessaire pour /welcome (on_member_join)
intents.message_content = True  # nécessaire pour /say, /sayedit


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        for ext in ("cogs.welcome", "cogs.tickets", "cogs.say", "cogs.social"):
            await self.load_extension(ext)

        # Enregistre les vues persistantes (boutons/select qui survivent aux redémarrages)
        from cogs.tickets import TicketPanelView, TicketCloseView

        self.add_view(TicketPanelView(self))
        self.add_view(TicketCloseView())

        synced = await self.tree.sync()
        print(f"✅ {len(synced)} commandes slash synchronisées.")

    async def on_ready(self):
        print(f"✅ Connecté en tant que {self.user} (ID: {self.user.id})")


bot = MyBot()


async def main():
    if not TOKEN:
        raise SystemExit("❌ Aucun token trouvé. Configure DISCORD_TOKEN dans le fichier .env")
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
