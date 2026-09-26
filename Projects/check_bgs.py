"""Fon hakimi: render_bgs-den sonra her fona vision model baxir, pis olanlari yeniden cekir.
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\check_bgs.py Episodes\\<slug> [--provider openai] [--force]
Cixis: Episodes\\<slug>\\bg_qa.json  (her sehnenin hokmu, neche defe yeniden cekildiyi)

Niye: soz filtrleri (TEXT_BEARING, HUMAN) her hali tutmur - her epizodda 6-8 fonda menasiz yazi, insan,
bos/menasiz sehne cixirdi ve montajdan evvel el ile yoxlanib duzeldilirdi. Indi bu is pipeline-dadir:
pis fon -> hakimin teklif etdiyi prompt (yene filtrlerden kecir) -> render_bgs --only (gpt-image).
MAX_ATTEMPTS raunddan sonra hele pisdirse sinanmis FALLBACK_POOL fonu qoyulur - pipeline hec vaxt ilismir.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from llm import DEFAULT_PROVIDER, LLMError, chat_json  # noqa: E402
from scene_plan import FALLBACK_BG, FALLBACK_POOL, clean_bg_prompt  # noqa: E402

MAX_ATTEMPTS = 3
JUDGE_WIDTH = 768
# gpt-4o: sekil "low" detail-de ~85 token (4o-mini ~2800 token sayir ve 6 paralel sorgu 200k TPM
# limitine direndi), gorme deqiqliyi de yuksekdir; epizod ~$0.2
JUDGE_MODEL = "gpt-4o"
WORKERS = 4
REPORT = "bg_qa.json"
# JSON acari -> problem kodu. Her yoxlama ayrica sual: umumi "ok" sualinda model narration-daki
# "you"-dan insan "gorurdu" (97 fonun 84-u "human" cixmisdi)
CHECKS = (("people", "human"), ("writing", "text"), ("collage", "collage"),
          ("no_subject", "empty"), ("deformed", "deformed"), ("off_topic", "mismatch"))

SYSTEM = """You check background images of an explainer video. A cartoon owl is added later, so the image
itself must not contain people. First write "description": one factual sentence of what is ACTUALLY
visible. Then answer each check with true/false, judging ONLY what is visible in the image. The narration
talks to the viewer ("you") - never infer people or writing from it.
- "people": a human or a human body part (face, hand, arm, cartoon child) is clearly visible. Robots,
  robotic hands and toys are NOT people.
- "writing": clearly visible letters, words, numbers or scribbled lines of writing (on paper, boards,
  screens, signs, labels, clipboards). Clock faces, dice dots and tiny unreadable brand specks are fine.
- "collage": several panels, split screen, grid or picture-in-picture.
- "no_subject": no clear main subject - mostly empty, blurry or unrecognisable.
- "deformed": melted, broken or impossible objects that look like generation mistakes.
- "off_topic": the image is unrelated to the narration even as a metaphor, or shows gambling, weapons,
  alcohol or medicine.
