"""Sehne bayqusu: her sehnenin "owl_action"-una uygun bayqus sekli (ChatGPT, seffaf fon) + vision hakimi.
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\render_owls.py Episodes\\<slug> [--provider openai] [--force]
Cixis: Episodes\\<slug>\\owl\\scNN.png  +  owl_qa.json

Istifadeci 2026-09-27: "personaj her sehnede metne uygun, detalli gorunsun, amma esl gorunusu deyismesin".
Referans sprite (front) /images/edits-e verilir - probda gpt-image-2 eynek/kostyum/qalstuku eyni saxladi.
Hakim referansla muqayise edir; MAX_ATTEMPTS-den sonra hele pisdirse sekil silinir ve o sehnede
kohne poz sprite-i gosterilir - pipeline hec vaxt ilismir.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from llm import DEFAULT_PROVIDER, LLMError, chat_json, edit_image  # noqa: E402

OWL_REF = os.path.join(os.path.dirname(HERE), "Character", "ELI5_Owl", "sprites_hd", "front.png")
MODEL = "gpt-image-2"
QUALITY = "low"
SIZE = "1024x1536"
MAX_ATTEMPTS = 3
PAD = 6                  # alpha kesiminden sonra kenar (px) - kontur kesilmesin
ALPHA_MIN = 16
WORKERS = 4
REPORT = "owl_qa.json"
JUDGE_MODEL = "gpt-4o"

CHARACTER = ("The exact same cartoon owl character as in the reference image: same brown feathers and "
             "feather tuft, same round black glasses, same navy suit, white shirt, yellow tie and brown belt, "
             "same proportions, face and 3D Pixar-like art style.")
RULES = ("Only this one owl (plus the single prop if mentioned). Full body from head to feet, feet visible, "
         "standing, centered. Transparent background, no shadow on the ground, no text, no letters, "
         "no people, no other animals.")

CHECKS = (("different_character", "identity"), ("cropped", "cropped"), ("writing", "text"),
          ("people", "human"), ("extra_owls", "extra_owl"), ("deformed", "deformed"))

SYSTEM = """You compare two images of a cartoon mascot. Image 1 is the REFERENCE owl. Image 2 is a new
drawing that must show the SAME character in a new pose. Answer each check with true/false, judging only
what is visible:
- "different_character": image 2 is not clearly the same owl (glasses missing or different, suit/tie colour
  changed, different species, very different face or art style). A new pose, prop or emotion is fine.
