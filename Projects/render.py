"""Remotion render: public qovlugu (foto JPEG, bayqus PNG, sriftler) + props.json -> video_raw.mp4 (sessiz)."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess

from PIL import Image

import generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "Remotion")
FONTS = os.path.join(REMOTION, "public-static", "fonts")


def props(data: dict, caps: list[dict], fps: int = 30) -> dict:
    """Frame starts come from cumulative seconds (no per-scene rounding drift); total never cuts the narration."""
    durations = [s["duration"] for s in data["scenes"]]
    bounds, cum = [0], 0.0
    for d in durations:
        cum += d
        bounds.append(round(cum * fps))
    for i in range(1, len(bounds)):
        bounds[i] = max(bounds[i], bounds[i - 1] + 1)
    bounds[-1] = max(bounds[-1], math.ceil(round(cum * fps, 6)))
    scenes = []
    for i, s in enumerate(data["scenes"]):
        scenes.append({"n": s["n"], "type": s["type"], "img": f"img/sc{s['n']:02d}.jpg" if s["type"] == "photo" else None,
                       "owl": f"owl/sc{s['n']:02d}.png", "anim": s["anim"], "section": s["section"],
                       "sectionStart": bool(s["section_start"]), "from": bounds[i], "frames": bounds[i + 1] - bounds[i]})
    return {"fps": fps, "total": bounds[-1], "scenes": scenes,
            "captions": [{"from": round(c["start"] * fps), "to": round(c["end"] * fps), "text": c["text"]} for c in caps]}


def require_photos(ep: str, data: dict) -> None:
    """Foto sehnesi fotosuz render olunmur - images merhelesi yeniden cekmelidir."""
    missing = [os.path.join(ep, "img", f"sc{s['n']:02d}.png") for s in data["scenes"]
               if s["type"] == "photo" and not os.path.isfile(os.path.join(ep, "img", f"sc{s['n']:02d}.png"))]
    if missing:
        raise FileNotFoundError(f"foto yoxdur: {', '.join(missing)} - python run.py --resume ile yeniden cekilir")


def public_dir(ep: str, data: dict) -> str:
    pub = os.path.join(ep, "public")
    for sub in ("img", "owl"):
        os.makedirs(os.path.join(pub, sub), exist_ok=True)
    shutil.copytree(FONTS, os.path.join(pub, "fonts"), dirs_exist_ok=True)
    for s in data["scenes"]:
        n = f"sc{s['n']:02d}"
        if s["type"] == "photo":
            with Image.open(os.path.join(ep, "img", f"{n}.png")) as im:
                w, h = im.size
                im.convert("RGB").resize((1920, round(1920 * h / w)), Image.LANCZOS).save(
                    os.path.join(pub, "img", f"{n}.jpg"), quality=92)
        shutil.copyfile(os.path.join(ep, "owl", f"{n}.png"), os.path.join(pub, "owl", f"{n}.png"))
    return pub


def main(ep: str, runner=subprocess.run) -> None:
    ep = os.path.abspath(ep)
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(ep, "captions.json"), encoding="utf-8") as f:
        caps = json.load(f)
    require_photos(ep, data)
    pub = public_dir(ep, data)
    pp = os.path.join(ep, "props.json")
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(props(data, caps), f, ensure_ascii=False)
    npx = "npx.cmd" if os.name == "nt" else "npx"
    out = os.path.join(ep, "video_raw.mp4")
    runner([npx, "remotion", "render", "src/index.ts", "Episode", generate.tmp_path(out),
            f"--props={pp}", f"--public-dir={pub}", "--muted", "--codec=h264", "--crf=18", "--log=info"],
           cwd=REMOTION, check=True)
    os.replace(generate.tmp_path(out), out)
