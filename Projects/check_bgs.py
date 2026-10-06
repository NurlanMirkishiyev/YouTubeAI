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
from scene_plan import (FALLBACK_BG, FALLBACK_POOL, case_note, clean_bg_prompt, episode_plan,  # noqa: E402
                        episode_topic, hero)
from visuals import animate_abstract  # noqa: E402
import render_bgs  # noqa: E402

MAX_ATTEMPTS = 3
# Tekrar kadr (CLIP oxsarligi) ucun elave raundlar - her raundda tekrar olan sonraki sehneler yeniden cekilir
DEDUPE_ROUNDS = 3
MUSIC_PY = os.path.join(os.path.dirname(HERE), "MusicGen", ".venv", "Scripts", "python.exe")   # torch burada
JUDGE_WIDTH = 768
# gpt-4o: sekil "low" detail-de ~85 token (4o-mini ~2800 token sayir ve 6 paralel sorgu 200k TPM
# limitine direndi), gorme deqiqliyi de yuksekdir; epizod ~$0.2
JUDGE_MODEL = "gpt-4o"
WORKERS = 4
REPORT = "bg_qa.json"
# JSON acari -> problem kodu. Her yoxlama ayrica sual: umumi "ok" sualinda model narration-daki
# "you"-dan insan "gorurdu" (97 fonun 84-u "human" cixmisdi)
CHECKS = (("people", "human"), ("writing", "text"), ("collage", "collage"),
          ("no_subject", "empty"), ("deformed", "deformed"), ("off_topic", "mismatch"),
          ("childish", "childish"), ("generic", "generic"))
GENERIC_MAX = 0.10          # #60 (istifadeci 2026-10-05): generik/metafor kadrlar 10%-den az

SYSTEM = """You check background images of an explainer video. A cartoon owl is added later, so the image
itself must not contain people. First write "description": one factual sentence of what is ACTUALLY
visible. Then answer each check with true/false, judging ONLY what is visible in the image. The narration
talks to the viewer ("you") - never infer people or writing from it.
- "people": a human or a human body part (face, hand, arm, cartoon child) is clearly visible. Robots
  and robotic hands are NOT people.
- "writing": clearly visible letters, words, numbers or scribbled lines of writing (on paper, boards,
  screens, signs, labels, clipboards). Clock faces, dice dots and tiny unreadable brand specks are fine.
- "collage": several panels, split screen, grid or picture-in-picture.
- "no_subject": no clear main subject - mostly empty, blurry or unrecognisable.
- "deformed": melted, broken or impossible objects that look like generation mistakes.
- "off_topic": the image is unrelated to the narration even as a metaphor, or shows gambling, weapons,
  alcohol or medicine.
- "childish": it looks like a children's video - toys, candy, carnival or playground things, cartoonish
  plastic toy-like objects, or a cute kids-show look. The video is for adult professionals.
- "generic": a generic stock picture or a symbolic metaphor (piggy bank, hourglass, chess piece, light bulb,
  compass, lighthouse, coins on a table, empty desk) instead of the LITERAL business, place, product, tool or
  machine the narration is about. A real place, room, tool, machine or product of the case business named
  in the message (e.g. the agency's own workroom or meeting room) is NOT generic, even if it looks ordinary.
Also give "fix_prompts": if any check is true, a list of 3 DIFFERENT new image prompts of 8-20 words each -
ONE clear real-world place, product, tool or machine of the case business (or the business in the narration
when no case is given), shown literally as a
photo (never a symbolic metaphor). Each main object must differ from every object already used in other scenes.
Nothing that carries writing: no price tags, menus, receipts, labels, packaging brands, signs, screens,
papers, books or cards - show the idea through the physical thing itself. No people, hands or toys.
Otherwise [].
Answer ONLY JSON with keys: description, people, writing, collage, no_subject, deformed, off_topic, childish,
generic, fix_prompts."""


@dataclass(frozen=True)
class Verdict:
    ok: bool
    problems: tuple[str, ...]
    fix_prompt: str
    fix_options: tuple[str, ...] = ()


