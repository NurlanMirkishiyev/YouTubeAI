"""FAZA F 5 - YouTube paketi: youtube\\title.txt, title_variants.txt, description.txt (chapters),
tags.txt, thumbnail.png (1280x720).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\publish_pack.py Episodes\\<slug> [--provider openai]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from PIL import Image, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cards  # noqa: E402
from llm import LLMError, add_provider_arg, chat_json  # noqa: E402
from timeline import INTRO_S, OUTRO_S, display_title, section_starts  # noqa: E402

TITLE_MAX = 70
TAGS_MAX = 500
MIN_CHAPTER_S = 10.0   # YouTube: her chapter >= 10 s, en az 3 chapter, ilki 00:00
FIRST_CHAPTER = "Intro"  # "Hook" daxili terminidir, tamasaciya gosterilmir
THUMB_SIZE = (1280, 720)
SPRITE_HD = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"

SYSTEM = """You write YouTube metadata for an ELI5 Business explainer channel hosted by a cartoon owl.
Honest, specific, curiosity-driven. Never promise anything the video does not deliver.
No emojis. No ALL CAPS words. No invented statistics."""

PACK_USER = """Topic: {topic}

Chapter titles in order:
{chapters}

How the video opens (narration):
{hook}

Return JSON only:
{{"titles": ["three different title options, each at most 60 characters"],
  "summary": "two or three sentences: what the viewer will understand after watching",
  "tags": ["12 to 15 search tags, lowercase, 1-4 words each"],
  "hashtags": ["three hashtags without spaces"],
  "thumb_text": "3 to 5 punchy words for the thumbnail"}}"""


def fmt_ts(sec: float) -> str:
    s = int(sec)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def chapters(scenes: list[dict], intro_s: float, total_s: float,
             min_len: float = MIN_CHAPTER_S) -> list[tuple[float, str]]:
    """Ilk chapter 00:00 (intro Hook-a daxildir); qisa chapter novbetiye yol verir."""
    kept: list[tuple[float, str]] = []
    for k, (sec, start) in enumerate(section_starts(scenes, intro_s)):
        item = (0.0, FIRST_CHAPTER) if k == 0 else (start, display_title(sec))
        if kept and item[0] - kept[-1][0] < min_len:
            if len(kept) > 1:
                kept[-1] = item
            continue
        kept.append(item)
    while len(kept) > 1 and total_s - kept[-1][0] < min_len:
        kept.pop()
    return kept if len(kept) >= 3 else []


def fit_tags(tags: list, limit: int = TAGS_MAX) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    used = 0
    for raw in tags:
        t = " ".join(str(raw).replace(",", " ").split())
        if not t or t.lower() in seen:
            continue
        cost = len(t) + (1 if out else 0)
        if used + cost > limit:
            break
        out.append(t)
        seen.add(t.lower())
        used += cost
    return out


def pick_title(titles: list) -> str:
    clean = [" ".join(str(t).split()) for t in titles if str(t).strip()]
    if not clean:
        raise ValueError("LLM basliq qaytarmadi")
    fitting = [t for t in clean if len(t) <= TITLE_MAX]
    return fitting[0] if fitting else clean[0][:TITLE_MAX].rsplit(" ", 1)[0]


def description(summary: str, chaps: list[tuple[float, str]], hashtags: list) -> str:
    lines = [summary.strip(), ""]
    if chaps:
        lines += ["Chapters:"] + [f"{fmt_ts(t)} {title}" for t, title in chaps] + [""]
    tags = " ".join(h if str(h).startswith("#") else "#" + str(h).replace(" ", "") for h in hashtags)
    if tags:
        lines.append(tags)
    return "\n".join(lines).strip() + "\n"


def pick_thumb_bg(paths: list[str]) -> str:
    """En kontrastli fon (parlaqliq standart kenarlasmasi en boyuk olan)."""
    def score(p: str) -> float:
        with Image.open(p) as im:
            g = im.convert("L")
            g.thumbnail((256, 256))
            return ImageStat.Stat(g).stddev[0]
    return max(paths, key=score)


def _read(ydir: str, name: str) -> str:
    with open(os.path.join(ydir, name), encoding="utf-8") as f:
        return f.read().strip()


def pack_problems(ydir: str) -> list[str]:
    names = ("title.txt", "description.txt", "tags.txt", "thumbnail.png")
    missing = [f"{n} yoxdur" for n in names if not os.path.isfile(os.path.join(ydir, n))]
    if missing:
        return missing
    problems = []
    title = _read(ydir, "title.txt")
    if not 0 < len(title) <= TITLE_MAX:
        problems.append(f"title uzunlugu {len(title)} (1..{TITLE_MAX})")
    if "00:00" not in _read(ydir, "description.txt"):
        problems.append("description-da 00:00 chapter yoxdur")
    tags = _read(ydir, "tags.txt")
    if len(tags) > TAGS_MAX:
        problems.append(f"tags {len(tags)} > {TAGS_MAX} simvol")
    with Image.open(os.path.join(ydir, "thumbnail.png")) as im:
        if im.size != THUMB_SIZE:
            problems.append(f"thumbnail {im.size} != {THUMB_SIZE}")
    return problems


def write_pack(ep: str, topic: str, data: dict, chaps: list[tuple[float, str]]) -> str:
    ydir = os.path.join(ep, "youtube")
    os.makedirs(ydir, exist_ok=True)
    titles = data.get("titles") or []
    files = {"title.txt": pick_title(titles) + "\n",
             "title_variants.txt": "\n".join(" ".join(str(t).split()) for t in titles) + "\n",
             "description.txt": description(str(data.get("summary", "")), chaps, data.get("hashtags") or []),
             "tags.txt": ",".join(fit_tags(data.get("tags") or [])) + "\n"}
    for name, text in files.items():
        with open(os.path.join(ydir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    bgs = sorted(glob.glob(os.path.join(ep, "bg_hd", "sc*.png"))) or \
        sorted(glob.glob(os.path.join(ep, "bg", "sc*.png")))
    cards.thumbnail(pick_thumb_bg(bgs), os.path.join(SPRITE_HD, "confident.png"),
                    str(data.get("thumb_text") or topic), os.path.join(ydir, "thumbnail.png"))
    return ydir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    add_provider_arg(ap)
    a = ap.parse_args()
    ep = a.episode_dir
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        sdata = json.load(f)
    scenes = sdata["scenes"]
    intro_s = float(sdata.get("intro_seconds", INTRO_S))
    outro_s = float(sdata.get("outro_seconds", OUTRO_S))
    with open(os.path.join(ep, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    total = intro_s + sum(float(s["duration"]) for s in scenes) + outro_s
    chaps = chapters(scenes, intro_s, total)
    try:
        data = chat_json(SYSTEM, PACK_USER.format(topic=meta["topic"],
                                                  chapters="\n".join(t for _, t in chaps),
                                                  hook=scenes[0]["narration"][:600]),
                         max_tokens=900, provider=a.provider, model=a.model, temperature=0.7)
        ydir = write_pack(ep, meta["topic"], data, chaps)
    except (LLMError, ValueError) as e:
        raise SystemExit("publish paketi xetasi: " + str(e)) from e
    problems = pack_problems(ydir)
    print(f"[F] youtube paketi -> {ydir}  chapters: {len(chaps)}")
    if problems:
        raise SystemExit("paket problemleri: " + "; ".join(problems))


if __name__ == "__main__":
    main()
