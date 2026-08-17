"""
Génère une bannière de bienvenue (PNG) avec l'avatar et le nom du membre.

Pour un rendu plus soigné, tu peux déposer des polices .ttf dans
assets/fonts/ (ex: Poppins-Bold.ttf et Poppins-Regular.ttf).
Si elles sont absentes, une police par défaut est utilisée automatiquement.
"""
import io
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_BOLD = ASSETS_DIR / "Poppins-Bold.ttf"
FONT_REGULAR = ASSETS_DIR / "Poppins-Regular.ttf"


async def _fetch_bytes(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()


def _circle_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size))
    result.paste(img, (0, 0), mask)
    return result


def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()


async def create_welcome_banner(member, guild_name: str) -> io.BytesIO:
    width, height = 1000, 350
    base = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(base)

    # Fond en dégradé
    top_color = (32, 34, 68)
    bottom_color = (10, 11, 26)
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Avatar avec anneau
    avatar_url = str(member.display_avatar.replace(size=256, format="png").url)
    avatar_bytes = await _fetch_bytes(avatar_url)
    avatar_size = 180
    avatar_img = _circle_avatar(avatar_bytes, avatar_size)

    ring_pad = 8
    ring = Image.new("RGBA", (avatar_size + ring_pad * 2, avatar_size + ring_pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse(
        (0, 0, avatar_size + ring_pad * 2, avatar_size + ring_pad * 2),
        fill=(88, 101, 242, 255),
    )
    ring.paste(avatar_img, (ring_pad, ring_pad), avatar_img)

    avatar_x = (width - avatar_size) // 2
    avatar_y = 55
    base.paste(ring, (avatar_x - ring_pad, avatar_y - ring_pad), ring)

    # Textes
    title_font = _load_font(FONT_BOLD, 46)
    sub_font = _load_font(FONT_REGULAR, 26)

    title_text = "BIENVENUE"
    tw = draw.textlength(title_text, font=title_font)
    draw.text(((width - tw) / 2, avatar_y + avatar_size + 25), title_text, font=title_font, fill=(255, 255, 255, 255))

    name_text = str(member)
    nw = draw.textlength(name_text, font=sub_font)
    draw.text(((width - nw) / 2, avatar_y + avatar_size + 88), name_text, font=sub_font, fill=(190, 195, 235, 255))

    member_count = getattr(member.guild, "member_count", None)
    sub_text = f"{guild_name} • Membre #{member_count}" if member_count else guild_name
    sw = draw.textlength(sub_text, font=sub_font)
    draw.text(((width - sw) / 2, avatar_y + avatar_size + 128), sub_text, font=sub_font, fill=(140, 145, 180, 255))

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