Also give "fix_prompt": if any check is true, a new image prompt of 8-20 words - ONE clear physical object
or robot in a simple setting that illustrates the narration as a visual metaphor, with no people, hands,
screens, papers, books, signs, cards or brand names; otherwise "".
Answer ONLY JSON with keys: description, people, writing, collage, no_subject, deformed, off_topic, fix_prompt."""


@dataclass(frozen=True)
class Verdict:
    ok: bool
    problems: tuple[str, ...]
    fix_prompt: str


def parse_verdict(d: dict) -> Verdict:
    """Yalniz acıq True cavab problemdir; eksik acar / "yes" kimi yanlis tip problem sayilmir."""
    problems = tuple(code for key, code in CHECKS if d.get(key) is True)
    fix = d.get("fix_prompt")
    return Verdict(ok=not problems, problems=problems, fix_prompt=fix.strip() if isinstance(fix, str) else "")


def next_prompt(fix: str, attempt: int, used: set[str]) -> str:
    """Hakimin teklifi soz filtrlerinden kecir; son cehdde ve ya teklif yararsizdirsa istifade olunmamis
    FALLBACK_POOL fonu (sinanmis, yazisiz, insansiz)."""
    if attempt < MAX_ATTEMPTS and fix.strip():
        p = clean_bg_prompt(fix)
        if p != FALLBACK_BG:
            return p
    return next((p for p in FALLBACK_POOL if p not in used), FALLBACK_BG)


def apply_changes(scenes_path: str, changes: dict[int, str]) -> None:
    """changes: {sehne nomresi (1-esasli): yeni prompt}. Fayl tezeden oxunur - basqa saheler qorunur."""
    with open(scenes_path, encoding="utf-8") as f:
        data = json.load(f)
    for n, prompt in changes.items():
        data["scenes"][n - 1]["bg_prompt"] = prompt
    with open(scenes_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _image_part(path: str) -> dict:
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((JUDGE_WIDTH, JUDGE_WIDTH))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
    url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": url, "detail": "low"}}


JUDGE_ERROR = Verdict(ok=True, problems=("judge_error",), fix_prompt="")
JUDGE_RETRIES = 3
JUDGE_RETRY_WAIT_S = 30     # TPM limiti deqiqelikdir - 1-4 s-lik backoff kifayet etmirdi


def judge_all(nums: list[int], judge_fn, workers: int = WORKERS, sleep=time.sleep) -> dict[int, Verdict]:
    """Paralel yoxla; API xetasi alanlari gozleyib ARDICIL yeniden yoxla (ep3-de sc89 429 ile yoxlanmadan
    kecmisdi). Son cehdden sonra da xetadirsa fon oldugu kimi qalir - pipeline dayanmir."""
    with ThreadPoolExecutor(workers) as pool:
        res = dict(zip(nums, pool.map(judge_fn, nums)))
    for _ in range(JUDGE_RETRIES):
        failed = [n for n in nums if res[n] is JUDGE_ERROR]
        if not failed:
            break
        sleep(JUDGE_RETRY_WAIT_S)
        for n in failed:
            res[n] = judge_fn(n)
    return res


def judge(path: str, scene: dict, provider: str) -> Verdict:
    text = f"Narration: {scene.get('narration', '')}\nImage prompt used: {scene.get('bg_prompt', '')}"
    try:
        return parse_verdict(chat_json(SYSTEM, [{"type": "text", "text": text}, _image_part(path)],
                                       provider=provider, model=JUDGE_MODEL if provider == "openai" else None,
                                       temperature=0.0, max_tokens=300))
    except LLMError as e:          # hakim elcatmazdirsa pipeline dayanmir - fon oldugu kimi qalir
        print(f"  hakim xetasi ({os.path.basename(path)}): {str(e)[:120]}")
        return JUDGE_ERROR


def rerender(ep: str, nums: list[int]) -> None:
    for n in nums:                 # kohne HD versiya qalmasin - upscale_bgs yenisini cixarsin
        hd = os.path.join(ep, "bg_hd", f"sc{n:02d}.png")
        if os.path.isfile(hd):
            os.remove(hd)
    cmd = [sys.executable, os.path.join(HERE, "render_bgs.py"), ep, "--only", *map(str, nums), "--force"]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--provider", default=DEFAULT_PROVIDER)
    ap.add_argument("--force", action="store_true", help="pipeline uygunlugu ucun; skript her defe butun fonlari yoxlayir")
    a = ap.parse_args()
    ep = os.path.abspath(a.episode_dir)
    scenes_path = os.path.join(ep, "scenes.json")

    report: dict[str, dict] = {}
    with open(scenes_path, encoding="utf-8") as f:
        pending = list(range(1, len(json.load(f)["scenes"]) + 1))
    for attempt in range(1, MAX_ATTEMPTS + 1):
        with open(scenes_path, encoding="utf-8") as f:
            scenes = json.load(f)["scenes"]
        paths = {n: os.path.join(ep, "bg", f"sc{n:02d}.png") for n in pending}
        verdicts = judge_all(pending, lambda n: judge(paths[n], scenes[n - 1], a.provider))
        bad = [n for n in pending if not verdicts[n].ok]
        for n in pending:
            v = verdicts[n]
            report[str(n)] = {"ok": v.ok, "problems": list(v.problems), "attempts": attempt - 1
                              + (0 if v.ok else 1), "prompt": scenes[n - 1]["bg_prompt"]}
        print(f"[qa] raund {attempt}: {len(pending)} yoxlandi, {len(bad)} pis: "
              + ", ".join(f"sc{n:02d}({'/'.join(verdicts[n].problems)})" for n in bad), flush=True)
        if not bad:
            break
        used = {s["bg_prompt"] for s in scenes}
        changes = {}
        for n in bad:
            p = next_prompt(verdicts[n].fix_prompt, attempt, used)
            used.add(p)
            changes[n] = p
            print(f"  sc{n:02d} -> {p}")
        apply_changes(scenes_path, changes)
        rerender(ep, bad)
        pending = bad

    with open(os.path.join(ep, REPORT), "w", encoding="utf-8") as f:
        json.dump({"passed": True, "scenes": report}, f, indent=2, ensure_ascii=False)
    redone = sorted(int(n) for n, r in report.items() if r["attempts"])
    print(f"[qa] bitdi: {len(redone)} fon yeniden cekildi {redone or ''}")


if __name__ == "__main__":
    main()