def parse_verdict(d: dict) -> Verdict:
    """Yalniz acıq True cavab problemdir; eksik acar / "yes" kimi yanlis tip problem sayilmir.
    Reyestr #32: hakim bir nece teklif verir (fix_prompts) - biri redd olunsa novbeti yoxlanir."""
    problems = tuple(code for key, code in CHECKS if d.get(key) is True)
    raw = d.get("fix_prompts") if isinstance(d.get("fix_prompts"), list) else []
    raw = [*raw, d.get("fix_prompt")]
    options = tuple(dict.fromkeys(f.strip() for f in raw if isinstance(f, str) and f.strip()))
    return Verdict(ok=not problems, problems=problems, fix_prompt=options[0] if options else "",
                   fix_options=options)


def next_prompt(fix: str | tuple[str, ...], attempt: int, used: set[str]) -> str:
    """Hakimin teklifleri (sira ile) soz filtrlerinden kecir; ilk yararlisi goturulur. Son cehdde ve ya hec
    biri yararsizdirsa istifade olunmamis FALLBACK_POOL fonu. Istifadeci (2026-09-28): tekrar kadr QETI
    olmasin - epizodda olan obyekt (hero) ne teklifde, ne ehtiyat fonda tekrarlanmir."""
    used_heroes = {hero(u) for u in used}
    options = (fix,) if isinstance(fix, str) else tuple(fix)
    cleaned = [clean_bg_prompt(f) for f in options if f.strip()] or [FALLBACK_BG]

    def fresh(p: str) -> bool:
        return p != FALLBACK_BG and p not in used and hero(p) not in used_heroes

    good = next((p for p in cleaned if fresh(p)), None)
    if attempt < MAX_ATTEMPTS and good:
        return good
    pick = next((p for p in FALLBACK_POOL if fresh(p)), None) or good
    if pick is None:
        raise RuntimeError("tekrarsiz ehtiyat fon qalmadi")
    return pick


def rejection_reason(option: str, used: set[str]) -> str | None:
    """Teklif niye redd olunur (hakime geri bildirim ucun); yararlidirsa None."""
    cleaned = clean_bg_prompt(option)
    if cleaned == FALLBACK_BG:
        return "carries writing (price tags, menus, labels, screens, signs, papers)"
    h = hero(cleaned)
    if cleaned in used or h in {hero(u) for u in used}:
        return f"main object '{h}' is already used in another scene"
    return None


SUGGEST_SYSTEM = """You write background image prompts for one scene of an explainer video for adults.
Your earlier suggestions were rejected for the reasons given. Give 5 NEW prompts of 8-20 words: ONE clear
real-world object or place of the case business (when one is given) shown as a realistic photo that fits
the narration - never another kind of business. Every main object must be
different from the objects already used. Nothing that carries writing or numbers: no price tags, menus,
receipts, labels, signs, screens, registers' displays, papers, books or cards. No people, hands or toys.
Answer ONLY JSON: {"fix_prompts": [...]}"""


def suggest_again(scene: dict, feedback: str, used: set[str], provider: str, case: str = "") -> tuple[str, ...]:
    """Butun teklifler redd olunanda sebebleri bildirib yeni teklifler (yalniz metn, sekil yoxdur)."""
    text = (f"{case}Narration: {scene.get('narration', '')}\nRejected: {feedback}\n"
            f"Objects already used: {'; '.join(sorted(used))}")
    try:
        return parse_verdict(chat_json(SUGGEST_SYSTEM, text, provider=provider,
                                       model=JUDGE_MODEL if provider == "openai" else None,
                                       temperature=0.7, max_tokens=400)).fix_options
    except LLMError as e:
        print(f"  teklif xetasi: {str(e)[:120]}")
        return ()


def choose_prompt(v: Verdict, attempt: int, used: set[str], suggest) -> str:
    """Reyestr #32: hakimin teklifleri redd olunanda derhal movzudan kenar ehtiyat fona kecilmir -
    sebebler bildirilib bir defe yeni teklif alinir (suggest(feedback) -> teklifler)."""
    p = next_prompt(v.fix_options, attempt, used)
    if attempt >= MAX_ATTEMPTS or p not in FALLBACK_POOL:
        return p
    feedback = "; ".join(f"{o} -> {rejection_reason(o, used)}" for o in v.fix_options) or "no usable suggestion"
    return next_prompt(suggest(feedback), attempt, used)


