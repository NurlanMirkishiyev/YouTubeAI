"""Add'im 24 - scenes.json -> her sehne ucun fon PNG (ComfyUI, Workflow B).
Istifade:
  ComfyUI\\.venv\\Scripts\\python Projects\\render_bgs.py Episodes\\<slug> [--only 3 7] [--force]
Cixis: Episodes\\<slug>\\bg\\sc01.png ...   (scenes.json-a "bg" sahesi yazilir)
ComfyUI serveri isleyir olmalidir: run_comfyui.bat
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_workflow import submit, wait  # noqa: E402

WORKFLOW = r"C:\YouTubeAI\Projects\_workflows\bg_sdxl_api.json"
COMFY_OUT = r"C:\YouTubeAI\ComfyUI\output"
API = "http://127.0.0.1:8188"
BASE_SEED = 1000
# sprite hansi terefdedirse, fonun o terefi bos qalmalidir
SPACE = {"right": "empty space on the right side",
         "left":  "empty space on the left side",
         "center": "empty uncluttered space in the lower center"}


def require_server() -> None:
    try:
        urllib.request.urlopen(f"{API}/system_stats", timeout=5).read()
    except (urllib.error.URLError, TimeoutError) as e:
        raise SystemExit(f"ComfyUI cavab vermir ({API}) - run_comfyui.bat isledin.  {e}")


def seed_of(scene: dict, n: int) -> int:
    """check_bgs yeniden cekende sehneye yeni "seed" yazir - eyni prompt + eyni seed eyni sekli verirdi."""
    return int(scene.get("seed", BASE_SEED + n))


def save_bg_paths(scenes_path: str, bg_dir: str) -> None:
    """scenes.json diskden TEZEDEN oxunur, yalniz "bg" saheleri yazilir. Evvel render basinda oxunan
    kohne nusxe butovlukle yazilirdi ve render vaxti edilmis prompt duzelislerini silirdi."""
    with open(scenes_path, encoding="utf-8") as f:
        data = json.load(f)
    for i, s in enumerate(data["scenes"]):
        p = os.path.join(bg_dir, f"sc{i + 1:02d}.png")
        if os.path.isfile(p):
            s["bg"] = p
    with open(scenes_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build(prompt: str, seed: int, prefix: str, pos: str) -> dict:
    text = open(WORKFLOW, encoding="utf-8").read()
    text = (text.replace("__POS__", json.dumps(prompt)[1:-1])
                .replace("__SPACE__", SPACE.get(pos, SPACE["right"]))
                .replace("__SEED__", str(seed))
                .replace("__PREFIX__", prefix))
    return json.loads(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--only", nargs="*", type=int, help="yalniz bu sehne nomreleri (1-esasli)")
    ap.add_argument("--force", action="store_true", help="movcud PNG-leri yenidden cek")
    a = ap.parse_args()

    scenes_path = os.path.join(a.episode_dir, "scenes.json")
    if not os.path.isfile(scenes_path):
        raise SystemExit("scenes.json tapilmadi: " + scenes_path)
    require_server()

    with open(scenes_path, encoding="utf-8") as f:
        data = json.load(f)
    scenes = data["scenes"]
    bg_dir = os.path.join(a.episode_dir, "bg")
    os.makedirs(bg_dir, exist_ok=True)

    todo = [i for i in range(len(scenes))
            if (not a.only or i + 1 in a.only)
            and (a.force or not os.path.isfile(os.path.join(bg_dir, f"sc{i + 1:02d}.png")))]
    print(f"[24] {len(todo)}/{len(scenes)} sehne cekilecek -> {bg_dir}")

    t0 = time.time()
    for k, i in enumerate(todo, 1):
        n = i + 1
        dest = os.path.join(bg_dir, f"sc{n:02d}.png")
        prefix = f"ep_{n:02d}"
        try:
            files = wait(submit(build(scenes[i]["bg_prompt"], seed_of(scenes[i], n), prefix,
                                      scenes[i].get("pos", "right"))), timeout_s=900)
        except SystemExit as e:
            print(f"  sc{n:02d} UGURSUZ: {e}")
            continue
        src = os.path.join(COMFY_OUT, files[-1])
        if not os.path.isfile(src):
            print(f"  sc{n:02d} UGURSUZ: cixis tapilmadi {src}")
            continue
        shutil.move(src, dest)
        el = time.time() - t0
        print(f"  [{k}/{len(todo)}] sc{n:02d}  {el / k:.0f}s/eded  qalan ~{(len(todo) - k) * el / k / 60:.1f} deq")

    save_bg_paths(scenes_path, bg_dir)
    missing = [i + 1 for i in range(len(scenes)) if not os.path.isfile(os.path.join(bg_dir, f"sc{i + 1:02d}.png"))]
    print(f"  bitdi {(time.time() - t0) / 60:.1f} deq;  catismayan: {missing or 'yoxdur'}")


if __name__ == "__main__":
    main()
