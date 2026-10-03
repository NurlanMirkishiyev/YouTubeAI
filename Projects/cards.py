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


THUMB_TEXT_W = 700           # yazi sol ~60%-de, bayqus sagda
THUMB_LINES = 3
THUMB_SIZES = range(150, 63, -6)
INK = (8, 11, 20)


def fit_title(text: str, max_w: int, max_lines: int = THUMB_LINES) -> tuple[int, list[str]]:
    """En boyuk sriftle max_lines setre siganini secir (qisa basliq boyuk, uzun kicik)."""
    lines: list[str] = []
    for size in THUMB_SIZES:
        font = load_font("ExtraBold", size)
        lines = wrap(text, font, max_w)
        if len(lines) <= max_lines and all(font.getlength(ln) <= max_w for ln in lines):
            return size, lines
    return THUMB_SIZES[-1], lines


def _left_shade(size: tuple[int, int]) -> Image.Image:
    """Sol terefde yazi ucun tund kecid (sagda fon tam gorunur) + asagi kolge."""
    w, h = size
    shade = Image.new("L", size, 0)
    px = shade.load()
    edge = int(w * 0.66)
    for x in range(w):
        a = int(235 * max(0.0, 1 - x / edge) ** 1.1)
        for y in range(h):
            px[x, y] = max(a, int(120 * max(0.0, (y - h * 0.7) / (h * 0.3))))
    layer = Image.new("RGBA", size, INK + (0,))
    layer.putalpha(shade)
    return layer


def _thumb_base(bg_path: str | None) -> Image.Image:
    if bg_path:
        img = backdrop(bg_path, (THUMB_W, THUMB_H), blur=0, dim=0.0)
        img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(1.15)).enhance(1.08)
    else:                                   # foto yoxdursa - Remotion StudioBackdrop-a oxsar tund gradient
        img = Image.new("RGB", (THUMB_W, THUMB_H), (17, 26, 48))
    return Image.alpha_composite(img.convert("RGBA"), _left_shade((THUMB_W, THUMB_H)))


def _word_colour(word: str, highlight: str) -> tuple[int, int, int]:
    keys = {w.strip(".,!?:;'\"").lower() for w in highlight.split()}
    return ACCENT if word.strip(".,!?:;'\"").lower() in keys else WHITE


def _words(lines: list[str], font, step: int):
    """(x, y, soz) - sol kenardan, saquli merkezde."""
    y = (THUMB_H - step * len(lines)) // 2 + 30
    for ln in lines:
        x = 60
        for word in ln.split():
            yield x, y, word
            x += round(font.getlength(word + " "))
        y += step


def _draw_title(img: Image.Image, lines: list[str], size: int, highlight: str) -> None:
    """Evvel yumsaq kolge qati, sonra ustunden kontur ile yazi (acar soz sari)."""
    font = load_font("ExtraBold", size)
    step = round(size * 1.08)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for x, y, word in _words(lines, font, step):
        sd.text((x + 6, y + 10), word, font=font, fill=(0, 0, 0, 210))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)), (0, 0))
    draw = ImageDraw.Draw(img)
    for x, y, word in _words(lines, font, step):
        draw.text((x, y), word, font=font, fill=_word_colour(word, highlight),
                  stroke_width=max(6, size // 14), stroke_fill=INK)


def _brand_pill(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    font = load_font("ExtraBold", 28)
    text = BRAND.upper()
    w = round(font.getlength(text))
    draw.rounded_rectangle((56, 44, 56 + w + 44, 44 + 54), radius=27, fill=ACCENT)
    draw.text((78, 54), text, font=font, fill=INK)


def _owl_glow(img: Image.Image) -> None:
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((THUMB_W - 560, THUMB_H - 560, THUMB_W + 40, THUMB_H + 120),
                                 fill=ACCENT + (90,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)), (0, 0))


def thumbnail(bg_path: str | None, sprite_path: str, text: str, out: str, highlight: str = "") -> str:
    """Reyestr #47: movzu fonu + sol tund kecid, 2-3 setir boyuk yazi (acar soz sari, qalin kontur, kolge),
    brend nisani, movzu esyali bayqus (owl/intro.png) isiq halesi ile."""
    img = _thumb_base(bg_path)
    size, lines = fit_title(text, THUMB_TEXT_W)
    _draw_title(img, lines, size, highlight)
    _brand_pill(img)
    _owl_glow(img)
    paste_sprite(img, sprite_path, 640, 20, 0)
    img.convert("RGB").save(out)
    return out
