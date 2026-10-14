"""Thumbnail dizayni: fon (gpt-image-2) + thumbnail ucun ayrica ifadeli bayqus pozasi (gpt-image-2, gorunus eyni)
+ qisa, iri yazi. Yazi yalniz ssenariden: "Thumbnail idea" bolmesindeki sitat, yoxdursa basligin DEQIQ fraqmenti.
Stil istifadeci secimidir ve config/thumbnail.json-da daimi saxlanir (STYLES).
Fon / bayqus alinmasa retry, tukense GenerationFailed (sehne fotosu / sprite ile evez olunmur).

Istifade:  python Projects/thumbs.py samples <ssenari>  -> Thumbnail_Numuneler/<slug>/<stil>.png + secim.png
           python Projects/thumbs.py select <stil>    -> secim daimi yazilir"""
from __future__ import annotations

import io
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402
import llm  # noqa: E402
import owl as owl_mod  # noqa: E402
import plan  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "Remotion", "public-static", "fonts", "Montserrat-ExtraBold.ttf")
CONFIG = os.path.join(ROOT, "config", "thumbnail.json")
SAMPLES = os.path.join(ROOT, "Thumbnail_Numuneler")
W, H = 1280, 720
YELLOW, NAVY, BLACK, WHITE = (255, 212, 0), (11, 26, 66), (0, 0, 0), (255, 255, 255)

STYLES = ("bold", "split", "spotlight", "frame")
LABELS = {"bold": "1 - BOLD (iri yazi, parlaq foto, sol tərəf qaranliq)",
          "split": "2 - SPLIT (sol göy panel + diaqonal sari xett, sagda foto)",
          "spotlight": "3 - SPOTLIGHT (qaranliq dramatik isiq, sari etiket yazi)",
          "frame": "4 - FRAME (sari-narinci fon, eyilmis foto kartı)"}
BG_MOOD = {"bold": "Bright, vivid, saturated colours, high contrast, main subject large in the center, "
                   "simple uncluttered left third.",
           "split": "Clean, bright, main subject centered and large, simple background.",
           "spotlight": "Dark moody studio, one dramatic spotlight on the main subject, deep black shadows.",
           "frame": "Bright clean product-style photo, main subject centered, soft studio light."}
BG_RULES = " Realistic photograph, 16:9, sharp focus. No text, no letters, no logos, no owl, no mascot."
THUMB_POSE = ("extremely surprised and excited YouTube-thumbnail expression: eyes wide open, beak open in amazement, "
              "leaning forward, one wing pointing to the left, the other wing raised")
HOOK_SYSTEM = ("You write YouTube thumbnail text. From the video title pick the 2-4 most clickable CONSECUTIVE words, "
               "copied EXACTLY from the title (no new words). Answer ONLY JSON: {\"text\": \"...\"}")


# --- secim ---------------------------------------------------------------------------------------------------

def chosen_style(path: str = CONFIG) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            style = json.load(f).get("style")
    except (OSError, ValueError, AttributeError):
        return STYLES[0]
    return style if style in STYLES else STYLES[0]


def save_style(style: str, path: str = CONFIG) -> None:
    if style not in STYLES:
        raise ValueError(f"namelum stil: {style} (var: {', '.join(STYLES)})")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    generate.atomic_json(path, {"style": style})


# --- yazi ve fon promptu -------------------------------------------------------------------------------------

def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$%']+", text.lower().replace("’", "'"))


def _is_fragment(part: str, title: str) -> bool:
    p, t = _words(part), _words(title)
    return bool(p) and any(t[i:i + len(p)] == p for i in range(len(t) - len(p) + 1))


def hook_text(data: dict, chat=llm.chat_json) -> str:
    if data.get("thumbnail_text"):
        return data["thumbnail_text"].upper()
    title = data["title"]
    for _ in range(2):
        try:
            text = str(chat(HOOK_SYSTEM, title, max_tokens=60).get("text") or "").strip()
        except Exception as e:  # noqa: BLE001 - yazi basliqdan da olur; balans xetasi istisnadir
            if llm.is_balance_error(e):
                raise
            continue
        if 1 < len(text.split()) <= 4 and _is_fragment(text, title):
            return text.upper()
    return title.upper()


