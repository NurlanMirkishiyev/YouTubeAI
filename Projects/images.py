"""Sehne fotolari gpt-image-2 (1536x1024). Alinmasa retry, tehlukesizlik reddinde prompt eyni movzuda yeniden
yazilir; hamisi tukense merhele dayanir (foto hec vaxt animasiya ile evez olunmur, --resume yeniden cekir).
Eyni sekil olmur: her yeni fotonun dHash-i epizodun diger fotolari ile muqayise olunur, cox oxsardirsa
"ferqli kompozisiya" ile yeniden cekilir. Intro/outro fonu da burada cekilir."""
from __future__ import annotations

import glob
import io
import json
import os
import threading

import numpy as np
from PIL import Image

import generate
import llm
import ratelimit

STYLE = (" Realistic documentary photograph, natural light, sharp detail, 16:9. No readable text, letters or logos."
         " No owl, no mascot, no cartoon characters.")
PHOTO_TYPES = ("photo", "intro", "outro")
DUP_BITS = 8                    # 64 bitlik dHash-de bu qeder ve ya az ferq -> eyni sekil sayilir
VARY = " Different composition, camera angle and setting."


class DuplicateImage(Exception):
    pass


def dhash(data: bytes) -> int:
    g = np.asarray(Image.open(io.BytesIO(data)).convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).ravel()
    return int("".join("1" if b else "0" for b in bits), 2)


class Seen:
    """Epizodun fotolarinin dHash-leri (thread-safe)."""

    def __init__(self, paths: list[str]):
        self.lock = threading.Lock()
        self.hashes = {p: dhash(open(p, "rb").read()) for p in paths}

    def claim(self, path: str, h: int) -> str | None:
        """Oxsar foto yoxdursa h-ni qeyd edir ve None qaytarir; varsa onun yolunu."""
        with self.lock:
            twin = next((p for p, x in self.hashes.items() if p != path and bin(h ^ x).count("1") <= DUP_BITS), None)
            if twin is None:
                self.hashes[path] = h
            return twin


def _one(path: str, prompt: str, gen, limiter, rewrite, seen: Seen) -> None:
    tries = {"dup": 0}

    def draw(p: str) -> None:
        if limiter:
            limiter.acquire()
        data = gen(p + STYLE + (VARY * min(tries["dup"], 1)))
        twin = seen.claim(path, dhash(data))
        if twin:
            tries["dup"] += 1
            raise DuplicateImage(f"{os.path.basename(twin)} ile eyni - ferqli kompozisiya ile yeniden")
        generate.atomic_bytes(path, data)
    generate.with_retry(draw, prompt, rewrite=rewrite, label=f"foto {os.path.basename(path)}")


def render_photos(ep: str, gen=None, workers: int = 3, limiter=ratelimit.IMAGE_LIMITER,
                  rewrite=llm.rewrite_safe) -> None:
    gen = gen or (lambda p: llm.generate_image(p))
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.join(ep, "img"), exist_ok=True)
    todo = [s for s in data["scenes"] if s["type"] in PHOTO_TYPES
            and not os.path.isfile(os.path.join(ep, "img", f"sc{s['n']:02d}.png"))]
    seen = Seen([p for p in glob.glob(os.path.join(ep, "img", "sc*.png")) if ".tmp." not in p])
    generate.run_parallel(lambda s: _one(os.path.join(ep, "img", f"sc{s['n']:02d}.png"),
                                         s.get("photo_prompt") or s.get("visual") or s["text"], gen, limiter,
                                         rewrite, seen),
                          todo, workers)
    print(f"  foto: {len(todo)} cekildi", flush=True)
