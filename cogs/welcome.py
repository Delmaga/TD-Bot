import discord
from discord import app_commands
from discord.ext import commands

from utils import storage
from utils.banner import create_welcome_banner


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    welcome_group = app_commands.Group(name="welcome", description="Configurer les messages de bienvenue")

    @welcome_group.command(name="salon", description="Définit le salon des messages de bienvenue")
    @app_commands.describe(salon="Le salon où seront envoyés les messages de bienvenue")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_salon(self, interaction: discord.Interaction, salon: discord.TextChannel):
        data = storage.load("welcome")
        data[str(interaction.guild_id)] = {"channel_id": salon.id}
        storage.save("welcome", data)
        await interaction.response.send_message(
            f"✅ Le salon de bienvenue est maintenant {salon.mention}.", ephemeral=True
        )

    @welcome_group.command(name="test", description="Envoie un message de bienvenue de test")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ok = await self.send_welcome(interaction.user, interaction.guild)
        if ok:
            await interaction.followup.send("✅ Message de bienvenue de test envoyé.", ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Aucun salon de bienvenue configuré. Utilise `/welcome salon` d'abord.", ephemeral=True
            )

    async def send_welcome(self, member: discord.Member, guild: discord.Guild) -> bool:
        data = storage.load("welcome")
        conf = data.get(str(guild.id))
        if not conf:
            return False
        channel = guild.get_channel(conf["channel_id"])
        if channel is None:
            return False

        buf = await create_welcome_banner(member, guild.name)
        file = discord.File(buf, filename="welcome.png")
        embed = discord.Embed(
            description=f"👋 {member.mention} bienvenue sur **{guild.name}** !",
            color=discord.Color.blurple(),
        )
        embed.set_image(url="attachment://welcome.png")
        await channel.send(embed=embed, file=file)
        return True

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send_welcome(member, member.guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
