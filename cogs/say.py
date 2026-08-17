import discord
from discord import app_commands
from discord.ext import commands

from utils import storage


def _build_payload(titre: str, contenu: str, image_url: str, lien_url: str, lien_texte: str, ping_mention: str | None):
    """Construit (content, embed, view) à partir des champs de la modale."""
    embed = None
    if titre or image_url:
        embed = discord.Embed(description=contenu, color=discord.Color.blurple())
        if titre:
            embed.title = titre
        if image_url:
            embed.set_image(url=image_url)

    content = contenu if embed is None else None
    if ping_mention:
        content = f"{ping_mention}\n{content}" if content else ping_mention

    view = None
    if lien_url:
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=(lien_texte or "🔗 En savoir plus"), url=lien_url, style=discord.ButtonStyle.link))

    return content, embed, view


class SayModal(discord.ui.Modal):
    def __init__(self, cog: "Say", salon: discord.TextChannel, role: discord.Role = None,
                 membre: discord.Member = None, edit_message_id: str = None, prefill: dict = None):
        super().__init__(title="Modifier le message" if edit_message_id else "Nouveau message")
        self.cog = cog
        self.salon = salon
        self.role = role
        self.membre = membre
        self.edit_message_id = edit_message_id
        prefill = prefill or {}

        self.titre = discord.ui.TextInput(
            label="Titre (optionnel)",
            style=discord.TextStyle.short,
            required=False,
            max_length=256,
            default=prefill.get("title") or None,
        )
        self.contenu = discord.ui.TextInput(
            label="Contenu",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
            default=prefill.get("content") or None,
            placeholder="Ton texte ici. **gras**, *italique*, retours à la ligne, liens... tout fonctionne.",
        )
        self.image_url = discord.ui.TextInput(
            label="Image (URL, optionnel)",
            style=discord.TextStyle.short,
            required=False,
            max_length=500,
            default=prefill.get("image_url") or None,
        )
        self.lien_url = discord.ui.TextInput(
            label="Lien du bouton (URL, optionnel)",
            style=discord.TextStyle.short,
            required=False,
            max_length=500,
            default=prefill.get("lien_url") or None,
        )
        self.lien_texte = discord.ui.TextInput(
            label="Texte du bouton (optionnel)",
            style=discord.TextStyle.short,
            required=False,
            max_length=80,
            default=prefill.get("lien_label") or None,
        )

        for item in (self.titre, self.contenu, self.image_url, self.lien_url, self.lien_texte):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        ping_mention = None
        if self.role:
            ping_mention = self.role.mention
        elif self.membre:
            ping_mention = self.membre.mention

        content, embed, view = _build_payload(
            self.titre.value, self.contenu.value, self.image_url.value,
            self.lien_url.value, self.lien_texte.value, ping_mention,
        )

        try:
            if self.edit_message_id:
                msg = await self.salon.fetch_message(int(self.edit_message_id))
                await msg.edit(content=content, embed=embed, view=view)
                action = "modifié"
            else:
                msg = await self.salon.send(content=content, embed=embed, view=view)
                action = "envoyé"
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Le bot n'a pas la permission d'écrire/modifier dans ce salon.", ephemeral=True
            )
            return
        except discord.NotFound:
            await interaction.response.send_message("❌ Ce message n'existe plus.", ephemeral=True)
            return

        data = storage.load("say_messages")
        data[str(msg.id)] = {
            "channel_id": self.salon.id,
            "guild_id": interaction.guild_id,
            "title": self.titre.value or None,
            "content": self.contenu.value,
            "image_url": self.image_url.value or None,
            "lien_url": self.lien_url.value or None,
            "lien_label": self.lien_texte.value or None,
            "ping_type": "role" if self.role else ("member" if self.membre else None),
            "ping_id": self.role.id if self.role else (self.membre.id if self.membre else None),
        }
        storage.save("say_messages", data)

        await interaction.response.send_message(
            f"✅ Message {action} dans {self.salon.mention}.\n🆔 ID du message : `{msg.id}`", ephemeral=True
        )


class Say(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="say", description="Ouvre une fenêtre pour composer un message envoyé par le bot")
    @app_commands.describe(
        salon="Salon cible (optionnel, sinon salon actuel)",
        role="Rôle à mentionner (optionnel)",
        membre="Membre à mentionner (optionnel)",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(
        self,
        interaction: discord.Interaction,
        salon: discord.TextChannel = None,
        role: discord.Role = None,
        membre: discord.Member = None,
    ):
        target = salon or interaction.channel
        modal = SayModal(self, target, role=role, membre=membre)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="sayedit", description="Modifie un message envoyé via /say (ouvre une fenêtre pré-remplie)")
    @app_commands.describe(
        message_id="L'ID du message à modifier",
        role="Nouveau rôle à mentionner (optionnel, sinon conservé)",
        membre="Nouveau membre à mentionner (optionnel, sinon conservé)",
    )
    async def sayedit(
        self,
        interaction: discord.Interaction,
        message_id: str,
        role: discord.Role = None,
        membre: discord.Member = None,
    ):
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
            await channel.fetch_message(int(message_id))
        except discord.NotFound:
            await interaction.response.send_message("❌ Ce message n'existe plus.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("❌ Le bot n'a pas accès à ce salon.", ephemeral=True)
            return

        # Conserve le ping existant si non précisé
        final_role = role
        final_membre = membre
        if not final_role and not final_membre and entry.get("ping_type"):
            if entry["ping_type"] == "role":
                final_role = interaction.guild.get_role(entry["ping_id"])
            elif entry["ping_type"] == "member":
                final_membre = interaction.guild.get_member(entry["ping_id"])

        prefill = {
            "title": entry.get("title"),
            "content": entry.get("content"),
            "image_url": entry.get("image_url"),
            "lien_url": entry.get("lien_url"),
            "lien_label": entry.get("lien_label"),
        }

        modal = SayModal(
            self, channel, role=final_role, membre=final_membre,
            edit_message_id=message_id, prefill=prefill,
        )
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(Say(bot))
