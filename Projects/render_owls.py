"""Sehne bayqusu: her sehnenin "owl_action"-una uygun bayqus sekli (ChatGPT, seffaf fon) + vision hakimi.
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\render_owls.py Episodes\\<slug> [--provider openai] [--force]
Cixis: Episodes\\<slug>\\owl\\scNN.png, owl\\intro.png, owl\\outro.png  +  owl_qa.json

Istifadeci 2026-09-27: "personaj her sehnede metne uygun, detalli gorunsun, amma esl gorunusu deyismesin".
Referans sprite (front) /images/edits-e verilir - model eynek/kostyum/qalstuku eyni saxlayir.
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
MODEL = "gpt-image-1.5"   # 2026-09-30: gpt-image-2 seffaf fonu redd edir (HTTP 400); 1.5 personaji
                          # referansa en yaxin saxladi (gpt-image-1 ile muqayise probu), alpha temiz
QUALITY = "low"
SIZE = "1024x1536"
MAX_ATTEMPTS = 3
PAD = 6                  # alpha kesiminden sonra kenar (px) - kontur kesilmesin
ALPHA_MIN = 16
WORKERS = 4
REPORT = "owl_qa.json"
JUDGE_MODEL = "gpt-4o"
FATAL_MARK = "not supported for this model"

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
  changed, a picture or print on the shirt/suit, different species, very different face or art style).
  A new pose, prop or emotion is fine.
- "cropped": the owl's head or feet are cut off by the image edge.
- "writing": visible letters, words or numbers.
- "people": a human or human body part is visible.
- "extra_owls": more than one owl, or any other character, creature or face is visible - including one
  printed or drawn on the clothes or on a prop.
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


def owl_path(ep: str, n: int | str) -> str:
    name = n if isinstance(n, str) else f"sc{n:02d}"
    return os.path.join(ep, "owl", f"{name}.png")


DEFAULT_PROP = "a brown leather briefcase"
PROP_SYSTEM = """You pick ONE prop for a cartoon owl mascot (business explainer channel for adults).
The prop must be a single concrete, realistic, everyday physical object that an adult immediately links
to the topic. Rules: no screens, no phones, no tablets, no documents, no charts, no writing, no letters,
no numbers, no logos, no characters or faces. Short noun phrase, max 8 words, e.g. "a leather wallet with a
few banknotes", "a card payment terminal", "a small balance scale", "a piggy bank" (only if fitting).
Return JSON only: {"prop": "..."}"""


def choose_prop(topic: str, chat: Callable = chat_json, **llm_kw) -> str:
    """Movzu esyasi (2026-09-30): "movzunu temsil eden esya" deyende model planset ustunde cizgi fiquru
    cekirdi - esya evvelceden konkret secilir ve giris/cixisda eyni olur."""
    try:
        prop = str(chat(PROP_SYSTEM, f"Topic: {topic}", temperature=0.2, max_tokens=60, **llm_kw)
                   .get("prop", "")).strip()
    except LLMError as e:
        print(f"  esya secilmedi ({str(e)[:80]}) - default", flush=True)
        prop = ""
    return prop or DEFAULT_PROP


def card_actions(topic: str, prop: str) -> dict[str, str]:
    """Giris/cixis karti ucun movzuya uygun, acilis ve qapanis oldugu aydin gorunen pozlar (2026-09-30).
    Eyni movzu esyasi her ikisinde - kartlar bir-birine baglanir."""
    return {
        "intro": (f"opening the video about \"{topic}\": welcoming the viewer and presenting the topic - one "
                  f"wing stretched wide open to the side in an inviting 'let's begin' gesture, eyes wide with "
                  f"excitement, big open smile, holding {prop} up proudly in the other wing"),
        "outro": (f"closing the video about \"{topic}\": saying goodbye - waving farewell with one wing raised "
                  f"high, happy closed-eye smile, head slightly bowed in thanks, the same {prop} tucked "
                  f"under the other arm"),
    }


def _draw(ep: str, n: int | str, action: str, gen: Callable[[str], bytes]) -> bool:
    try:
        data = gen(build_owl_prompt(action))
    except LLMError as e:
        if FATAL_MARK in str(e):
            raise      # model/parametr sehvi - her bayqus sprite-a duser, sessizce kecmek olmaz
        print(f"  {os.path.basename(owl_path(ep, n))}: bayqus cekilmedi ({str(e)[:100]})", flush=True)
        return False
    with Image.open(io.BytesIO(data)) as im:
        trim_alpha(im).save(owl_path(ep, n))
    return True


def _run_named(ep: str, actions: dict, gen: Callable[[str], bytes], judge: Callable,
               workers: int = WORKERS) -> dict[str, dict]:
    """actions {acar: hereket} ucun cekir, hakimden kecmeyenleri yeniden cekir (MAX_ATTEMPTS).
    Hele pis olan / cekilmeyen sekil silinir -> remotion_build kohne sprite-i gosterir."""
    os.makedirs(os.path.join(ep, "owl"), exist_ok=True)
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
              + ", ".join(f"{os.path.basename(owl_path(ep, n))[:-4]}({'/'.join(report[str(n)]['problems'])})"
                          for n in pending), flush=True)
        if not pending:
            break
    for n in pending:
        if os.path.isfile(owl_path(ep, n)):
            os.remove(owl_path(ep, n))
    return report


def run(ep: str, scenes: list[dict], gen: Callable[[str], bytes], judge: Callable[[str, int], Verdict],
        workers: int = WORKERS) -> dict[str, dict]:
    """Hereketi olan her sehne ucun bayqus (owl/scNN.png)."""
    actions = {i + 1: s.get("owl_action", "").strip() for i, s in enumerate(scenes)}
    return _run_named(ep, actions, gen, judge, workers)


def run_cards(ep: str, topic: str, gen: Callable[[str], bytes], judge: Callable[[str, str], Verdict],
              workers: int = WORKERS, prop: str = DEFAULT_PROP) -> dict[str, dict]:
    """Giris/cixis karti bayqusu (owl/intro.png, owl/outro.png) - sehne bayqusu ile eyni referans ve hakim."""
    report = _run_named(ep, card_actions(topic, prop), gen, judge, workers)
    return {k: {**v, "prop": prop} for k, v in report.items()}


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

    gen = with_429_retry(raw_gen)
    report = run(ep, scenes, gen, lambda p, n: judge_owl(p, a.provider))
    topic = episode_topic(ep)
    prop = choose_prop(topic, provider=a.provider)
    print(f"[owl] giris/cixis karti: movzu esyasi = {prop}", flush=True)
    cards = run_cards(ep, topic, gen, lambda p, n: judge_owl(p, a.provider), prop=prop)
    with open(os.path.join(ep, REPORT), "w", encoding="utf-8") as f:
        json.dump({"scenes": report, "cards": cards}, f, indent=2, ensure_ascii=False)
    bad = sorted(int(n) for n, r in report.items() if not r["ok"])
    print(f"[owl] bitdi: {len(report) - len(bad)} sehne bayqusu, kohne poza dusen: {bad or 'yoxdur'}; "
          f"kart: " + ", ".join(f"{k}={'ok' if v['ok'] else 'sprite'}" for k, v in cards.items()))


def episode_topic(ep: str) -> str:
    path = os.path.join(ep, "meta.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            topic = str(json.load(f).get("topic", "")).strip()
        if topic:
            return topic
    return os.path.basename(ep.rstrip("\\/")).replace("-", " ")


if __name__ == "__main__":
    main()
