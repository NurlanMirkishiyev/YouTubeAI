"""FAZA F 3.6 / 5 - intro, outro, bolme basligi (lower-third) ve YouTube thumbnail (Pillow)."""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imaging import cut_side, fit_cover, is_bust  # noqa: E402

FONTS_DIR = r"C:\YouTubeAI\Assets\fonts"
FALLBACK_FONT = r"C:\Windows\Fonts\segoeuib.ttf"
W, H = 1920, 1080
THUMB_W, THUMB_H = 1280, 720
ACCENT = (255, 196, 0)
WHITE = (255, 255, 255)
PANEL = (15, 18, 28, 200)
BRAND = "ELI5 Business"


def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS_DIR, f"Montserrat-{weight}.ttf")
    if os.path.isfile(path):
        return ImageFont.truetype(path, size)
    print(f"  DIQQET: {path} yoxdur - {FALLBACK_FONT} istifade olunur")
    return ImageFont.truetype(FALLBACK_FONT, size)


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        test = f"{cur} {word}".strip()
        if not cur or font.getlength(test) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def backdrop(bg_path: str, size: tuple[int, int], blur: int, dim: float) -> Image.Image:
    with Image.open(bg_path) as im:
        img = fit_cover(im.convert("RGB"), *size)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return ImageEnhance.Brightness(img).enhance(1.0 - dim)


def paste_sprite(canvas: Image.Image, sprite_path: str, height: int, right: int, bottom: int) -> None:
    """Sprite-i hundurluye gore kicildib sag-asagi kunce yapisdirir (canvas yerinde deyisir).
    Bust sprite sag+alt kenara yapisir (right/bottom nezere alinmir), kesik terefi saga cevrilir."""
    with Image.open(sprite_path) as im:
        owl = im.convert("RGBA")
    owl = owl.resize((round(owl.width * height / owl.height), height), Image.LANCZOS)
    if is_bust(sprite_path):
        right = bottom = 0
        if cut_side(owl) == "left":
            owl = owl.transpose(Image.FLIP_LEFT_RIGHT)
    box = owl.getchannel("A").getbbox() or (0, 0, owl.width, owl.height)
    x = canvas.width - box[2] - right       # seffaf kenar bosluqlari hesaba alinmir
    y = canvas.height - box[3] - bottom
    canvas.paste(owl, (x, y), owl)


def _title_block(draw: ImageDraw.ImageDraw, lines: list[str], font, x: int, y: int, step: int) -> int:
    draw.rectangle((x - 50, y - 30, x - 38, y + len(lines) * step - 20), fill=ACCENT)
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=WHITE)
        y += step
    return y


def intro_card(title: str, bg_path: str, sprite_path: str, out: str) -> str:
    img = backdrop(bg_path, (W, H), blur=10, dim=0.45)
    draw = ImageDraw.Draw(img)
    font = load_font("ExtraBold", 96)
    lines = wrap(title, font, 1100)
    y = _title_block(draw, lines, font, 170, H // 2 - len(lines) * 110 // 2, 110)
    draw.text((170, y + 10), BRAND, font=load_font("SemiBold", 40), fill=ACCENT)
    paste_sprite(img, sprite_path, 620, 140, 60)
    img.save(out)
    return out


def outro_card(bg_path: str, sprite_path: str, out: str) -> str:
    img = backdrop(bg_path, (W, H), blur=10, dim=0.5)
    draw = ImageDraw.Draw(img)
    y = _title_block(draw, ["Thanks for watching!"], load_font("ExtraBold", 88), 170, 400, 110)
    draw.text((170, y + 10), f"Subscribe for more {BRAND}", font=load_font("SemiBold", 44), fill=ACCENT)
    paste_sprite(img, sprite_path, 600, 160, 60)
    img.save(out)
    return out


def lower_third(text: str, out: str) -> str:
    """Seffaf 1920x1080 kadr; panel yuxari-solda (sprite asagi kunclerde, subtitr asagi-merkezde)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = load_font("SemiBold", 44)
    x0, y0, tw = 70, 60, round(font.getlength(text))
    draw.rounded_rectangle((x0, y0, x0 + tw + 80, y0 + 84), radius=14, fill=PANEL)
    draw.rectangle((x0, y0, x0 + 10, y0 + 84), fill=ACCENT)
    draw.text((x0 + 40, y0 + 16), text, font=font, fill=WHITE)
    img.save(out)
    return out


def thumbnail(bg_path: str, sprite_path: str, text: str, out: str) -> str:
    img = backdrop(bg_path, (THUMB_W, THUMB_H), blur=0, dim=0.25)
    draw = ImageDraw.Draw(img)
    font = load_font("ExtraBold", 110)
    y = 90
    for ln in wrap(text, font, 700):
        draw.text((60, y), ln, font=font, fill=WHITE, stroke_width=8, stroke_fill=(0, 0, 0))
        y += 125
    paste_sprite(img, sprite_path, 640, 40, 0)
    img.save(out)
    return out
