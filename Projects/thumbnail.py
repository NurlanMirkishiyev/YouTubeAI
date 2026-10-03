"""Reyestr #47 (istifadeci 2026-10-03): thumbnail daha keyfiyyetli olsun.
Fon artiq sehne fotolarindan secilmir (why-9-99: qiymet movzusunda qehve qovurma masini) - LLM-in verdiyi
movzu konsepti gpt-image-2 "high" ile VARIANTS defe cekilir, gpt-4o hakimi yazi/insan olmayan en cazibedari
secir. Hec biri alinmasa None - publish_pack kohne yola (en kontrastli sehne fotosu) qayidir, pipeline dayanmir.
"""
from __future__ import annotations

import io
import os
from typing import Callable

from PIL import Image

from llm import LLMError, chat_json, generate_image
from render_bgs import crop_16x9
from scene_plan import clean_bg_prompt

MODEL = "gpt-image-2"
QUALITY = "high"
SIZE = "1536x1024"
VARIANTS = 2
JUDGE_MODEL = "gpt-4o"

STYLE = ("Striking YouTube thumbnail background, realistic editorial photograph, dramatic cinematic lighting, "
         "bold saturated colours with strong contrast, sharp focus on ONE large hero subject, shallow depth of field.")
LAYOUT = ("Composition: the hero subject sits in the centre-right, large and close; the left third is calm, dark "
          "and empty for a headline; the bottom-right corner is uncluttered.")
RULES = "No text, letters, numbers, logos, signs, people, faces or animals. Adult, premium look, not childish."

JUDGE_SYSTEM = """You rate YouTube thumbnail BACKGROUNDS (a headline and a cartoon owl are added later).
Answer ONLY JSON: {"writing": bool (any visible letters, numbers or logos), "people": bool (any human or body part),
"score": 0-10 (how eye-catching it is at small size: one bold clear subject, strong contrast and colour,
dark calm left third for text, professional adult look)}."""


def thumb_prompt(concept: str) -> str:
    scene = clean_bg_prompt(" ".join(str(concept).split()))
    return f"{STYLE} Scene: {scene}. {LAYOUT} {RULES}"


def pick_best(verdicts: dict[str, dict | None]) -> str | None:
    ok = {p: v for p, v in verdicts.items()
          if isinstance(v, dict) and v.get("writing") is False and v.get("people") is False}
    return max(ok, key=lambda p: float(ok[p].get("score") or 0)) if ok else None


def _generate(prompt: str) -> bytes:
    return generate_image(prompt, model=MODEL, size=SIZE, quality=QUALITY)


def _judge(path: str) -> dict | None:
    from check_bgs import _image_part
    try:
        return chat_json(JUDGE_SYSTEM, [{"type": "text", "text": "Rate this background."}, _image_part(path)],
                         model=JUDGE_MODEL, temperature=0.0, max_tokens=80)
    except LLMError as e:
        print(f"  thumbnail hakimi xetasi: {str(e)[:120]}", flush=True)
        return None


def make_background(concept: str, out_dir: str, generate: Callable[[str], bytes] = _generate,
                    judge: Callable[[str], dict | None] = _judge) -> str | None:
    prompt = thumb_prompt(concept)
    paths = []
    for k in range(1, VARIANTS + 1):
        try:
            data = generate(prompt)
        except LLMError as e:
            print(f"  thumbnail fonu {k} cekilmedi: {str(e)[:120]}", flush=True)
            continue
        path = os.path.join(out_dir, f"thumb_bg_{k}.png")
        with Image.open(io.BytesIO(data)) as im:
            crop_16x9(im.convert("RGB")).save(path)
        paths.append(path)
    if not paths:
        return None
    best = pick_best({p: judge(p) for p in paths})
    print(f"  thumbnail fonu: {os.path.basename(best) if best else 'hakimden kecmedi - kohne yol'}", flush=True)
    return best
