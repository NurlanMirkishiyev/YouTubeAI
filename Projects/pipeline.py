"""FAZA F orchestrator: movzu -> hazir video + youtube\\ paketi.
Istifade (koku qovluqdan):
  python run.py "Movzu" [--words 2150] [--music Music\\x.mp3]
  python run.py --resume <slug> [--from build_episode]
Her merhele oz venv-i ile subprocess kimi isleyir; log: Episodes\\<slug>\\logs\\<merhele>.log.
Merhele "bitib" = fayl sistemi + yoxlama; state.json yalniz jurnaldir.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import duration  # noqa: E402
from comfy import ComfyGuard  # noqa: E402
from script_gen import EPISODES, slugify, word_count, words_for_seconds, words_to_add  # noqa: E402
from stages import PROJ, PY, ROOT, STAGES, Ctx, stage_index  # noqa: E402
from state import new_state, now_iso, read_state, with_stage, write_state  # noqa: E402

DEFAULT_WORDS = 2150
MIN_SECONDS = 600.0
MAX_EXTENSIONS = 2
INVALIDATE_DIRS = ("bg", "bg_hd", "audio", "cards", "remotion", "youtube")
INVALIDATE_FILES = ("scenes.json", "narration.wav", "narration.srt", "narration.words.json",
                    "narration.shifted.srt")


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
    return [f"exit {rc} - bax: {log}"] if rc else stage.verify(ctx)


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


def word_gate(ctx: Ctx, log_dir: str, attempt: int) -> Gate:
    n = 0
    for k in range(MAX_EXTENSIONS + 1):
        with open(ctx.p("script.md"), encoding="utf-8") as f:
            n = word_count(f.read())
        need = words_to_add(n, ctx.min_seconds)
        if need == 0:
            return Gate("ok", f"skript {n} soz")
        if k == MAX_EXTENSIONS:
            break
        print(f"  skript {n} soz - {ctx.min_seconds:.0f} s ucun +{need} soz elave olunur", flush=True)
        problems = extend_script(ctx, need, log_dir)
        if problems:
            return Gate("fail", problems[0])
    return Gate("fail", f"skript {n} soz - {MAX_EXTENSIONS} uzatmadan sonra da {ctx.min_seconds:.0f} s-e catmir")


def length_gate(ctx: Ctx, log_dir: str, attempt: int) -> Gate:
    secs = duration(ctx.p("narration.wav"))
    if secs >= ctx.min_seconds:
        return Gate("ok", f"narration {secs:.0f} s")
    if attempt >= MAX_EXTENSIONS:
        return Gate("fail", f"narration {secs:.0f} s < {ctx.min_seconds:.0f} s, {MAX_EXTENSIONS} cehd bitdi")
    problems = extend_script(ctx, words_for_seconds(ctx.min_seconds - secs), log_dir)
    if problems:
        return Gate("fail", problems[0])
    invalidate_after_script(ctx.ep_dir, ctx.slug)
    return Gate("restart", f"narration {secs:.0f} s qisadir - skript uzadildi, scene_plan-dan tekrar", "scene_plan")


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


def run_pipeline(ctx: Ctx, state_path: str, stages=STAGES, from_idx: int | None = None,
                 runner=run_stage, gates=None, comfy=None) -> int:
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
                problems = _step(st, ctx, force, log_dir, runner, comfy, list(stages[i:]))
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="FAZA F: movzu -> YouTube-a hazir video")
    ap.add_argument("topic", nargs="?")
    ap.add_argument("--slug")
    ap.add_argument("--words", type=int, default=DEFAULT_WORDS)
    ap.add_argument("--music", help="royalty-free fon musiqisi")
    ap.add_argument("--resume", metavar="SLUG")
    ap.add_argument("--from", dest="from_stage", choices=[s.name for s in STAGES])
    ap.add_argument("--min-seconds", type=float, default=MIN_SECONDS, help="yalniz test ucun asagi sal")
    ap.add_argument("--provider", default="openai")
    ap.add_argument("--motion", choices=["kenburns"], default="kenburns", help="Faza 2: ltx")
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
    return Ctx(topic, slug, ep, a.words, a.music and os.path.abspath(a.music), a.min_seconds, a.provider)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    ctx = make_ctx(a)
    os.makedirs(ctx.p("logs"), exist_ok=True)
    print(f"FAZA F: {ctx.topic!r} -> {ctx.ep_dir}", flush=True)
    if not ctx.music:
        print("  DIQQET: --music verilmeyib - video musiqisiz olacaq", flush=True)
    guard = ComfyGuard(ctx.p("logs", "comfyui.log"))
    rc = run_pipeline(ctx, ctx.p("state.json"),
                      from_idx=stage_index(a.from_stage) if a.from_stage else None, comfy=guard)
    if rc == 0:
        mp4 = ctx.p(f"{ctx.slug}.mp4")
        print(f"\nHAZIRDIR: {mp4}  ({duration(mp4) / 60:.2f} deq)\n  YouTube paketi: {ctx.p('youtube')}")
    return rc