- "cropped": the owl's head or feet are cut off by the image edge.
- "writing": visible letters, words or numbers.
- "people": a human or human body part is visible.
- "extra_owls": more than one owl is visible.
- "deformed": broken anatomy (extra limbs, melted face) or a prop fused into the body.
Answer ONLY JSON with keys: different_character, cropped, writing, people, extra_owls, deformed."""


@dataclass(frozen=True)
class Verdict:
    ok: bool
    problems: tuple[str, ...]


JUDGE_ERROR = Verdict(True, ("judge_error",))    # hakim elcatmazdirsa sekil qalir


def build_owl_prompt(action: str) -> str:
    return f"{CHARACTER} New pose for this scene: {action}. {RULES}"


def parse_owl_verdict(d: dict) -> Verdict:
    problems = tuple(code for key, code in CHECKS if d.get(key) is True)
    return Verdict(not problems, problems)


def trim_alpha(im: Image.Image) -> Image.Image:
    """Seffaf kenarlari kesir - ekranda olcu bayqusun ozune gore hesablanir, bos sahe ile yox."""
    im = im.convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a >= ALPHA_MIN else 0).getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(0, l - PAD), max(0, t - PAD), min(im.width, r + PAD), min(im.height, b + PAD)))


def owl_path(ep: str, n: int) -> str:
    return os.path.join(ep, "owl", f"sc{n:02d}.png")


def _draw(ep: str, n: int, action: str, gen: Callable[[str], bytes]) -> bool:
    try:
        data = gen(build_owl_prompt(action))
    except LLMError as e:
        print(f"  sc{n:02d}: bayqus cekilmedi ({str(e)[:100]})", flush=True)
        return False
    with Image.open(io.BytesIO(data)) as im:
        trim_alpha(im).save(owl_path(ep, n))
    return True


def run(ep: str, scenes: list[dict], gen: Callable[[str], bytes], judge: Callable[[str, int], Verdict],
        workers: int = WORKERS) -> dict[str, dict]:
    """Hereketi olan her sehne ucun bayqus cekir, hakimden kecmeyenleri yeniden cekir (MAX_ATTEMPTS).
    Hele pis olan / cekilmeyen sekil silinir -> remotion_build kohne poz sprite-ini gosterir."""
    os.makedirs(os.path.join(ep, "owl"), exist_ok=True)
    actions = {i + 1: s.get("owl_action", "").strip() for i, s in enumerate(scenes)}
    pending = [n for n, a in actions.items() if a]
    report: dict[str, dict] = {}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        with ThreadPoolExecutor(workers) as pool:
            drawn = dict(zip(pending, pool.map(lambda n: _draw(ep, n, actions[n], gen), pending)))
        ok_draw = [n for n in pending if drawn[n]]
        with ThreadPoolExecutor(workers) as pool:
            verdicts = dict(zip(ok_draw, pool.map(lambda n: judge(owl_path(ep, n), n), ok_draw)))
        for n in pending:
            v = verdicts.get(n, Verdict(False, ("not_drawn",)))
            report[str(n)] = {"ok": v.ok, "problems": list(v.problems), "attempts": attempt, "action": actions[n]}
        pending = [n for n in pending if not report[str(n)]["ok"]]
        print(f"[owl] raund {attempt}: {len(pending)} pis "
              + ", ".join(f"sc{n:02d}({'/'.join(report[str(n)]['problems'])})" for n in pending), flush=True)
        if not pending:
            break
    for n in pending:
        if os.path.isfile(owl_path(ep, n)):
            os.remove(owl_path(ep, n))
    return report


def judge_owl(path: str, provider: str) -> Verdict:
    from check_bgs import _image_part
    try:
        return parse_owl_verdict(chat_json(
            SYSTEM, [{"type": "text", "text": "Image 1 (reference), then image 2 (new drawing)."},
                     _image_part(OWL_REF), _image_part(path)],
            provider=provider, model=JUDGE_MODEL if provider == "openai" else None,
            temperature=0.0, max_tokens=200))
    except LLMError as e:
        print(f"  hakim xetasi ({os.path.basename(path)}): {str(e)[:120]}")
        return JUDGE_ERROR


def main() -> None:
    from render_bgs import IMAGES_PER_MIN, RateLimiter, with_429_retry
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--provider", default=DEFAULT_PROVIDER)
    ap.add_argument("--force", action="store_true", help="pipeline uygunlugu ucun; her defe hamisi cekilir")
    a = ap.parse_args()
    ep = os.path.abspath(a.episode_dir)
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        scenes = json.load(f)["scenes"]
    todo = sum(1 for s in scenes if s.get("owl_action"))
    print(f"[owl] {todo}/{len(scenes)} sehne ucun bayqus ({MODEL}/{QUALITY}, ~{todo / IMAGES_PER_MIN:.0f} deq)",
          flush=True)
    limiter = RateLimiter(IMAGES_PER_MIN)

    def raw_gen(prompt: str) -> bytes:
        limiter.acquire()
        return edit_image(prompt, OWL_REF, model=MODEL, size=SIZE, quality=QUALITY)

    report = run(ep, scenes, with_429_retry(raw_gen), lambda p, n: judge_owl(p, a.provider))
    with open(os.path.join(ep, REPORT), "w", encoding="utf-8") as f:
        json.dump({"scenes": report}, f, indent=2, ensure_ascii=False)
    bad = sorted(int(n) for n, r in report.items() if not r["ok"])
    print(f"[owl] bitdi: {len(report) - len(bad)} sehne bayqusu, kohne poza dusen: {bad or 'yoxdur'}")


if __name__ == "__main__":
    main()
