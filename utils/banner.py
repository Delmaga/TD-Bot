"""
Génère une bannière de bienvenue (PNG) avec l'avatar et le nom du membre,
sur fond de l'image de marque fournie (assets/welcome_background.jpg).

Pour un rendu plus soigné, tu peux déposer des polices .ttf dans
assets/fonts/ (ex: Poppins-Bold.ttf et Poppins-Regular.ttf).
Si elles sont absentes, une police par défaut est utilisée automatiquement.
"""
import io
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONT_BOLD = ASSETS_DIR / "fonts" / "Poppins-Bold.ttf"
FONT_REGULAR = ASSETS_DIR / "fonts" / "Poppins-Regular.ttf"
BACKGROUND_IMAGE = ASSETS_DIR / "welcome_background.jpg"

# Couleurs reprises de la charte de la bannière (doré / bleu nuit)
GOLD = (198, 161, 91)
GOLD_LIGHT = (231, 202, 148)
NAVY_DARK = (10, 9, 15)


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
    # --- Fond : l'illustration de marque fournie, jamais recouverte ---
    artwork = Image.open(BACKGROUND_IMAGE).convert("RGBA")
    width, art_height = artwork.size

    # On ajoute une bande en bas pour l'avatar + le pseudo, sans toucher au visuel d'origine
    pad_top = 30
    avatar_size = 128
    ring_pad = 6
    gap_avatar_name = 18
    gap_name_sub = 46
    pad_bottom = 34
    footer_height = pad_top + (avatar_size + ring_pad * 2) + gap_avatar_name + gap_name_sub + pad_bottom
    height = art_height + footer_height

    base = Image.new("RGBA", (width, height), NAVY_DARK + (255,))
    base.paste(artwork, (0, 0))

    draw = ImageDraw.Draw(base)

    # Dégradé de raccord entre l'image et la bande du bas (mêmes tons que le bas de l'image)
    blend_h = 40
    top_c = (58, 44, 44)
    for y in range(blend_h):
        ratio = y / blend_h
        r = int(top_c[0] + (NAVY_DARK[0] - top_c[0]) * ratio)
        g = int(top_c[1] + (NAVY_DARK[1] - top_c[1]) * ratio)
        b = int(top_c[2] + (NAVY_DARK[2] - top_c[2]) * ratio)
        draw.line([(0, art_height + y), (width, art_height + y)], fill=(r, g, b, 255))
    draw.rectangle([0, art_height + blend_h, width, height], fill=NAVY_DARK + (255,))

    # Fine ligne dorée séparatrice
    draw.line([(0, art_height), (width, art_height)], fill=GOLD + (140,), width=2)

    # --- Avatar avec anneau doré, centré dans la bande du bas ---
    avatar_url = str(member.display_avatar.replace(size=256, format="png").url)
    avatar_bytes = await _fetch_bytes(avatar_url)
    avatar_img = _circle_avatar(avatar_bytes, avatar_size)

    ring = Image.new("RGBA", (avatar_size + ring_pad * 2, avatar_size + ring_pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse(
        (0, 0, avatar_size + ring_pad * 2, avatar_size + ring_pad * 2),
        fill=GOLD + (255,),
    )
    ring.paste(avatar_img, (ring_pad, ring_pad), avatar_img)

    avatar_x = width // 2 - (avatar_size + ring_pad * 2) // 2
    avatar_y = art_height + pad_top
    base.paste(ring, (avatar_x, avatar_y), ring)

    # --- Textes : pseudo + sous-texte ---
    name_font = _load_font(FONT_BOLD, 34)
    sub_font = _load_font(FONT_REGULAR, 20)

    name_text = member.display_name
    nw = draw.textlength(name_text, font=name_font)
    name_y = avatar_y + avatar_size + ring_pad * 2 + gap_avatar_name
    draw.text(((width - nw) / 2, name_y), name_text, font=name_font, fill=GOLD_LIGHT + (255,))

    member_count = getattr(member.guild, "member_count", None)
    sub_text = f"a rejoint {guild_name} • Membre #{member_count}" if member_count else f"a rejoint {guild_name}"
    sw = draw.textlength(sub_text, font=sub_font)
    draw.text(((width - sw) / 2, name_y + gap_name_sub), sub_text, font=sub_font, fill=(190, 185, 200, 255))

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
