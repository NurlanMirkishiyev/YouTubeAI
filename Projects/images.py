"""Sehne fotolari gpt-image-2 (1536x1024). Alinmasa retry, tehlukesizlik reddinde prompt eyni movzuda yeniden
yazilir; hamisi tukense merhele dayanir (foto hec vaxt animasiya ile evez olunmur, --resume yeniden cekir)."""
from __future__ import annotations

import json
import os

import generate
import llm
import ratelimit

STYLE = (" Realistic documentary photograph, natural light, sharp detail, 16:9. No readable text, letters or logos."
         " No owl, no mascot, no cartoon characters.")


def _one(path: str, prompt: str, gen, limiter, rewrite) -> None:
    def draw(p: str) -> None:
        if limiter:
            limiter.acquire()
        generate.atomic_bytes(path, gen(p + STYLE))
    generate.with_retry(draw, prompt, rewrite=rewrite, label=f"foto {os.path.basename(path)}")


def render_photos(ep: str, gen=None, workers: int = 3, limiter=ratelimit.IMAGE_LIMITER,
                  rewrite=llm.rewrite_safe) -> None:
    gen = gen or (lambda p: llm.generate_image(p))
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.join(ep, "img"), exist_ok=True)
    todo = [s for s in data["scenes"] if s["type"] == "photo"
            and not os.path.isfile(os.path.join(ep, "img", f"sc{s['n']:02d}.png"))]
    generate.run_parallel(lambda s: _one(os.path.join(ep, "img", f"sc{s['n']:02d}.png"),
                                         s.get("photo_prompt") or s.get("visual") or s["text"], gen, limiter, rewrite),
                          todo, workers)
    print(f"  foto: {len(todo)} cekildi", flush=True)