def bg_prompt(data: dict, style: str) -> str:
    first = next((s for s in data.get("scenes", []) if s.get("type") == "photo" and s.get("photo_prompt")), {})
    idea = data.get("thumbnail_idea") or first.get("photo_prompt") or data["title"]
    idea = " ".join(s for s in re.split(r"(?<=[.!?])\s+", idea)
                    if not re.search(r"\b(owl|mascot|words?|text|title)\b", s, re.I)) or idea
    return f"YouTube thumbnail background photo: {plan.photo_safe(idea)} {BG_MOOD[style]}{BG_RULES}"


# --- cizim yardimcilari --------------------------------------------------------------------------------------

def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def _cover(img: Image.Image, w: int, h: int, x_bias: float = 0.5) -> Image.Image:
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS, centering=(x_bias, 0.5))


def fit_lines(text: str, max_w: int, max_lines: int, big: int, small: int) -> tuple[int, list[str]]:
    """En iri srift (big -> small) ki, soz-soz bolunmus setrler max_w-e ve max_lines-a sigsin."""
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    for size in range(big, small - 1, -4):
        f, lines, cur = _font(size), [], ""
        for w in text.split():
            test = f"{cur} {w}".strip()
            if cur and d.textlength(test, font=f) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        lines.append(cur)
        if len(lines) <= max_lines and all(d.textlength(ln, font=f) <= max_w for ln in lines):
            return size, lines
    return small, lines[:max_lines]