def apply_changes(scenes_path: str, changes: dict[int, str]) -> None:
    """changes: {sehne nomresi (1-esasli): yeni prompt}. Fayl tezeden oxunur - basqa saheler qorunur."""
    with open(scenes_path, encoding="utf-8") as f:
        data = json.load(f)
    for n, prompt in changes.items():
        data["scenes"][n - 1]["bg_prompt"] = prompt
    with open(scenes_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def apply_visuals(scenes_path: str, specs: dict[int, dict]) -> None:
    """#67: {sehne nomresi: animasiya spec-i} - sehne fotodan animasiyaya kecir (fayl tezeden oxunur)."""
    with open(scenes_path, encoding="utf-8") as f:
        data = json.load(f)
    for n, spec in specs.items():
        data["scenes"][n - 1]["visual"] = spec
    with open(scenes_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def to_animate(nums: list[int], verdicts: dict, tries: dict[int, int]) -> list[int]:
    """#67: bir defe yeniden cekilib hele generik qalan foto - abstrakt mezmundur, foto onu literal gostermir."""
    return [n for n in nums if "generic" in verdicts[n].problems and tries.get(n, 0) >= 1]


def drop_animated(report: dict, animated: set[int]) -> dict:
    return {k: v for k, v in report.items() if int(k) not in animated}


def animate(ep: str, scenes_path: str, nums: list[int], provider: str) -> set[int]:
    with open(scenes_path, encoding="utf-8") as f:
        scenes = json.load(f)["scenes"]
    specs = animate_abstract(scenes, nums, episode_topic(ep), provider=provider)
    apply_visuals(scenes_path, specs)
    print(f"[qa] generik foto -> animasiya: {sorted(specs) or 'yoxdur'} (cehd: {nums})", flush=True)
    return set(specs)


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


def generic_share(report: dict) -> tuple[list[int], float]:
    """#60: generik/metafor say - hakim "generic" dedi ve ya ehtiyat hovuz fonu (terife gore generikdir)."""
    nums = sorted(int(n) for n, r in report.items()
                  if "generic" in (r.get("problems") or []) or r.get("prompt") in FALLBACK_POOL)
    return nums, (round(len(nums) / len(report), 3) if report else 0.0)


def judge_text(scene: dict, case: str = "") -> str:
    """Kicik saxlanilir: istifade olunmus obyektler siyahisi burada DEYIL (56 paralel sorgu gpt-4o TPM
    limitini asirdi, #32) - onu yalniz redd olunan sehneler ucun suggest_again alir."""
    # #65: case biznesi - onun real yerleri generik sayilmir, teklifler bu biznesden olur
    return f"{case}Narration: {scene.get('narration', '')}\nImage prompt used: {scene.get('bg_prompt', '')}"


def needs_redo(v: Verdict, prompt: str, tries: int) -> bool:
    """Ehtiyat hovuz fonu terife gore movzudan kenardir - yalniz "mismatch" ucun yeniden cekilmir
    (pricing E2E-2: 22 sehne 3 raund boyu hovuzdan hovuza kecib yene "mismatch" qalmisdi)."""
    if v.ok or tries >= MAX_ATTEMPTS:
        return False
    # hovuz fonu QA-da artiq secilibse (tries >= 1) yalniz "mismatch" ucun yeniden cekilmir; ilk defe
    # (plan / evvelki run-dan qalib) - choose_prompt ile movzuya uygun fona bir sans verilir
    return not (tries >= 1 and prompt in FALLBACK_POOL and set(v.problems) <= {"mismatch"})


def load_tries(ep: str, scenes: list[dict]) -> dict[int, int]:
    """Resume/retry: evvelki bg_qa.json-dan cehd sayi, prompt deyismeyibse (qebul olunmus fon yeniden cekilmir)."""
    try:
        with open(os.path.join(ep, REPORT), encoding="utf-8") as f:
            old = json.load(f).get("scenes", {})
    except (OSError, ValueError):
        return {}
    return {int(n): r["attempts"] for n, r in old.items()
            if r.get("attempts") and 0 < int(n) <= len(scenes)
            and scenes[int(n) - 1].get("bg_prompt") == r.get("prompt")}


def judge(path: str, scene: dict, provider: str, case: str = "") -> Verdict:
    text = judge_text(scene, case)
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
    code = subprocess.run(cmd).returncode
    if code == render_bgs.EXIT_NO_BALANCE:      # #64: pipeline NO_RETRY gorsun, bos retry olmasin
        raise SystemExit("OpenAI BALANSI BITIB - fonlar yeniden cekilmedi; kredit elave et, sonra: "
                         "python run.py --resume <slug>")
    if code:
        raise SystemExit(f"render_bgs ugursuz (exit {code})")


SAME_SYSTEM = """You compare two background images of one explainer video. The rule is: the same object or
the same scene must never appear twice. Answer "same": true if both images show the same kind of main
object (e.g. two piggy banks, two coin stacks, two stopwatches) or the same place/scene, even from another
angle or in another colour. Different objects that merely share a theme, surface, lighting or mood
(a stopwatch vs an hourglass vs a compass on a table) are NOT the same. First write "a" and "b": the main
object of each image in 2-5 words. Answer ONLY JSON with keys: a, b, same."""


def parse_same(d: dict) -> bool | None:
    """True/False yalniz aciq bool cavabdan; qalan hal (xeta, "yes") None - tekrar sayilir."""
    v = d.get("same")
    return v if isinstance(v, bool) else None


def same_scene(ep: str, a: int, b: int, provider: str) -> bool | None:
    parts = [_image_part(os.path.join(ep, "bg", f"sc{n:02d}.png")) for n in (a, b)]
    try:
        return parse_same(chat_json(SAME_SYSTEM, [{"type": "text", "text": "Image A, then image B."}, *parts],
                                    provider=provider, model=JUDGE_MODEL if provider == "openai" else None,
                                    temperature=0.0, max_tokens=80))
    except LLMError as e:
        print(f"  hakim xetasi (sc{a:02d}/sc{b:02d}): {str(e)[:120]}")
        return None


def confirm_duplicates(pairs: list[list[int]], same_fn) -> dict:
    """CLIP namized cutlerinden hakimin "eyni" dediklerini (ve ya cavab vermediklerini) saxlayir.
    Reyestr #31: realist fotoda ferqli obyektler (saniyeolcen/kompas) CLIP-de eyni sikkeden yuksek cixdi."""
    confirmed = [[a, b] for a, b in pairs if same_fn(a, b) is not False]
    redo: set[int] = set()
    for a, b in confirmed:
        if a not in redo:
            redo.add(b)
    return {"pairs": confirmed, "redo": sorted(redo)}


def find_duplicates(ep: str, provider: str = DEFAULT_PROVIDER) -> dict:
    """Eyni obyekt/sehne: CLIP namizedleri (bg_dedupe.py, MusicGen venv) + vision hakimi tesdiqi.
    Qaytarir {"pairs": [[a, b], ...], "redo": [b, ...]}."""
    out = subprocess.run([MUSIC_PY, os.path.join(HERE, "bg_dedupe.py"), ep], check=True,
                         capture_output=True, text=True).stdout
    pairs = json.loads(out.strip().splitlines()[-1])["pairs"]
    res = confirm_duplicates(pairs, lambda a, b: same_scene(ep, a, b, provider))
    if len(res["pairs"]) < len(pairs):
        print(f"[qa] CLIP {len(pairs)} cut, hakim {len(res['pairs'])} tesdiqledi: {res['pairs']}", flush=True)
    return res


def photo_scene_numbers(scenes: list[dict]) -> list[int]:
    """#45: analitik animasiya sehnelerinin fonu yoxdur - hakim yalniz foto sehnelerine baxir."""
    return [n for n, s in enumerate(scenes, 1) if not s.get("visual")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--provider", default=DEFAULT_PROVIDER)
    ap.add_argument("--force", action="store_true", help="pipeline uygunlugu ucun; skript her defe butun fonlari yoxlayir")
    a = ap.parse_args()
    ep = os.path.abspath(a.episode_dir)
    scenes_path = os.path.join(ep, "scenes.json")
    case = case_note(episode_plan(ep))

    report: dict[str, dict] = {}
    with open(scenes_path, encoding="utf-8") as f:
        first = json.load(f)["scenes"]
    pending = photo_scene_numbers(first)
    tries: dict[int, int] = load_tries(ep, first)
    clean = False               # hakim + tekrar yoxlamasi temiz bitdi
    for rnd in range(1, MAX_ATTEMPTS + DEDUPE_ROUNDS + 1):
        with open(scenes_path, encoding="utf-8") as f:
            scenes = json.load(f)["scenes"]
        paths = {n: os.path.join(ep, "bg", f"sc{n:02d}.png") for n in pending}
        verdicts = judge_all(pending, lambda n: judge(paths[n], scenes[n - 1], a.provider, case))
        # MAX_ATTEMPTS defe yeniden cekilib hele pisdirse sonuncu (ehtiyat) fon qalir - pipeline ilismir
        bad = [n for n in pending if needs_redo(verdicts[n], scenes[n - 1]["bg_prompt"], tries.get(n, 0))]
        for n in pending:
            v = verdicts[n]
            report[str(n)] = {"ok": v.ok, "problems": list(v.problems), "attempts": tries.get(n, 0)
                              + (0 if v.ok else 1), "prompt": scenes[n - 1]["bg_prompt"]}
        print(f"[qa] raund {rnd}: {len(pending)} yoxlandi, {len(bad)} pis: "
              + ", ".join(f"sc{n:02d}({'/'.join(verdicts[n].problems)})" for n in bad), flush=True)
        if to_animate(bad, verdicts, tries):
            done = animate(ep, scenes_path, to_animate(bad, verdicts, tries), a.provider)
            report = drop_animated(report, done)
            bad = [n for n in bad if n not in done]
        # hakim temiz olanda tekrar kadr yoxlamasi: eyni gorunen fonlarin sonrakilari yeniden cekilir
        dups = [] if bad else find_duplicates(ep, a.provider)["redo"]
        if dups:
            print(f"[qa] tekrar kadr: {len(dups)} sehne yeniden cekilir {dups}", flush=True)
        redo = bad or dups
        if not redo:
            clean = True
            break
        used = {s["bg_prompt"] for s in scenes}
        changes = {}
        for n in redo:
            tries[n] = tries.get(n, 0) + 1
            if n in bad:        # oz pis promptunun obyekti basqa sehnede yoxdursa, teklifde qala biler
                others = used - {scenes[n - 1]["bg_prompt"]}
                p = choose_prompt(verdicts[n], tries[n], others,
                                  lambda fb, s=scenes[n - 1], o=others: suggest_again(s, fb, o, a.provider, case))
            else:               # tekrar kadr: epizodda olmayan ehtiyat obyekt
                p = next_prompt("", MAX_ATTEMPTS, used)
            used.add(p)
            changes[n] = p
            print(f"  sc{n:02d} -> {p}", flush=True)
        apply_changes(scenes_path, changes)
        rerender(ep, redo)
        pending = redo

    generic, _ = generic_share(report)      # #67: son cehdden sonra da generik (ve ya hovuz) - animasiya
    if generic:
        report = drop_animated(report, animate(ep, scenes_path, generic, a.provider))
    duplicates = [] if clean else find_duplicates(ep, a.provider)["pairs"]     # bos deyilse check_bgs merhelesi kecmir
    with open(os.path.join(ep, REPORT), "w", encoding="utf-8") as f:
        generic, share = generic_share(report)
        json.dump({"passed": not duplicates and share <= GENERIC_MAX, "scenes": report, "duplicates": duplicates,
                   "generic": generic, "generic_share": share}, f, indent=2, ensure_ascii=False)
    redone = sorted(int(n) for n, r in report.items() if r["attempts"])
    print(f"[qa] bitdi: {len(redone)} fon yeniden cekildi {redone or ''}; generik {generic} ({share:.0%})")


if __name__ == "__main__":
    main()
