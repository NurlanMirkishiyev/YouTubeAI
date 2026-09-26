"""FAZA F orchestrator: movzu -> hazir video + youtube\\ paketi.
Istifade (koku qovluqdan):
  python run.py "Movzu" [--words 1230] [--music Music\\x.mp3]
  python run.py --resume <slug> [--from build_episode]
Her merhele oz venv-i ile subprocess kimi isleyir; log: Episodes\\<slug>\\logs\\<merhele>.log.
Merhele "bitib" = fayl sistemi + yoxlama; state.json yalniz jurnaldir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import duration  # noqa: E402
from comfy import ComfyGuard  # noqa: E402
from script_gen import (EFFECTIVE_WPM, EPISODES, slugify, word_count, words_for_seconds,  # noqa: E402
                        words_to_add, words_to_cut)
from stages import PROJ, PY, ROOT, STAGES, Ctx, stage_index  # noqa: E402
from state import new_state, now_iso, read_state, with_stage, write_state  # noqa: E402

# Istifadeci (2026-09-26): video 8-10 deq, 10 deq-den uzun olmamalidir. LLM hedefi ~10% asir ->
# 1230 istenen ~1350 soz ~ 9 deq video (EFFECTIVE_WPM ile)
DEFAULT_WORDS = 1230
MIN_SECONDS = 480.0
MAX_SECONDS = 600.0
MAX_EXTENSIONS = 2
MUSIC_DIR = os.path.join(ROOT, "Music")   # --music verilmeyende trek buradan secilir
DELIVERY_DIR = os.path.join(ROOT, "Hazir_Videolar")   # butun hazir videolar bir yerde (istifadeci 2026-09-27)
INVALIDATE_DIRS = ("bg", "bg_hd", "owl", "audio", "cards", "remotion", "youtube")
INVALIDATE_FILES = ("scenes.json", "narration.wav", "narration.srt", "narration.words.json",
                    "narration.shifted.srt", "bg_qa.json", "owl_qa.json")


@dataclass(frozen=True)
class Gate:
    status: str            # "ok" | "fail" | "restart"
    message: str = ""
    restart_at: str = ""


def _logged_call(cmd: list[str], log: str) -> int:
    with open(log, "a", encoding="utf-8") as lf:
        lf.write(f"\n[{now_iso()}] $ {' '.join(cmd)}\n")
        lf.flush()
        return subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT)


def run_stage(stage, ctx: Ctx, force: bool, log_dir: str) -> list[str]:
    log = os.path.join(log_dir, f"{stage.name}.log")
    rc = _logged_call(stage.command(ctx, force), log)
    return [f"exit {rc}: {_last_line(log)} - bax: {log}"] if rc else stage.verify(ctx)


def _last_line(log: str) -> str:
    """Xetanin sebebi istifadeciye gorunsun (evvel yalniz "exit 1 - bax: log" yazilirdi)."""
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return ""
    return lines[-1][:200] if lines else ""


def extend_script(ctx: Ctx, words: int, log_dir: str) -> list[str]:
    log = os.path.join(log_dir, "script_extend.log")
    cmd = [PY["projects"], os.path.join(PROJ, "script_gen.py"), ctx.topic, "--slug", ctx.slug,
           "--extend", str(words), "--provider", ctx.provider]
    rc = _logged_call(cmd, log)
    return [f"skript uzadilmadi (exit {rc}) - bax: {log}"] if rc else []


def invalidate_after_script(ep_dir: str, slug: str) -> None:
    """Skript deyisdi -> sehne nomreleri surusur; skriptden sonraki her sey silinir."""
    for d in INVALIDATE_DIRS:
        shutil.rmtree(os.path.join(ep_dir, d), ignore_errors=True)
    for f in (*INVALIDATE_FILES, f"{slug}.mp4"):
        p = os.path.join(ep_dir, f)
        if os.path.isfile(p):
            os.remove(p)


def shorten_script(ctx: Ctx, words: int, log_dir: str) -> list[str]:
    log = os.path.join(log_dir, "script_shorten.log")
    cmd = [PY["projects"], os.path.join(PROJ, "script_gen.py"), ctx.topic, "--slug", ctx.slug,
           "--shorten", str(words), "--provider", ctx.provider]
    rc = _logged_call(cmd, log)
    return [f"skript qisaldilmadi (exit {rc}) - bax: {log}"] if rc else []


def word_gate(ctx: Ctx, log_dir: str, attempt: int) -> Gate:
    """Skriptin tehmini video uzunlugu [min, max] araligina salinir (uzat / qisalt)."""
    n = 0
    for k in range(MAX_EXTENSIONS + 1):
        with open(ctx.p("script.md"), encoding="utf-8") as f:
            n = word_count(f.read())
        add, cut = words_to_add(n, ctx.min_seconds), words_to_cut(n, ctx.max_seconds)
        if not add and not cut:
            return Gate("ok", f"skript {n} soz ~{n / EFFECTIVE_WPM:.1f} deq")
        if k == MAX_EXTENSIONS:
            break
        if add:
            print(f"  skript {n} soz - {ctx.min_seconds:.0f} s ucun +{add} soz elave olunur", flush=True)
            problems = extend_script(ctx, add, log_dir)
        else:
            print(f"  skript {n} soz - {ctx.max_seconds:.0f} s-e sigmaq ucun -{cut} soz", flush=True)
            problems = shorten_script(ctx, cut, log_dir)
        if problems:
            return Gate("fail", problems[0])
    return Gate("fail", f"skript {n} soz - {MAX_EXTENSIONS} cehdden sonra da "
                        f"{ctx.min_seconds:.0f}-{ctx.max_seconds:.0f} s araligina dusmur")


def length_gate(ctx: Ctx, log_dir: str, attempt: int) -> Gate:
    """Real TTS uzunlugu yoxlanir; araliqdan kenardirsa skript duzelir ve scene_plan-dan tekrar."""
    secs = duration(ctx.p("narration.wav"))
    if ctx.min_seconds <= secs <= ctx.max_seconds:
        return Gate("ok", f"narration {secs:.0f} s")
    if attempt >= MAX_EXTENSIONS:
        return Gate("fail", f"narration {secs:.0f} s {ctx.min_seconds:.0f}-{ctx.max_seconds:.0f} s "
                            f"araliginda deyil, {MAX_EXTENSIONS} cehd bitdi")
    if secs < ctx.min_seconds:
        problems, what = extend_script(ctx, words_for_seconds(ctx.min_seconds - secs), log_dir), "uzadildi"
    else:
        cut = math.ceil((secs - ctx.max_seconds * 0.95) / 60.0 * EFFECTIVE_WPM)
        problems, what = shorten_script(ctx, cut, log_dir), "qisaldildi"
    if problems:
        return Gate("fail", problems[0])
    invalidate_after_script(ctx.ep_dir, ctx.slug)
    return Gate("restart", f"narration {secs:.0f} s - skript {what}, scene_plan-dan tekrar", "scene_plan")


DEFAULT_GATES = {"script_gen": word_gate, "tts_gen": length_gate}


def _save(path: str, state: dict, stage: str, **fields) -> dict:
    new = with_stage(state, stage, **fields)
    write_state(path, new)
    return new


def _step(stage, ctx, force, log_dir, runner, comfy, remaining) -> list[str]:
    if comfy is not None:
        err = comfy.before(remaining)
        if err:
            return [err]
    return runner(stage, ctx, force, log_dir)


STAGE_RETRIES = 2          # muveqqeti xeta (sebeke, ComfyUI/Remotion cokmesi) - merhele yeniden cehd edilir
RETRY_WAIT_S = 30
NO_RETRY = "BALANSI BITIB"   # llm.py-in balans xetasi mesaji


def _step_with_retries(stage, ctx, force, log_dir, runner, comfy, remaining, sleep) -> list[str]:
    """Skriptler qaldigi yerden davam edir (hazir fayllari kecir) - tekrar cehd ucuzdur."""
    problems = _step(stage, ctx, force, log_dir, runner, comfy, remaining)
    for k in range(STAGE_RETRIES):
        if not problems or any(NO_RETRY in p for p in problems):     # balans bitibse tekrar hec ne vermir
            break
        print(f"  {stage.name} ugursuz ({'; '.join(problems)[:200]}) - {RETRY_WAIT_S}s sonra "
              f"tekrar cehd {k + 1}/{STAGE_RETRIES}", flush=True)
        sleep(RETRY_WAIT_S)
        problems = _step(stage, ctx, force, log_dir, runner, comfy, remaining)
    return problems


def run_pipeline(ctx: Ctx, state_path: str, stages=STAGES, from_idx: int | None = None,
                 runner=run_stage, gates=None, comfy=None, sleep=time.sleep) -> int:
    gates = DEFAULT_GATES if gates is None else gates
    log_dir = ctx.p("logs")
    os.makedirs(log_dir, exist_ok=True)
    state = read_state(state_path) or new_state(ctx.topic, ctx.slug, [s.name for s in stages])
    forced = set(range(from_idx, len(stages))) if from_idx is not None else set()
    attempts: dict[str, int] = {}
    i = 0
    try:
        while i < len(stages):
            st, force = stages[i], i in forced
            forced.discard(i)
            if not force and st.done(ctx) and not st.verify(ctx):
                print(f"[{i + 1}/{len(stages)}] {st.name}: hazirdir - kecilir", flush=True)
                problems = []
            else:
                print(f"[{i + 1}/{len(stages)}] {st.name} ... ({now_iso()})", flush=True)
                state = _save(state_path, state, st.name, status="running", started=now_iso(), error=None)
                problems = _step_with_retries(st, ctx, force, log_dir, runner, comfy, list(stages[i:]), sleep)
            gate = Gate("ok")
            if not problems and st.name in gates:
                gate = gates[st.name](ctx, log_dir, attempts.get(st.name, 0))
                attempts[st.name] = attempts.get(st.name, 0) + 1
                problems = [gate.message] if gate.status == "fail" else []
            if problems:
                _save(state_path, state, st.name, status="failed", finished=now_iso(), error="; ".join(problems))
                print(f"  XETA ({st.name}): " + "; ".join(problems), flush=True)
                return 1
            state = _save(state_path, state, st.name, status="done", finished=now_iso())
            if gate.message:
                print("  " + gate.message, flush=True)
            i = [s.name for s in stages].index(gate.restart_at) if gate.status == "restart" else i + 1
    finally:
        if comfy is not None:
            comfy.stop()
    return 0


def default_music(slug: str, music_dir: str) -> str | None:
    """Music/*.mp3-den epizoda gore trek: eyni slug hemise eyni trek (resume), ferqli epizodlar
    novbelesir. Hash sabitdir (Python hash() her prosesde ferqli olur)."""
    if not os.path.isdir(music_dir):
        return None
    tracks = sorted(n for n in os.listdir(music_dir) if n.lower().endswith(".mp3"))
    if not tracks:
        return None
    k = int.from_bytes(hashlib.sha1(slug.encode("utf-8")).digest()[:4], "big") % len(tracks)
    return os.path.join(music_dir, tracks[k])


DELIVER_OPTIONAL = (("narration.srt", "subtitles.srt"), ("script.md", "script.md"))


def deliver(ep_dir: str, slug: str, out_dir: str) -> str:
    """Her movzunun oz qovlugu out_dir/<slug>/ (istifadeci 2026-09-27: movzular qarismasin):
    <slug>.mp4 (eyni diskde hardlink - yer tutmur), thumbnail.png, youtube.txt (basliq + description +
    tags), subtitles.srt ve script.md (varsa). Kohne nusxe evez olunur."""
    topic = os.path.join(out_dir, slug)
    os.makedirs(topic, exist_ok=True)
    ydir = os.path.join(ep_dir, "youtube")
    video = os.path.join(topic, f"{slug}.mp4")
    if os.path.exists(video):
        os.remove(video)
    try:
        os.link(os.path.join(ep_dir, f"{slug}.mp4"), video)
    except OSError:
        shutil.copy2(os.path.join(ep_dir, f"{slug}.mp4"), video)
    shutil.copy2(os.path.join(ydir, "thumbnail.png"), os.path.join(topic, "thumbnail.png"))
    for src, dst in DELIVER_OPTIONAL:
        if os.path.isfile(os.path.join(ep_dir, src)):
            shutil.copy2(os.path.join(ep_dir, src), os.path.join(topic, dst))
    parts = []
    for label, name in (("TITLE", "title.txt"), ("DESCRIPTION", "description.txt"), ("TAGS", "tags.txt")):
        with open(os.path.join(ydir, name), encoding="utf-8") as f:
            parts.append(f"=== {label} ===\n{f.read().strip()}\n")
    with open(os.path.join(topic, "youtube.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return topic


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="FAZA F: movzu -> YouTube-a hazir video")
    ap.add_argument("topic", nargs="?")
    ap.add_argument("--slug")
    ap.add_argument("--words", type=int, default=DEFAULT_WORDS)
    ap.add_argument("--music", help="royalty-free fon musiqisi")
    ap.add_argument("--resume", metavar="SLUG")
    ap.add_argument("--from", dest="from_stage", choices=[s.name for s in STAGES])
    ap.add_argument("--min-seconds", type=float, default=MIN_SECONDS, help="video minimum uzunlugu (s)")
    ap.add_argument("--max-seconds", type=float, default=MAX_SECONDS, help="video maksimum uzunlugu (s)")
    ap.add_argument("--provider", default="openai")
    a = ap.parse_args(argv)
    if not a.topic and not a.resume:
        ap.error("movzu ve ya --resume <slug> lazimdir")
    return a


def make_ctx(a: argparse.Namespace) -> Ctx:
    slug = a.resume or a.slug or slugify(a.topic)
    ep = os.path.join(EPISODES, slug)
    topic = a.topic or (read_state(os.path.join(ep, "state.json")) or {}).get("topic")
    meta_path = os.path.join(ep, "meta.json")
    if not topic and os.path.isfile(meta_path):     # FAZA F-den evvelki epizodlarda state.json yoxdur
        with open(meta_path, encoding="utf-8") as f:
            topic = json.load(f).get("topic")
    if not topic:
        raise SystemExit(f"movzu tapilmadi: {ep} (state.json / meta.json) - movzunu da ver")
    if a.music and not os.path.isfile(a.music):
        raise SystemExit("musiqi tapilmadi: " + a.music)
    music = os.path.abspath(a.music) if a.music else default_music(slug, MUSIC_DIR)
    return Ctx(topic, slug, ep, a.words, music, a.min_seconds, a.max_seconds, a.provider)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    ctx = make_ctx(a)
    os.makedirs(ctx.p("logs"), exist_ok=True)
    print(f"FAZA F: {ctx.topic!r} -> {ctx.ep_dir}", flush=True)
    if ctx.music:
        print(f"  musiqi: {ctx.music}", flush=True)
    else:
        print("  DIQQET: Music qovlugunda mp3 yoxdur - video musiqisiz olacaq", flush=True)
    guard = ComfyGuard(ctx.p("logs", "comfyui.log"))
    rc = run_pipeline(ctx, ctx.p("state.json"),
                      from_idx=stage_index(a.from_stage) if a.from_stage else None, comfy=guard)
    if rc == 0:
        mp4 = ctx.p(f"{ctx.slug}.mp4")
        folder = deliver(ctx.ep_dir, ctx.slug, DELIVERY_DIR)
        print(f"\nHAZIRDIR ({duration(mp4) / 60:.2f} deq): {folder}\n"
              f"  {ctx.slug}.mp4 + thumbnail.png + youtube.txt + subtitles.srt + script.md")
    return rc
