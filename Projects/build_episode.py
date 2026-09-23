"""Add'im 27 / FAZA F - scenes.json -> final MP4 (montage.py cagirisini qurur).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\build_episode.py Episodes\\<slug> [--srt] [--cards]
                                     [--require-hd] [--music Music\\bg.mp3] [--dry]
--cards: 4 s intro + 6 s outro + bolme basliqlari; narration ve SRT INTRO_S qeder surusur.
--require-hd: her sehne ucun bg_hd\\scNN.png (>= 3840x2160) mecburidir (A6).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MONTAGE = os.path.join(HERE, "_ffmpeg", "montage.py")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(MONTAGE))
import cards  # noqa: E402
from montage import SPRITE_DIR, XFADE  # noqa: E402
from motion import transitions_for  # noqa: E402
from timeline import (INTRO_S, OUTRO_S, display_title, first_of_section,  # noqa: E402
                      montage_total, plan_timeline, shift_srt)

MIN_HD = (3840, 2160)
FONTS_DIR = r"C:\YouTubeAI\Assets\fonts"


def scene_image(ep_dir: str, n: int, scene: dict, require_hd: bool) -> str:
    hd = os.path.join(ep_dir, "bg_hd", f"sc{n:02d}.png")
    if os.path.isfile(hd):
        with Image.open(hd) as im:
            if im.width < MIN_HD[0] or im.height < MIN_HD[1]:
                raise SystemExit(f"{hd} {im.width}x{im.height} < {MIN_HD[0]}x{MIN_HD[1]} (A6)")
        return hd
    if require_hd:
        raise SystemExit(f"{hd} yoxdur - once upscale_bgs.py isledin")
    img = scene.get("bg") or os.path.join(ep_dir, "bg", f"sc{n:02d}.png")
    if not os.path.isfile(img):
        raise SystemExit(f"fon yoxdur: {img} - once render_bgs.py isledin")
    return img


def lower_third_titles(scenes: list[dict]) -> list[str | None]:
    return [display_title(s["section"]) if first and not s["section"].lower().startswith("hook") else None
            for s, first in zip(scenes, first_of_section(scenes))]


def make_cards(ep_dir: str, topic: str, scenes: list[dict], images: list[str]) -> dict:
    cdir = os.path.join(ep_dir, "cards")
    os.makedirs(cdir, exist_ok=True)
    lts = [cards.lower_third(t, os.path.join(cdir, f"lt_{i:02d}.png")) if t else "-"
           for i, t in enumerate(lower_third_titles(scenes), 1)]
    return {"intro": cards.intro_card(topic, images[0], os.path.join(SPRITE_DIR, "front.png"),
                                      os.path.join(cdir, "intro.png")),
            "outro": cards.outro_card(images[-1], os.path.join(SPRITE_DIR, "happy.png"),
                                      os.path.join(cdir, "outro.png")),
            "lower_thirds": lts}


def assemble(scenes: list[dict], images: list[str], card_paths: dict | None, xfade: float) -> dict:
    durs = [float(s["duration"]) for s in scenes]
    sprites = [s.get("sprite_token", "-") for s in scenes]
    sections = [s["section"] for s in scenes]
    if card_paths is None:
        return {"images": list(images), "sprites": sprites, "lower_thirds": ["-"] * len(scenes),
                "durations": [f"{d:.3f}" for d in plan_timeline(durs, xfade)],
                "transitions": transitions_for(sections), "delay": 0.0}
    return {"images": [card_paths["intro"], *images, card_paths["outro"]],
            "sprites": ["-", *sprites, "-"],
            "lower_thirds": ["-", *card_paths["lower_thirds"], "-"],
            "durations": [f"{d:.3f}" for d in plan_timeline(durs, xfade, INTRO_S, OUTRO_S)],
            "transitions": transitions_for(["__intro__", *sections, "__outro__"]),
            "delay": INTRO_S}


def srt_arg(ep_dir: str, delay: float) -> str:
    srt = os.path.join(ep_dir, "narration.srt")
    if not os.path.isfile(srt):
        raise SystemExit("narration.srt tapilmadi - once make_srt.py isledin")
    if delay <= 0:
        return srt
    shifted = os.path.join(ep_dir, "narration.shifted.srt")
    with open(srt, encoding="utf-8") as f, open(shifted, "w", encoding="utf-8", newline="\n") as g:
        g.write(shift_srt(f.read(), delay))
    return shifted


def montage_cmd(plan: dict, narration: str, out: str) -> list[str]:
    cmd = [sys.executable, MONTAGE, "--images", *plan["images"], "--durations", *plan["durations"],
           "--sprites", *plan["sprites"], "--lower-thirds", *plan["lower_thirds"],
           "--audio-delay", f"{plan['delay']:.3f}", "--audio", narration, "--out", out]
    return cmd + (["--transitions", *plan["transitions"]] if plan["transitions"] else [])


def read_topic(ep_dir: str, fallback: str) -> str:
    meta_path = os.path.join(ep_dir, "meta.json")
    if not os.path.isfile(meta_path):
        return fallback
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f).get("topic", fallback)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--out", help="default: Episodes\\<slug>\\<slug>.mp4")
    ap.add_argument("--srt", action="store_true", help="narration.srt yandirilir")
    ap.add_argument("--cards", action="store_true", help="intro/outro + bolme basliqlari")
    ap.add_argument("--require-hd", action="store_true")
    ap.add_argument("--music")
    ap.add_argument("--dry", action="store_true", help="yalniz emri cap et")
    a = ap.parse_args()

    ep = a.episode_dir
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        scenes = json.load(f)["scenes"]
    slug = os.path.basename(os.path.normpath(ep))
    narration = os.path.join(ep, "narration.wav")
    if not os.path.isfile(narration):
        raise SystemExit("narration.wav tapilmadi - once tts_gen.py isledin")

    images = [scene_image(ep, i, s, a.require_hd) for i, s in enumerate(scenes, 1)]
    card_paths = make_cards(ep, read_topic(ep, slug), scenes, images) if a.cards else None
    plan = assemble(scenes, images, card_paths, XFADE)
    out = a.out or os.path.join(ep, f"{slug}.mp4")
    cmd = montage_cmd(plan, narration, out)
    if a.srt:
        cmd += ["--srt", srt_arg(ep, plan["delay"]), "--fontsdir", FONTS_DIR]
    if a.music:
        if not os.path.isfile(a.music):
            raise SystemExit("musiqi tapilmadi: " + a.music)
        cmd += ["--music", a.music]

    total = montage_total([float(d) for d in plan["durations"]], XFADE)
    print(f"[27] {len(scenes)} sehne (+kartlar: {bool(a.cards)}), {total / 60:.2f} deq -> {out}", flush=True)
    if a.dry:
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
