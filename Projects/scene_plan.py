"""Add'im 23 - script.md -> scenes.json (fon promptu + sprite + muddet + narration).
Narration LLM-e yazdirilmir: skript deterministik olaraq sehnelere bolunur,
LLM yalniz her sehne ucun fon promptu ve sprite adini secir. Beleliklede metn 1:1 qorunur.
Istifade:
  python Projects\\scene_plan.py Episodes\\<slug> [--provider openai] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import LLMError, add_provider_arg, chat_json  # noqa: E402

SPRITES_JSON = r"C:\YouTubeAI\Character\ELI5_Owl\sprites\sprites.json"
WPM = 199.0   # olculmus; hər halda add. 25-de gercek audio uzunlugu ile evez olunur
MIN_WORDS, MAX_WORDS = 30, 75      # sehne uzunlugu (teqriben 12-30 s)
MIN_DUR, MAX_DUR = 6.0, 45.0   # klemp yalniz emniyyet ucun; gercek muddet add. 25-de TTS-den gelir
POSITIONS = ("left", "right", "center")

SYSTEM = """You are a scene planner for an animated explainer video.
The host is a cartoon owl rendered as a fixed sprite overlay - you never describe the owl.
You only choose: (1) a background illustration prompt, (2) which owl pose fits the narration.

Background prompt rules:
- Describe CONTENT ONLY - never style. The render pipeline appends the art style itself,
  so never write "vector", "illustration", "flat", "3D", "render", "style", "colors", "palette".
- The background must contain NO characters, NO people, NO animals, NO owl, NO mascot.
- The background must contain NO written words, letters or numbers - the image model cannot
  render text. Use icons, shapes, arrows, charts without labels instead.
- Describe one clear concrete scene or object set that mirrors the narration's example.
- A comma separated list of objects and setting, 12-25 words, English.
- Start with the setting, then the objects in it."""

USER = """For each numbered scene below, return a background prompt and an owl pose.

Available owl poses (use the name exactly):
{poses}

Pose guidance: front/three_q/side for plain explanation, happy for good news and payoffs,
thinking for questions and problems, confident for conclusions and advice,
chart for numbers, growth and comparisons, box for concrete objects, products and examples.
Vary the poses - do not repeat the same pose more than twice in a row.

Return JSON exactly in this shape, one entry per scene, same order, no extra keys:
{{"scenes": [{{"n": 1, "bg_prompt": "...", "sprite": "three_q"}}]}}

