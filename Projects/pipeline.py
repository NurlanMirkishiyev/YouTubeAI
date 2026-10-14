"""Merheleler ardicil; her merhele fayl yazir, fayl varsa kecilir (resume). Xeta -> 1 tekrar, sonra DAYANDI + --resume.
Foto / bayqus / musiqi / thumbnail hec vaxt evez olunmur (fallback YOX); OpenAI balansi bitende derhal dayanir."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Callable

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import captions  # noqa: E402
import generate  # noqa: E402
import images  # noqa: E402
import llm  # noqa: E402
import mix  # noqa: E402
import owl  # noqa: E402
import plan  # noqa: E402
import publish  # noqa: E402
import render  # noqa: E402
import script  # noqa: E402

TTS_PY = os.path.join(ROOT, "TTS", ".venv", "Scripts", "python.exe")
MUSIC_PY = os.path.join(ROOT, "MusicGen", ".venv", "Scripts", "python.exe")
USAGE = 'python run.py "<ssenari faylı>"  |  python run.py --resume <slug>'


@dataclass(frozen=True)
class Stage:
    name: str
    done: Callable[[str], bool]
    run: Callable[[str], None]


def _f(*parts: str) -> Callable[[str], bool]:
    return lambda ep: os.path.isfile(os.path.join(ep, *parts))


def _scenes(ep: str) -> dict:
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        return json.load(f)


def _all(sub: str, ext: str, photo_only: bool = False) -> Callable[[str], bool]:
    def done(ep: str) -> bool:
        if not os.path.isfile(os.path.join(ep, "scenes.json")):
            return False
        return all(os.path.isfile(os.path.join(ep, sub, f"sc{s['n']:02d}.{ext}")) for s in _scenes(ep)["scenes"]
                   if not photo_only or s["type"] in images.PHOTO_TYPES)
    return done


def _planned(ep: str) -> bool:
    return os.path.isfile(os.path.join(ep, "scenes.json")) and all(s["type"] for s in _scenes(ep)["scenes"])


VOICE_TIMEOUT_S, MUSIC_TIMEOUT_S = 3 * 3600, 5 * 3600     # ilisme qorumasi (adi: ~5 deq / ~10 deq)


def _voice(ep: str) -> None:
    generate.run_cmd([TTS_PY, os.path.join(HERE, "voice.py"), ep], timeout=VOICE_TIMEOUT_S)


def _music(ep: str) -> None:
    generate.run_cmd([MUSIC_PY, os.path.join(HERE, "music.py"), ep], timeout=MUSIC_TIMEOUT_S)


def _voiced(ep: str) -> bool:
    return (os.path.isfile(os.path.join(ep, "narration.wav")) and os.path.isfile(os.path.join(ep, "scenes.json"))
            and all((s.get("duration") or 0) > 0 for s in _scenes(ep)["scenes"]))


def _slug_mp4(ep: str) -> bool:
    return os.path.isfile(os.path.join(ep, "scenes.json")) and os.path.isfile(os.path.join(ep, f"{_scenes(ep)['slug']}.mp4"))




STAGES = [
    Stage("script", _f("scenes.json"), lambda ep: None),          # start() yazir
    Stage("plan", _planned, plan.main),
    Stage("images", _all("img", "png", photo_only=True), images.render_photos),
    Stage("owl", _all("owl", "png"), owl.render_owls),
    Stage("voice", _voiced, _voice),
    Stage("captions", _f("captions.json"), captions.main),
    Stage("music", _f("music.wav"), _music),
    Stage("render", _f("video_raw.mp4"), render.main),
    Stage("mix", _slug_mp4, mix.main),
    Stage("publish", _f("published"), publish.main),
]


_published = _f("published")


STAGE_ATTEMPTS = 5
RETRY_WAITS_S = (30, 120, 300, 600)          # kecici xeta (sebeke, GPU, render) - artan gozleme
BALANCE_WAIT_S, BALANCE_TRIES = 600, 36      # balans bitende her 10 deq yoxlanir, 6 saata qeder


def _run_stage(ep: str, st: Stage, log, sleep, resume: str) -> None:
    """Merhele fayllari resume-dur: tekrar cehd yalniz catismayan hisseni edir (pul tekrar xerclenmir)."""
    failures = balance = 0
    while True:
        try:
            st.run(ep)
            return
        except Exception as e:  # noqa: BLE001
            if llm.is_balance_error(e):
                balance += 1
                if balance > BALANCE_TRIES:
                    log(f"DAYANDI: OpenAI balansi {BALANCE_TRIES * BALANCE_WAIT_S // 3600} saatdir bosdur ({st.name}). "
                        f"Balansi doldurub davam: {resume}")
                    raise SystemExit(1)
                log(f"XEBERDARLIQ: OpenAI balansi bitib ({st.name}) - balansi artirin; pipeline her "
                    f"{BALANCE_WAIT_S // 60} deq yoxlayir ve ozu davam edir ({balance}/{BALANCE_TRIES})")
                sleep(BALANCE_WAIT_S)
                continue
            failures += 1
            log(f"  {st.name} xetasi (cehd {failures}/{STAGE_ATTEMPTS}): {str(e)[:300]}")
            if failures >= STAGE_ATTEMPTS:
                log(f"DAYANDI: {st.name}. Davam: {resume}")
                raise SystemExit(1)
            wait = RETRY_WAITS_S[min(failures - 1, len(RETRY_WAITS_S) - 1)]
            log(f"  {st.name}: {wait} s sonra yeniden (hazir hisseler saxlanilir)")
            sleep(wait)


def keep_awake(on: bool) -> None:
    """Uzun run zamani Windows yuxuya getmesin (proses olmesin). Basqa OS-de hec ne etmir."""
    if os.name != "nt":
        return
    import ctypes
    es_continuous, es_system_required = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(es_continuous | (es_system_required if on else 0))


def run_stages(ep: str, stages=STAGES, log=print, sleep=time.sleep) -> None:
    resume = f"python run.py --resume {os.path.basename(ep)}"
    for i, st in enumerate(stages, 1):
        if st.done(ep):
            log(f"[{i}/{len(stages)}] {st.name}: hazirdir - kecilir")
            continue
        log(f"[{i}/{len(stages)}] {st.name} ... ({time.strftime('%H:%M:%S')})")
        _run_stage(ep, st, log, sleep, resume)


def find_script(name: str) -> str:
    if os.path.isfile(name):
        return os.path.abspath(name)
    base = os.path.join(ROOT, "Ssenariler", os.path.basename(name))
    for p in (base, base + ".md"):
        if os.path.isfile(p):
            return p
    raise SystemExit(f"ssenari tapilmadi: {name}")


DERIVED_DIRS = ("img", "owl", "voice", "music_parts", "public")
DERIVED_FILES = ("scenes.json", "narration.wav", "captions.json", "music.wav", "music.skip", "props.json",
                 "video_raw.mp4", "thumbnail.png", "youtube.txt", "published")


def _texts(data: dict) -> list[tuple]:
    """Yalniz ssenari sehneleri (intro/outro GPT metnidir, ssenari deyisikliyi sayilmir)."""
    return [(s.get("section"), s.get("text")) for s in data["scenes"] if s.get("type") not in ("intro", "outro")]


def _reset_episode(ep: str, slug: str) -> None:
    """Derived artifacts are deleted; run.log is kept."""
    for d in DERIVED_DIRS:
        shutil.rmtree(os.path.join(ep, d), ignore_errors=True)
    names = set(DERIVED_FILES) | {f"{slug}.mp4"}
    for fn in os.listdir(ep):
        if fn in names or fn.endswith(".srt") or ".tmp." in fn:
            path = os.path.join(ep, fn)
            if os.path.isfile(path):
                os.remove(path)


def start(script_path: str, log=print) -> str:
    data = script.build(find_script(script_path))
    for n, sent in script.suspicious(data["scenes"]):    # yalniz xeberdarliq - ssenari video dayandirmir
        log(f"XEBERDARLIQ sc{n:02d}: rejissor qeydine oxsayir, danisiq kimi oxunacaq: {sent[:120]}")
    ep = os.path.join(ROOT, "Episodes", data["slug"])
    os.makedirs(ep, exist_ok=True)
    sc_path = os.path.join(ep, "scenes.json")
    if os.path.isfile(sc_path):
        try:
            reason = "ssenari deyisib" if _texts(_scenes(ep)) != _texts(data) else ""
        except (ValueError, KeyError, TypeError, AttributeError):
            reason = "scenes.json zedelidir"
        if reason:
            log(f"{reason} - kohne epizod fayllari silinir")
            _reset_episode(ep, data["slug"])
    if not os.path.isfile(sc_path):
        generate.atomic_json(sc_path, data)
    return ep


def main(argv: list[str]) -> None:
    if not argv or (argv[0] == "--resume" and len(argv) < 2):
        print(f"Istifade: {USAGE}")
        raise SystemExit(2)
    if argv[0] == "--resume":
        slug = os.path.basename(argv[1].replace("\\", "/").rstrip("/"))
        ep = os.path.join(ROOT, "Episodes", slug)
        if slug in ("", ".", "..") or not os.path.isfile(os.path.join(ep, "scenes.json")):
            print(f"epizod tapilmadi: {argv[1]}")
            raise SystemExit(2)
    else:
        ep = start(argv[0])
    log_path = os.path.join(ep, "run.log")

    def log(msg: str) -> None:
        print(msg, flush=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    log(f"=== {os.path.basename(ep)} ===")
    keep_awake(True)
    try:
        run_stages(ep, STAGES, log)
    finally:
        keep_awake(False)
    log("BITDI")
