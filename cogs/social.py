import discord
from discord import app_commands
from discord.ext import commands


class Social(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="web", description="Partage un lien de site web")
    @app_commands.describe(lien="L'URL du site web")
    async def web(self, interaction: discord.Interaction, lien: str):
        embed = discord.Embed(
            title="🌐 Site Web",
            description=f"[Cliquez ici pour visiter le site]({lien})",
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Partagé par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="twitch", description="Partage un lien Twitch")
    @app_commands.describe(lien="L'URL de la chaîne Twitch")
    async def twitch(self, interaction: discord.Interaction, lien: str):
        embed = discord.Embed(
            title="🟣 Twitch",
            description=f"[Cliquez ici pour rejoindre le stream]({lien})",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Partagé par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tiktok", description="Partage un lien TikTok")
    @app_commands.describe(lien="L'URL TikTok")
    async def tiktok(self, interaction: discord.Interaction, lien: str):
        embed = discord.Embed(
            title="🎵 TikTok",
            description=f"[Cliquez ici pour voir]({lien})",
            color=discord.Color.from_rgb(20, 20, 20),
        )
        embed.set_footer(text=f"Partagé par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))
