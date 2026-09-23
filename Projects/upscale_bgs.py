"""FAZA F 3.2 - bg\\scNN.png (SDXL 1344x768) -> 4x-UltraSharp -> bg_hd\\scNN.png (5120x2880).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\upscale_bgs.py Episodes\\<slug> [--only 3 7] [--force]
ComfyUI serveri isleyir olmalidir.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imaging import fit_cover  # noqa: E402
from render_bgs import require_server  # noqa: E402
from upscale import upscale_file  # noqa: E402

MODEL = "4x-UltraSharp.pth"
HD_W, HD_H = 5120, 2880


def upscale_one(src: str, dest: str, model: str, prefix: str) -> None:
    out = upscale_file(src, model, prefix)
    with Image.open(out) as im:
        fit_cover(im.convert("RGB"), HD_W, HD_H).save(dest, compress_level=3)
    os.remove(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--only", nargs="*", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()

    srcs = sorted(glob.glob(os.path.join(a.episode_dir, "bg", "sc[0-9][0-9].png")))
    if not srcs:
        raise SystemExit("bg\\scNN.png tapilmadi - once render_bgs.py isledin")
    require_server()
    hd_dir = os.path.join(a.episode_dir, "bg_hd")
    os.makedirs(hd_dir, exist_ok=True)
    slug = os.path.basename(os.path.normpath(a.episode_dir))

    todo = [s for s in srcs
            if (not a.only or int(os.path.basename(s)[2:4]) in a.only)
            and (a.force or not os.path.isfile(os.path.join(hd_dir, os.path.basename(s))))]
    print(f"[F] {len(todo)}/{len(srcs)} fon boyudulecek -> {hd_dir}", flush=True)
    failed, t0 = [], time.time()
    for k, src in enumerate(todo, 1):
        name = os.path.basename(src)
        try:
            upscale_one(src, os.path.join(hd_dir, name), a.model, f"hd_{slug}_{name[:-4]}")
        except (SystemExit, RuntimeError, OSError) as e:
            print(f"  {name} UGURSUZ: {e}", flush=True)
            failed.append(name)
            continue
        el = time.time() - t0
        print(f"  [{k}/{len(todo)}] {name}  {el / k:.0f}s/eded  qalan ~{(len(todo) - k) * el / k / 60:.1f} deq",
              flush=True)
    if failed:
        raise SystemExit(f"ugursuz fonlar: {failed}")


if __name__ == "__main__":
    main()