Scenes:
{scenes}"""


def load_poses() -> list[str]:
    if not os.path.isfile(SPRITES_JSON):
        raise SystemExit("sprites.json tapilmadi - evvelce make_sprites.py isledin: " + SPRITES_JSON)
    with open(SPRITES_JSON, encoding="utf-8") as f:
        return sorted(json.load(f))


def split_scenes(markdown: str) -> list[dict]:
    """Basliqlari atir, paraqraflari MIN_WORDS..MAX_WORDS araliginda sehnelere yigir."""
    scenes: list[dict] = []
    section = ""
    buf: list[str] = []

    def flush() -> None:
        if buf:
            text = " ".join(buf).strip()
            if text:
                scenes.append({"section": section, "narration": text})
            buf.clear()

    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            flush()
            section = line.lstrip("#").strip()
            continue
        if not line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if not sentence:
                continue
            buf.append(sentence)
            if len(" ".join(buf).split()) >= MAX_WORDS:
                flush()
        flush()
    flush()

    # cox qisa sehneleri qonsusuna birlesdir (eyni bolme daxilinde)
    merged: list[dict] = []
    for sc in scenes:
        if merged and merged[-1]["section"] == sc["section"] \
                and len(merged[-1]["narration"].split()) < MIN_WORDS:
            merged[-1]["narration"] += " " + sc["narration"]
        else:
            merged.append(sc)
    return merged


def assign_positions(scenes: list[dict]) -> list[str]:
    """Sprite movqeyi deterministik: bolmeler novbe ile sag/sol. LLM-e buraxilanda butun
    sehneler eyni terefde qalirdi. 'center' istifade olunmur - subtitr asagi-merkezdedir
    ve merkezdeki bayqusun ustune dusurdu (FAZA F kadr yoxlamasi)."""
    order: list[str] = []
    for s in scenes:
        if s["section"] not in order:
            order.append(s["section"])
    side = {sec: ("right", "left")[k % 2] for k, sec in enumerate(order)}
    return [side[s["section"]] for s in scenes]


def raw_duration(narration: str) -> float:
    """Klempsiz tehmin: soz sayi / WPM + qisa nefes."""
    return round(len(narration.split()) / WPM * 60.0 + 0.6, 1)


def duration_for(narration: str) -> float:
    return round(min(MAX_DUR, max(MIN_DUR, raw_duration(narration))), 1)


def plan(scenes: list[dict], poses: list[str], **llm_kw) -> list[dict]:
    listing = "\n".join(f"{i + 1}. [{s['section']}] {s['narration']}" for i, s in enumerate(scenes))
    data = chat_json(SYSTEM, USER.format(poses=", ".join(poses), scenes=listing),
                     max_tokens=6000, **llm_kw)
    items = data.get("scenes") or []
    if len(items) != len(scenes):
        raise LLMError(f"sehne sayi uygun gelmir: LLM {len(items)}, gozlenilen {len(scenes)}")
    out = []
    positions = assign_positions(scenes)
    for sc, it, pos in zip(scenes, items, positions):
        sprite = str(it.get("sprite", "")).strip()
        bg = " ".join(str(it.get("bg_prompt", "")).split())
        if sprite not in poses:
            print(f"  DIQQET: bilinmeyen sprite {sprite!r} -> three_q")
            sprite = "three_q"
        if not bg:
            raise LLMError("bos bg_prompt qaytarildi")
        out.append({**sc, "bg_prompt": bg, "sprite": sprite, "pos": pos,
                    "sprite_token": f"{sprite}@{pos}", "duration": duration_for(sc["narration"])})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir", help=r"mes. Episodes\trademark-copyright-patent")
    ap.add_argument("--force", action="store_true")
    add_provider_arg(ap)
    a = ap.parse_args()

    script_path = os.path.join(a.episode_dir, "script.md")
    out_path = os.path.join(a.episode_dir, "scenes.json")
    if not os.path.isfile(script_path):
        raise SystemExit("script.md tapilmadi: " + script_path)
    if os.path.isfile(out_path) and not a.force:
        raise SystemExit(f"artiq movcuddur: {out_path}  (--force ile uzerine yaz)")

    poses = load_poses()
    scenes = split_scenes(open(script_path, encoding="utf-8").read())
    if not scenes:
        raise SystemExit("script.md-den sehne cixmadi")
    print(f"[23] {len(scenes)} sehne bolundu -> fon promptu + sprite secilir")

    try:
        planned = plan(scenes, poses, provider=a.provider, model=a.model, temperature=a.temperature)
    except LLMError as e:
        raise SystemExit("LLM xetasi: " + str(e)) from e

    clamped = [i + 1 for i, s in enumerate(planned)
               if abs(s["duration"] - raw_duration(s["narration"])) > 0.05]
    if clamped:
        print("  DIQQET: muddeti klemplenmis sehneler:", clamped)
    total = sum(s["duration"] for s in planned)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"scenes": planned, "total_seconds": round(total, 1)}, f, indent=2, ensure_ascii=False)

    print(f"  {len(planned)} sehne  ~{total / 60:.1f} deq  -> {out_path}")
    print("  sprite istifadesi:", ", ".join(
        f"{p}x{sum(1 for s in planned if s['sprite'] == p)}" for p in poses))


if __name__ == "__main__":
    main()
