import asyncio
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils import storage

TICKET_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "ticket_logo.png"

DEFAULT_TICKET_MESSAGE = (
    "Bonjour {membre}, merci de décrire ta demande ici.\n"
    "Un membre de l'équipe va te répondre dès que possible."
)


def get_config(guild_id: int) -> dict:
    data = storage.load("tickets_config")
    return data.get(str(guild_id), {"categories": {}})


def save_config(guild_id: int, conf: dict) -> None:
    data = storage.load("tickets_config")
    data[str(guild_id)] = conf
    storage.save("tickets_config", data)


async def category_name_autocomplete(interaction: discord.Interaction, current: str):
    conf = get_config(interaction.guild_id)
    names = list(conf.get("categories", {}).keys())
    return [
        app_commands.Choice(name=n, value=n)
        for n in names
        if current.lower() in n.lower()
    ][:25]


# ---------------------------------------------------------------------------
# Vues persistantes
# ---------------------------------------------------------------------------

class TicketPanelSelect(discord.ui.Select):
    def __init__(self, categories: dict | None = None):
        options = []
        if categories:
            for name, info in categories.items():
                options.append(
                    discord.SelectOption(
                        label=name[:100],
                        description=(info.get("description") or None),
                        emoji=info.get("emoji") or None,
                    )
                )
        if not options:
            options = [discord.SelectOption(label="Aucune catégorie configurée", value="__none__")]

        super().__init__(
            placeholder="Choisissez une catégorie pour ouvrir un ticket",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_panel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "__none__":
            await interaction.response.send_message("❌ Aucune catégorie n'est configurée pour le moment.", ephemeral=True)
            return

        conf = get_config(interaction.guild_id)
        cat_info = conf.get("categories", {}).get(value)
        if not cat_info:
            await interaction.response.send_message("❌ Cette catégorie n'existe plus.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # Empêche les doublons de ticket pour un même membre / catégorie
        open_tickets = storage.load("tickets_open")
        for cid, info in open_tickets.items():
            if (
                info.get("guild_id") == guild.id
                and info.get("opener_id") == interaction.user.id
                and info.get("category_name") == value
            ):
                existing = guild.get_channel(int(cid))
                if existing:
                    await interaction.followup.send(
                        f"❗ Vous avez déjà un ticket ouvert : {existing.mention}", ephemeral=True
                    )
                    return

        discord_category = guild.get_channel(cat_info.get("discord_category_id"))

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True, read_message_history=True
            ),
        }

        ping_role = None
        role_id = cat_info.get("ping_role_id")
        if role_id:
            ping_role = guild.get_role(role_id)
            if ping_role:
                overwrites[ping_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        channel_name = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:90]

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=discord_category if isinstance(discord_category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                topic=f"Ticket ouvert par {interaction.user} ({interaction.user.id}) | Catégorie: {value}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Le bot n'a pas la permission de créer un salon. Vérifie ses permissions.", ephemeral=True
            )
            return

        open_tickets[str(ticket_channel.id)] = {
            "guild_id": guild.id,
            "opener_id": interaction.user.id,
            "category_name": value,
        }
        storage.save("tickets_open", open_tickets)

        message_template = cat_info.get("message") or DEFAULT_TICKET_MESSAGE
        description = message_template.replace("{membre}", interaction.user.mention).replace(
            "{categorie}", value
        )

        embed = discord.Embed(
            title=f"🎫 Ticket — {value}",
            description=description,
            color=discord.Color.green(),
        )

        content = interaction.user.mention
        if ping_role:
            content += f" {ping_role.mention}"

        logo_file = None
        if TICKET_LOGO_PATH.exists():
            logo_file = discord.File(TICKET_LOGO_PATH, filename="logo.png")
            embed.set_thumbnail(url="attachment://logo.png")

        kwargs = {"content": content, "embed": embed, "view": TicketCloseView()}
        if logo_file:
            kwargs["file"] = logo_file

        await ticket_channel.send(**kwargs)
        await interaction.followup.send(f"✅ Ton ticket a été créé : {ticket_channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    """Vue persistante affichée dans le panneau /ticket setup."""

    def __init__(self, bot: commands.Bot | None = None, categories: dict | None = None):
        super().__init__(timeout=None)
        self.add_item(TicketPanelSelect(categories))


class TicketCloseView(discord.ui.View):
    """Vue persistante avec le bouton de fermeture, présente dans chaque ticket."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        open_tickets = storage.load("tickets_open")
        info = open_tickets.get(str(interaction.channel_id))
        if not info:
            await interaction.response.send_message("❌ Ce salon n'est pas reconnu comme un ticket.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Ce ticket va être fermé dans 5 secondes...")
        open_tickets.pop(str(interaction.channel_id), None)
        storage.save("tickets_open", open_tickets)

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Gérer le système de tickets")

    @ticket_group.command(name="setup", description="Affiche le panneau d'ouverture de tickets dans ce salon")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_setup(self, interaction: discord.Interaction):
        conf = get_config(interaction.guild_id)
        categories = conf.get("categories", {})

        embed = discord.Embed(
            title="🎫 Support — Ouvrir un ticket",
            description="Sélectionne une catégorie ci-dessous pour ouvrir un ticket privé avec l'équipe.",
            color=discord.Color.blurple(),
        )
        if not categories:
            embed.set_footer(text="⚠️ Aucune catégorie n'est encore configurée (utilise /ticket add).")

        view = TicketPanelView(categories=categories)
        await interaction.response.send_message(embed=embed, view=view)

    @ticket_group.command(name="add", description="Ajoute une catégorie de ticket")
    @app_commands.describe(
        nom="Nom de la catégorie (ex: Support, Signalement...)",
        categorie="Catégorie Discord dans laquelle créer les salons de ticket",
        emoji="Emoji affiché dans le menu (optionnel)",
        description="Courte description affichée dans le menu (optionnel)",
        message="Texte affiché dans le ticket à l'ouverture (optionnel). Utilise {membre} pour mentionner l'ouvreur.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_add(
        self,
        interaction: discord.Interaction,
        nom: str,
        categorie: discord.CategoryChannel,
        emoji: str = None,
        description: str = None,
        message: str = None,
    ):
        conf = get_config(interaction.guild_id)
        conf.setdefault("categories", {})
        existing = conf["categories"].get(nom, {})
        conf["categories"][nom] = {
            "discord_category_id": categorie.id,
            "emoji": emoji,
            "description": description,
            "message": message,
            "ping_role_id": existing.get("ping_role_id"),
        }
        save_config(interaction.guild_id, conf)
        await interaction.response.send_message(
            f"✅ Catégorie de ticket `{nom}` ajoutée → salons créés dans **{categorie.name}**.\n"
            f"N'oublie pas de relancer `/ticket setup` pour mettre à jour le panneau.",
            ephemeral=True,
        )

    @ticket_group.command(name="edit", description="Modifie une catégorie de ticket existante")
    @app_commands.describe(
        nom="Nom de la catégorie à modifier",
        categorie="Nouvelle catégorie Discord (optionnel)",
        emoji="Nouvel emoji (optionnel)",
        description="Nouvelle description (optionnel)",
        message="Nouveau texte affiché dans le ticket (optionnel). Utilise {membre} pour mentionner l'ouvreur.",
    )
    @app_commands.autocomplete(nom=category_name_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_edit(
        self,
        interaction: discord.Interaction,
        nom: str,
        categorie: discord.CategoryChannel = None,
        emoji: str = None,
        description: str = None,
        message: str = None,
    ):
        conf = get_config(interaction.guild_id)
        cat = conf.get("categories", {}).get(nom)
        if not cat:
            await interaction.response.send_message(f"❌ Aucune catégorie nommée `{nom}` n'existe.", ephemeral=True)
            return

        if categorie:
            cat["discord_category_id"] = categorie.id
        if emoji:
            cat["emoji"] = emoji
        if description:
            cat["description"] = description
        if message:
            cat["message"] = message

        save_config(interaction.guild_id, conf)
        await interaction.response.send_message(
            f"✅ Catégorie `{nom}` mise à jour. Relance `/ticket setup` pour actualiser le panneau.", ephemeral=True
        )

    @ticket_group.command(name="sup", description="Supprime une catégorie de ticket")
    @app_commands.describe(nom="Nom de la catégorie à supprimer")
    @app_commands.autocomplete(nom=category_name_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_sup(self, interaction: discord.Interaction, nom: str):
        conf = get_config(interaction.guild_id)
        if nom not in conf.get("categories", {}):
            await interaction.response.send_message(f"❌ Aucune catégorie nommée `{nom}` n'existe.", ephemeral=True)
            return

        del conf["categories"][nom]
        save_config(interaction.guild_id, conf)
        await interaction.response.send_message(
            f"✅ Catégorie `{nom}` supprimée. Relance `/ticket setup` pour actualiser le panneau.", ephemeral=True
        )

    @ticket_group.command(name="ping", description="Définit le rôle notifié à l'ouverture d'un ticket")
    @app_commands.describe(nom="Nom de la catégorie", role="Rôle à mentionner à l'ouverture du ticket")
    @app_commands.autocomplete(nom=category_name_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_ping(self, interaction: discord.Interaction, nom: str, role: discord.Role):
        conf = get_config(interaction.guild_id)
        cat = conf.get("categories", {}).get(nom)
        if not cat:
            await interaction.response.send_message(f"❌ Aucune catégorie nommée `{nom}` n'existe.", ephemeral=True)
            return

        cat["ping_role_id"] = role.id
        save_config(interaction.guild_id, conf)
        await interaction.response.send_message(
            f"✅ Le rôle {role.mention} sera notifié et ajouté aux tickets de catégorie `{nom}`.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
