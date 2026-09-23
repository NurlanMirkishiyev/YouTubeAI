"""Add'im 27 - scenes.json -> final MP4 (montage.py cagirisini qurur).
Istifade:
  python Projects\\build_episode.py Episodes\\<slug> [--srt] [--music Music\\bg.mp3] [--dry]
Teleb: her sehne ucun bg\\scNN.png, narration.wav (add. 24 ve 25 bitmis olmalidir).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

MONTAGE = r"C:\YouTubeAI\Projects\_ffmpeg\montage.py"
sys.path.insert(0, os.path.dirname(MONTAGE))
from montage import XFADE  # noqa: E402

# montage.py her kecidde XFADE qeder ortusme yaradir: total = sum(d) - XFADE*(n-1).
# Ona gore son sehneden basqa her sehnenin muddetine XFADE elave edilir - beleliklede
# video uzunlugu narration audiosu ile eyni olur ve sehneler audio ile duz oturur.


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--out", help="default: Episodes\\<slug>\\<slug>.mp4")
    ap.add_argument("--srt", action="store_true", help="narration.srt varsa yandirir")
    ap.add_argument("--music")
    ap.add_argument("--dry", action="store_true", help="yalniz emri cap et")
    a = ap.parse_args()

    scenes_path = os.path.join(a.episode_dir, "scenes.json")
    if not os.path.isfile(scenes_path):
        raise SystemExit("scenes.json tapilmadi: " + scenes_path)
    with open(scenes_path, encoding="utf-8") as f:
        scenes = json.load(f)["scenes"]

    images, durations, sprites, missing = [], [], [], []
    for i, s in enumerate(scenes, 1):
        img = s.get("bg") or os.path.join(a.episode_dir, "bg", f"sc{i:02d}.png")
        if not os.path.isfile(img):
            missing.append(i)
            continue
        images.append(img)
        durations.append(float(s["duration"]))
        sprites.append(s.get("sprite_token", "-"))
    if missing:
        raise SystemExit(f"catismayan fon: {missing} - once render_bgs.py isledin")

    durations = [f"{d + XFADE:.3f}" for d in durations[:-1]] + [f"{durations[-1]:.3f}"]

    narration = os.path.join(a.episode_dir, "narration.wav")
    if not os.path.isfile(narration):
        raise SystemExit("narration.wav tapilmadi - once tts_gen.py isledin")

    slug = os.path.basename(os.path.normpath(a.episode_dir))
    out = a.out or os.path.join(a.episode_dir, f"{slug}.mp4")

    cmd = [sys.executable, MONTAGE,
           "--images", *images, "--durations", *durations,
           "--sprites", *sprites, "--audio", narration, "--out", out]
    srt = os.path.join(a.episode_dir, "narration.srt")
    if a.srt:
        if not os.path.isfile(srt):
            raise SystemExit("narration.srt tapilmadi - once make_srt.py isledin")
        cmd += ["--srt", srt]
    if a.music:
        if not os.path.isfile(a.music):
            raise SystemExit("musiqi tapilmadi: " + a.music)
        cmd += ["--music", a.music]

    total = sum(float(d) for d in durations)
    print(f"[27] {len(images)} sehne, {total / 60:.2f} deq -> {out}")
    if a.dry:
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
