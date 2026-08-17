import discord
from discord import app_commands
from discord.ext import commands

from utils import storage


class Say(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="say", description="Fait envoyer un message par le bot")
    @app_commands.describe(message="Le message à envoyer", salon="Salon cible (optionnel, sinon salon actuel)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(self, interaction: discord.Interaction, message: str, salon: discord.TextChannel = None):
        target = salon or interaction.channel
        sent = await target.send(message)

        data = storage.load("say_messages")
        data[str(sent.id)] = {"channel_id": target.id, "guild_id": interaction.guild_id}
        storage.save("say_messages", data)

        await interaction.response.send_message(
            f"✅ Message envoyé dans {target.mention}.\n🆔 ID du message : `{sent.id}`", ephemeral=True
        )

    @app_commands.command(name="sayedit", description="Modifie un message envoyé via /say (à partir de son ID)")
    @app_commands.describe(message_id="L'ID du message à modifier", nouveau_message="Le nouveau contenu du message")
    async def sayedit(self, interaction: discord.Interaction, message_id: str, nouveau_message: str):
        data = storage.load("say_messages")
        entry = data.get(message_id)

        if not entry or entry.get("guild_id") != interaction.guild_id:
            await interaction.response.send_message(
                "❌ Ce message est introuvable (ou n'a pas été envoyé via `/say` sur ce serveur).", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(entry["channel_id"])
        if channel is None:
            await interaction.response.send_message("❌ Le salon d'origine est introuvable.", ephemeral=True)
            return

        try:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(content=nouveau_message)
        except discord.NotFound:
            await interaction.response.send_message("❌ Ce message n'existe plus.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("❌ Le bot n'a pas la permission de modifier ce message.", ephemeral=True)
            return

        await interaction.response.send_message("✅ Message modifié avec succès.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Say(bot))
