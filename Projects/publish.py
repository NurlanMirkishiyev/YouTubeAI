"""Thumbnail (thumbs.py: secilmis stil, gpt-image-2 fon + ayrica bayqus pozasi) ve youtube.txt - ssenari metninden.
Thumbnail alinmasa retry / promptu yeniden yazma; tukense merhele dayanir (ilk foto ve sprite ile evez olunmur).
Butun fayllar kopyalanandan sonra en sonda Episodes/<slug>/published isaresi yazilir."""
from __future__ import annotations

import json
import os
import re
import shutil

from PIL import Image

import generate
import llm
import ratelimit
import thumbs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, "Hazir_Videolar")


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
    content = [s for s in data["scenes"] if s.get("type") not in ("intro", "outro")]
    desc = content[0]["text"] if content else ""
    chap = chapters(data["scenes"], data["title"])
    return "\n".join([data["title"], "", desc, "", *chap, "", f"Tags: {tags}"]) + "\n"


def thumbnail(ep: str, data: dict, gen, rewrite=llm.rewrite_safe, edit=None, chat=llm.chat_json) -> Image.Image:
    """Secilmis stilde (config/thumbnail.json) thumbnail - dizayn thumbs.py-dadir."""
    return thumbs.make(ep, data, gen, edit or thumbs._default_edit, rewrite, chat=chat)


def _default_gen(prompt: str) -> bytes:
    ratelimit.IMAGE_LIMITER.acquire()
    return llm.generate_image(prompt, quality="high")


def main(ep: str, gen=None, out_root: str = OUT_ROOT, rewrite=llm.rewrite_safe, edit=None) -> None:
    gen = gen or _default_gen
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    thumb = os.path.join(ep, "thumbnail.png")
    if not os.path.isfile(thumb):                # tekrar cehdde yeniden pul odenmir
        thumbnail(ep, data, gen, rewrite, edit).save(generate.tmp_path(thumb))
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