def _text(img: Image.Image, lines: list[str], size: int, x: int, y: int, fills: list, stroke: int, stroke_fill,
          shadow: bool = True) -> int:
    d, f = ImageDraw.Draw(img), _font(size)
    for i, ln in enumerate(lines):
        if shadow:
            d.text((x + 7, y + 8), ln, font=f, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
        d.text((x, y), ln, font=f, fill=fills[i % len(fills)], stroke_width=stroke, stroke_fill=stroke_fill)
        y += int(size * 1.08)
    return y


def _fills(n: int, base, accent) -> list:
    return [base] * (n - 1) + [accent] if n > 1 else [accent]


def sticker(owl: Image.Image, height: int, outline: int = 9, color=WHITE, glow=None) -> Image.Image:
    """Bayqus kesik "stiker" kimi: ag kontur + kolge (istege gore rengli parilti)."""
    owl = owl.convert("RGBA")
    owl = owl.resize((int(owl.width * height / owl.height), height), Image.LANCZOS)
    pad = outline * 4
    canvas = Image.new("RGBA", (owl.width + 2 * pad, owl.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", canvas.size, 0)
    a.paste(owl.getchannel("A"), (pad, pad))
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    halo = a.filter(ImageFilter.GaussianBlur(outline * 2.2)).point(lambda v: min(255, v * 2))
    out.paste(Image.new("RGBA", canvas.size, glow or (0, 0, 0, 255)), (0, 0), halo if glow else
              a.filter(ImageFilter.GaussianBlur(outline)).point(lambda v: v // 2))
    ring = a.filter(ImageFilter.MaxFilter(outline * 2 + 1))
    out.paste(Image.new("RGBA", canvas.size, color + (255,)), (0, 0), ring)
    out.alpha_composite(owl, (pad, pad))
    return out


def _paste_owl(img: Image.Image, st: Image.Image, right: int = -10, bottom: int = 0, x: int | None = None) -> None:
    base = img.convert("RGBA")
    pos = (W - st.width - right if x is None else x, H - st.height + int(st.height * 0.04) - bottom)
    base.alpha_composite(st, (max(-st.width // 2, pos[0]), pos[1]))
    img.paste(base.convert("RGB"))


def _left_shade(img: Image.Image, width: float, strength: int) -> Image.Image:
    grad = Image.linear_gradient("L").rotate(90).resize((W, H))      # sol 255 -> sag 0
    mask = grad.point(lambda v: max(0, min(255, int((v - 255 * (1 - width)) / width * strength / 255))))
    return Image.composite(Image.new("RGB", (W, H), BLACK), img, mask)


def _vignette(img: Image.Image, cx: float, strength: int) -> Image.Image:
    m = Image.radial_gradient("L").resize((int(W * 1.5), int(H * 1.6)))
    m = m.crop((int(W * (0.75 - cx)), int(H * 0.3), int(W * (0.75 - cx)) + W, int(H * 0.3) + H))
    m = m.point(lambda v: min(255, int(v * strength / 160)))
    return Image.composite(Image.new("RGB", (W, H), BLACK), img, m)


def _pop(img: Image.Image, color: float = 1.3, contrast: float = 1.12) -> Image.Image:
    return ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(color)).enhance(contrast)


# --- stiller -------------------------------------------------------------------------------------------------

def _bold(bg, owl, text):
    img = _left_shade(_pop(_cover(bg, W, H, 0.6)), 0.62, 215)
    size, lines = fit_lines(text, 690, 3, 168, 80)
    total = int(size * 1.08) * len(lines)
    _text(img, lines, size, 46, (H - total) // 2 - 10, _fills(len(lines), WHITE, YELLOW), 9, BLACK)
    _paste_owl(img, sticker(owl, 600), right=-20)
    return img


def _split(bg, owl, text):
    img = _pop(_cover(bg, W, H, 0.5), 1.2, 1.08)
    panel = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(panel)
    d.polygon([(0, 0), (640, 0), (520, H), (0, H)], fill=255)
    img.paste(Image.new("RGB", (W, H), NAVY), (0, 0), panel)
    ImageDraw.Draw(img).polygon([(640, 0), (662, 0), (542, H), (520, H)], fill=YELLOW)
    size, lines = fit_lines(text, 470, 4, 132, 64)
    total = int(size * 1.08) * len(lines)
    _text(img, lines, size, 40, (H - total) // 2, _fills(len(lines), WHITE, YELLOW), 4, BLACK, shadow=False)
    _paste_owl(img, sticker(owl, 520, outline=8), right=-30)
    return img


def _spotlight(bg, owl, text):
    img = _vignette(_pop(_cover(bg, W, H, 0.55), 1.15, 1.2), 0.58, 235)
    size, lines = fit_lines(text, 640, 3, 104, 60)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, f, y = ImageDraw.Draw(layer), _font(size), 44
    for ln in lines:
        tw = int(d.textlength(ln, font=f))
        d.rounded_rectangle((36, y, 36 + tw + 44, y + int(size * 1.12)), radius=14, fill=YELLOW + (255,))
        d.text((58, y + int(size * 0.02)), ln, font=f, fill=BLACK)
        y += int(size * 1.24)
    layer = layer.rotate(3, resample=Image.BICUBIC, center=(0, 0))
    base = img.convert("RGBA")
    base.alpha_composite(layer)
    img = base.convert("RGB")
    _paste_owl(img, sticker(owl, 580, outline=7, color=YELLOW, glow=(255, 200, 0, 255)), right=-10)
    return img


def _frame(bg, owl, text):
    img = Image.composite(Image.new("RGB", (W, H), (255, 122, 0)), Image.new("RGB", (W, H), YELLOW),
                          Image.linear_gradient("L").resize((W, H)))
    rays = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(rays)
    for k in range(0, 360, 20):
        d.pieslice((-W, -H, 2 * W, 2 * H), k, k + 9, fill=40)
    img = Image.composite(Image.new("RGB", (W, H), WHITE), img, rays.filter(ImageFilter.GaussianBlur(6)))
    card = ImageOps.expand(_pop(_cover(bg, 640, 400)), border=14, fill=WHITE).convert("RGBA").rotate(
        -5, expand=True, resample=Image.BICUBIC)
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", card.size, (0, 0, 0, 150)), (0, 0), card.getchannel("A"))
    base = img.convert("RGBA")
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)), (528, 168))
    base.alpha_composite(card, (510, 150))
    img = base.convert("RGB")
    size, lines = fit_lines(text, 520, 4, 128, 60)
    total = int(size * 1.08) * len(lines)
    _text(img, lines, size, 40, (H - total) // 2, _fills(len(lines), BLACK, (200, 0, 0)), 7, WHITE, shadow=False)
    _paste_owl(img, sticker(owl, 470, outline=8), right=-30)
    return img


_DRAW = {"bold": _bold, "split": _split, "spotlight": _spotlight, "frame": _frame}


def compose(style: str, bg: Image.Image, owl: Image.Image, text: str) -> Image.Image:
    return _DRAW[style](bg, owl, text).convert("RGB")


# --- generasiya ----------------------------------------------------------------------------------------------

def background(data: dict, style: str, gen, rewrite) -> Image.Image:
    def draw(p: str) -> Image.Image:
        img = Image.open(io.BytesIO(gen(p)))
        img.load()
        return img.convert("RGB")
    return generate.with_retry(draw, bg_prompt(data, style), rewrite=rewrite, label=f"thumbnail fonu ({style})")


def thumb_owl(ep: str, edit, rewrite) -> Image.Image:
    path = os.path.join(ep, "owl", "thumb.png")
    if not os.path.isfile(path):                 # bir defe cekilir, sonra yeniden istifade
        os.makedirs(os.path.dirname(path), exist_ok=True)
        owl_mod._one(path, THUMB_POSE, edit, None, rewrite)
    return Image.open(path).convert("RGBA")


def make(ep: str, data: dict, gen, edit, rewrite=llm.rewrite_safe, style: str | None = None,
         chat=llm.chat_json) -> Image.Image:
    style = style or chosen_style()
    owl_img = thumb_owl(ep, edit, rewrite)
    return compose(style, background(data, style, gen, rewrite), owl_img, hook_text(data, chat))


def _default_gen(prompt: str) -> bytes:
    import ratelimit
    ratelimit.IMAGE_LIMITER.acquire()
    return llm.generate_image(prompt, quality="high")


def _default_edit(prompt: str, ref: str) -> bytes:
    import ratelimit
    ratelimit.IMAGE_LIMITER.acquire()
    return llm.edit_image(prompt, ref, quality="medium")


def samples(script_name: str, out_root: str = SAMPLES) -> str:
    """Ssenaridan (basliq, Thumbnail idea) butun stillerde numune - her stile oz fonu - ve muqayise vereqi secim.png.
    Fon ve bayqus fayllari saxlanir: tekrar cagiris pul xerclemir."""
    import script
    from pipeline import find_script
    data = script.build(find_script(script_name))
    out = os.path.join(out_root, data["slug"])
    os.makedirs(out, exist_ok=True)
    owl_img = thumb_owl(out, _default_edit, llm.rewrite_safe)
    text = hook_text(data)
    tiles = []
    for style in STYLES:
        bg_path = os.path.join(out, f"fon_{style}.png")
        if os.path.isfile(bg_path):
            bg = Image.open(bg_path).convert("RGB")
        else:
            bg = background(data, style, _default_gen, llm.rewrite_safe)
            bg.save(bg_path)
        img = compose(style, bg, owl_img, text)
        img.save(os.path.join(out, f"{style}.png"))
        tiles.append((style, img))
        print(f"  numune: {style}.png", flush=True)
    sheet = Image.new("RGB", (W * 2 + 30, (H + 70) * 2 + 10), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    for i, (style, img) in enumerate(tiles):
        x, y = (i % 2) * (W + 30), (i // 2) * (H + 70)
        d.text((x + 10, y + 12), LABELS[style], font=_font(38), fill=WHITE)
        sheet.paste(img, (x, y + 60))
    sheet.save(os.path.join(out, "secim.png"))
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "samples":
        print(f"HAZIR: {samples(sys.argv[2])}")
    elif len(sys.argv) == 3 and sys.argv[1] == "select":
        save_style(sys.argv[2])
        print(f"secildi: {sys.argv[2]} ({CONFIG})")
    else:
        print(__doc__)
        raise SystemExit(2)
