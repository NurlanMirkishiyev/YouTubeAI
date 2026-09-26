"""scenes.json -> her sehne ucun fon PNG (OpenAI gpt-image, ChatGPT sekil modeli).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\render_bgs.py Episodes\\<slug> [--only 3 7] [--force]
Cixis: Episodes\\<slug>\\bg\\sc01.png ... (1536x864, 16:9)   (scenes.json-a "bg" sahesi yazilir)

2026-09-26: SDXL (lokal ComfyUI) evezine gpt-image. SDXL yazi cekmeyi bacarmir ve menasiz "psevdo-yazi",
insan, qarisiq obyektler verirdi; gpt-image kompozisiya telimatina (bayqus ucun bos teref) emel edir.
Keyfiyyet "low" - istifadecinin secimi (~$1.5/video, gpt-image-1 olcusu ile).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import LLMError, generate_image  # noqa: E402
from scene_plan import FALLBACK_BG  # noqa: E402

MODEL = "gpt-image-2"     # 2026-09-26 probu: kompozisiyaya gpt-image-1-den yaxsi emel etdi
QUALITY = "low"
SIZE = "1536x1024"        # en genis olcu; 16:9-a kesilir
WORKERS = 4
IMAGES_PER_MIN = 5        # OpenAI hesab limiti (2026-09-26: "input-images per min: Limit 5"); tier artsa boyut
RETRIES_429 = 6
STYLE = ("3D Pixar-style animated render, soft studio lighting, vibrant friendly colors, "
         "clean simple composition with one clear main subject, wide 16:9 framing.")
RULES = "No text, no letters, no numbers, no logos, no people, no hands."
# bayqus hansi terefdedirse, fonun o terefi bos qalmalidir
SPACE = {"right": "The main subject is on the left half; calm empty space on the right side.",
         "left": "The main subject is on the right half; calm empty space on the left side.",
         "center": "Empty uncluttered space in the lower center."}


class RateLimiter:
    """Surusen 60 s pencerede en cox per_min baslangic (thread-safe). Hesabin gpt-image limiti
    deqiqede 5 sekildir - limitsiz 4 paralel sorgu 97 sekilden 55-ni 429 ile itirdi (ep4)."""

    def __init__(self, per_min: int, now=time.monotonic, sleep=time.sleep):
        self.per_min, self.now, self.sleep = per_min, now, sleep
        self.starts: list[float] = []
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            while True:
                t = self.now()
                self.starts = [s for s in self.starts if t - s < 60.0]
                if len(self.starts) < self.per_min:
                    self.starts.append(t)
                    return
                self.sleep(60.0 - (t - self.starts[0]) + 0.1)


_WAIT = re.compile(r"try again in ([\d.]+)\s*(ms|s)", re.I)


def with_429_retry(gen, sleep=time.sleep, attempts: int = RETRIES_429):
    """429-da API-nin dediyi qeder (+1 s) gozle ve tekrarla; diger xetalar oldugu kimi atilir."""
    def wrapped(prompt: str) -> bytes:
        for k in range(attempts):
            try:
                return gen(prompt)
            except LLMError as e:
                if "429" not in str(e) or k == attempts - 1:
                    raise
                m = _WAIT.search(str(e))
                wait = (float(m[1]) / (1000 if m[2].lower() == "ms" else 1) if m else 15.0) + 1.0
                sleep(max(wait, 5.0))
        raise AssertionError("unreachable")
    return wrapped


def build_prompt(scene_prompt: str, pos: str) -> str:
    return f"{STYLE} {SPACE.get(pos, SPACE['right'])} {RULES} Scene: {scene_prompt}"


def crop_16x9(im: Image.Image) -> Image.Image:
    """Tam en saxlanir, yuxari/asagi beraber kesilir."""
    w, h = im.size
    th = round(w * 9 / 16)
    top = (h - th) // 2
    return im.crop((0, top, w, top + th))


def render_one(scene: dict, dest: str, gen) -> None:
    """gen(prompt) -> PNG baytlari. Prompt redd edilse (moderation ve s.) FALLBACK_BG ile bir defe de."""
    pos = scene.get("pos", "right")
    try:
        data = gen(build_prompt(scene["bg_prompt"], pos))
    except LLMError as e:
        print(f"  {os.path.basename(dest)}: prompt redd edildi ({str(e)[:100]}) - ehtiyat fon", flush=True)
        data = gen(build_prompt(FALLBACK_BG, pos))
    with Image.open(io.BytesIO(data)) as im:
        crop_16x9(im.convert("RGB")).save(dest, compress_level=3)


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--only", nargs="*", type=int, help="yalniz bu sehne nomreleri (1-esasli)")
    ap.add_argument("--force", action="store_true", help="movcud PNG-leri yenidden cek")
    a = ap.parse_args()

    scenes_path = os.path.join(a.episode_dir, "scenes.json")
    if not os.path.isfile(scenes_path):
        raise SystemExit("scenes.json tapilmadi: " + scenes_path)
    with open(scenes_path, encoding="utf-8") as f:
        scenes = json.load(f)["scenes"]
    bg_dir = os.path.join(a.episode_dir, "bg")
    os.makedirs(bg_dir, exist_ok=True)

    def dest(i: int) -> str:
        return os.path.join(bg_dir, f"sc{i + 1:02d}.png")

    todo = [i for i in range(len(scenes))
            if (not a.only or i + 1 in a.only) and (a.force or not os.path.isfile(dest(i)))]
    print(f"[24] {len(todo)}/{len(scenes)} sehne cekilecek ({MODEL}/{QUALITY}) -> {bg_dir}", flush=True)

    limiter = RateLimiter(IMAGES_PER_MIN)

    def raw_gen(prompt: str) -> bytes:
        limiter.acquire()
        return generate_image(prompt, model=MODEL, size=SIZE, quality=QUALITY)

    gen = with_429_retry(raw_gen)
    print(f"  limit: deqiqede {IMAGES_PER_MIN} sekil -> ~{len(todo) / IMAGES_PER_MIN:.0f} deq", flush=True)

    def job(i: int) -> str | None:
        try:
            render_one(scenes[i], dest(i), gen)
            return None
        except (LLMError, OSError) as e:
            return f"sc{i + 1:02d}: {str(e)[:150]}"

    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as pool:
        errors = [e for e in pool.map(job, todo) if e]
    save_bg_paths(scenes_path, bg_dir)
    missing = [i + 1 for i in range(len(scenes)) if not os.path.isfile(dest(i))]
    print(f"  bitdi {(time.time() - t0) / 60:.1f} deq;  catismayan: {missing or 'yoxdur'}", flush=True)
    if errors:
        for e in errors:
            print("  UGURSUZ " + e, flush=True)
        raise SystemExit(f"{len(errors)} fon cekilmedi")


if __name__ == "__main__":
    main()
