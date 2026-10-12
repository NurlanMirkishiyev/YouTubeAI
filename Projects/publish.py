"""Thumbnail (gpt-image-2 foto + sahnenin bayqusu + basliq) ve youtube.txt - yalniz ssenari metninden.
Thumbnail alinmasa retry / promptu yeniden yazma; tukense merhele dayanir (ilk foto ve sprite ile evez olunmur).
Butun fayllar kopyalanandan sonra en sonda Episodes/<slug>/published isaresi yazilir."""
from __future__ import annotations

import io
import json
import os
import re
import shutil

from PIL import Image, ImageDraw, ImageFont

import generate
import llm
import ratelimit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "Remotion", "public-static", "fonts", "Montserrat-ExtraBold.ttf")
OUT_ROOT = os.path.join(ROOT, "Hazir_Videolar")
MAX_TITLE_SIZE, MIN_TITLE_SIZE = 74, 44
MAX_TITLE_LINES = 4
TITLE_WIDTH, TITLE_TOP, TITLE_BOTTOM, TITLE_LEADING = 760, 60, 690, 14


def _mmss(s: float) -> str:
    s = int(s)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def _starts_chapter(s: dict) -> bool:
    return bool(s["section_start"] and s["section"])


def chapters(scenes: list[dict], title: str) -> list[str]:
    """YouTube chapters start at 0:00; an unnamed first scene opens the chapter with the script title."""
    out, t = [], 0.0
    if scenes and not _starts_chapter(scenes[0]):
        out.append(f"0:00 {title}")
    for s in scenes:
        if _starts_chapter(s):
            out.append(f"{_mmss(t)} {s['section']}")
        t += s["duration"]
    return out


def youtube_text(data: dict) -> str:
    tags = ", ".join(w.lower() for w in re.findall(r"[A-Za-z]+", data["title"]) if len(w) > 2)
    desc = data["scenes"][0]["text"] if data["scenes"] else ""
    chap = chapters(data["scenes"], data["title"])
    return "\n".join([data["title"], "", desc, "", *chap, "", f"Tags: {tags}"]) + "\n"


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def _background(first: dict, gen, rewrite) -> Image.Image:
    def draw(p: str) -> Image.Image:
        img = Image.open(io.BytesIO(gen(p + " Realistic photo, no text.")))
        img.load()
        return img.convert("RGB")
    return generate.with_retry(draw, first["photo_prompt"], rewrite=rewrite, label="thumbnail")


def _owl_path(ep: str) -> str:
    own = os.path.join(ep, "owl", "sc01.png")
    if not os.path.isfile(own):
        raise generate.GenerationFailed(f"thumbnail: sehne bayqusu yoxdur ({own})")
    return own


def fit_title(draw, title: str) -> tuple[int, list[str]]:
    """Largest font (74 -> MIN_TITLE_SIZE) whose wrap fits MAX_TITLE_LINES and the bottom limit; else capped with an ellipsis."""
    lines: list[str] = []
    size = MAX_TITLE_SIZE
    for size in range(MAX_TITLE_SIZE, MIN_TITLE_SIZE - 1, -2):
        lines = _wrap(draw, title, ImageFont.truetype(FONT, size), TITLE_WIDTH)
        if len(lines) <= MAX_TITLE_LINES and TITLE_TOP + len(lines) * (size + TITLE_LEADING) <= TITLE_BOTTOM:
            return size, lines
    font = ImageFont.truetype(FONT, size)
    lines = lines[:MAX_TITLE_LINES]
    last = lines[-1]
    while last and draw.textlength(last + "…", font=font) > TITLE_WIDTH:
        last = last[:-1].rstrip()
    lines[-1] = last + "…"
    return size, lines


def thumbnail(ep: str, data: dict, gen, rewrite=llm.rewrite_safe) -> Image.Image:
    first = next((s for s in data["scenes"] if s["type"] == "photo"), data["scenes"][0])
    owl = Image.open(_owl_path(ep)).convert("RGBA")
    bg = _background(first, gen, rewrite).resize((1280, 720))
    owl = owl.resize((int(owl.width * 600 / owl.height), 600))
    bg.paste(owl, (1280 - owl.width - 20, 720 - owl.height), owl)
    d = ImageDraw.Draw(bg)
    size, lines = fit_title(d, data["title"].upper())
    font = ImageFont.truetype(FONT, size)
    y = TITLE_TOP
    for line in lines:
        d.text((50, y), line, font=font, fill="white", stroke_width=6, stroke_fill="black")
        y += size + TITLE_LEADING
    return bg


def _default_gen(prompt: str) -> bytes:
    ratelimit.IMAGE_LIMITER.acquire()
    return llm.generate_image(prompt)


def main(ep: str, gen=None, out_root: str = OUT_ROOT, rewrite=llm.rewrite_safe) -> None:
    gen = gen or _default_gen
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    thumb = os.path.join(ep, "thumbnail.png")
    if not os.path.isfile(thumb):                # tekrar cehdde yeniden pul odenmir
        thumbnail(ep, data, gen, rewrite).save(generate.tmp_path(thumb))
        os.replace(generate.tmp_path(thumb), thumb)
    with open(os.path.join(ep, "youtube.txt"), "w", encoding="utf-8") as f:
        f.write(youtube_text(data))
    out = os.path.join(out_root, data["slug"])
    os.makedirs(out, exist_ok=True)
    for f in (f"{data['slug']}.mp4", "thumbnail.png", f"{data['slug']}.srt", "youtube.txt"):
        shutil.copyfile(os.path.join(ep, f), os.path.join(out, f))
    with open(os.path.join(ep, "published"), "w", encoding="utf-8") as f:
        f.write(out + "\n")
    print(f"  HAZIR: {out}", flush=True)
