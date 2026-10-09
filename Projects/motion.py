"""Faza 3.2-3.6 (istifadeci 2026-10-07): deterministik muxtəliflik - her epizodun hereket plani.
- seed = slug sha256 (data_visuals.seed_of); eyni slug -> eyni plan, ferqli -> ferqli;
- her epizoda bir motion theme (clean / dynamic / editorial); editorial-da yungul film gorunusu (Remotion);
- her animasiya novunun ve Title/Kicker/lower-third/cold open-un >= 3 giris varianti (typewriter daxil;
  cold open hemise typewriter - danisiqla eyni vaxtda, sehne muddetini deyismir);
- kecidler: bolme kecidi ve adi kecid ucun ayri destler (@remotion/transitions 4.0.529-un DOM presentation-lari),
  eyni kecid ardicil 2 defe olmur; Ken Burns sabit suretle, hereket novleri artirilib;
- Episodes/_motion_history.json: son 3 epizodla variant ardicilliginin oxsarligi > 50%-dirse theme deyisir.
Secim Python-dadir (test olunur, tarixce ucun lazimdir) - Remotion yalniz plani oynadir.
"""
from __future__ import annotations

import json
import math
import os
import random

from data_visuals import seed_of

THEMES = ("clean", "dynamic", "editorial")
BACKDROPS = ("studio", "aurora", "blueprint", "spotlight")
VARIANTS: dict[str, tuple[str, ...]] = {
    "stats": ("rise", "scale_pop", "mask_reveal", "digit_roll"),
    "counter": ("rise", "scale_pop", "digit_roll"),
    "bars": ("stagger", "left_to_right", "center_out"),
    "line": ("draw_pulse", "draw_fill", "draw_markers"),
    "timeseries": ("draw_pulse", "draw_fill", "draw_markers"),
    "compare": ("face_off", "split", "flip"),
    "equation": ("term_by_term", "slide_terms", "pop_terms"),
    "table": ("row_stagger", "column_wipe", "fade_rows"),
    "threshold": ("axes_curve_point", "gauge_fill", "marker_drop"),
    "usmap": ("dot_wave", "region_sweep", "center_burst"),
    "ring": ("sweep", "pop_sweep", "count_first"),
    "flow": ("step_chain", "slide_steps", "pop_steps"),
    "timeline": ("draw_line", "pop_events", "slide_events"),
    "waterfall": ("stagger", "left_to_right", "pop_steps"),     # #135
    "gauge": ("sweep", "pop_sweep", "count_first"),
    "dotgrid": ("dot_wave", "center_burst", "region_sweep"),
    "balance": ("face_off", "split", "flip"),
    "funnel": ("stagger", "slide_steps", "pop_steps"),
    "versus": ("face_off", "scale_pop", "split"),
    "title": ("slide_up", "typewriter", "mask_reveal"),
    "kicker": ("fade_slide", "typewriter", "track_in"),
    "lower_third": ("slide_in", "wipe", "typewriter"),
    "cold_open": ("typewriter", "word_rise", "mask_reveal"),
}
KEN_BURNS = ("zoom_in", "zoom_out", "pan_lr", "pan_rl", "diag_tl_br", "diag_br_tl", "push_in", "tilt_up", "tilt_down")
# @remotion/transitions 4.0.529: fade, slide, wipe, flip, iris, clockWipe, pushCut (DOM; shader-li olanlar yox)
SECTION_TRANSITIONS = ("slide_right", "slide_bottom", "push_cut", "iris", "flip", "clock_wipe")
TRANSITIONS = ("fade", "wipe_left", "wipe_right", "wipe_top_left", "slide_left")
SIMILARITY_MAX = 0.5
HISTORY_WINDOW = 3
HISTORY_KEEP = 10
THEME_SHARE = 2 / 3      # theme her hovuzun firlanmis siyahisinin ilk 2/3-den secir


def _pool(options: tuple[str, ...], theme: str) -> tuple[str, ...]:
    """Theme hovuzu: siyahi theme indeksi qeder firlanir, ilk 2/3 qalir - ferqli theme ferqli uslub."""
    k = THEMES.index(theme) % len(options)
    rotated = options[k:] + options[:k]
    return rotated[:max(2, math.ceil(len(rotated) * THEME_SHARE))]


def _pick(rnd: random.Random, options: tuple[str, ...], avoid: str | None = None) -> str:
    choices = [o for o in options if o != avoid] or list(options)
    return rnd.choice(choices)


def plan_motion(slug: str, scenes: list[dict], theme: str | None = None, salt: int = 0) -> dict:
    """scenes: [{"kind": chart novu ve ya None (foto), "section_start": bool}] -> hereket plani."""
    rnd = random.Random(seed_of(slug) + salt)
    theme = theme or THEMES[rnd.randrange(len(THEMES))]
    out, prev_tr, prev_kb = [], None, None
    for s in scenes:
        kind = s.get("kind")
        sec = bool(s.get("section_start"))
        tr = _pick(rnd, SECTION_TRANSITIONS if sec else TRANSITIONS, prev_tr)
        item = {"kind": kind, "section_start": sec, "transition": tr,
                "variant": _pick(rnd, _pool(VARIANTS[kind], theme)) if kind in VARIANTS else None,
                "motion": None, "title": None}
        if kind is None:
            item["motion"] = _pick(rnd, KEN_BURNS, prev_kb)
            prev_kb = item["motion"]
        if sec:
            item["title"] = _pick(rnd, _pool(VARIANTS["kicker" if kind else "lower_third"], theme))
        out.append(item)
        prev_tr = tr
    import config
    cold = "typewriter" if config.TYPEWRITER else _pick(rnd, VARIANTS["cold_open"], "typewriter")   # Faza 5.1
    return {"theme": theme, "backdrop": rnd.choice(BACKDROPS), "cold_open": cold,
            "chart_title": _pick(rnd, _pool(VARIANTS["title"], theme)), "scenes": out}


def signature(plan: dict) -> list[str]:
    return [f"{s['variant']}|{s['transition']}|{s['motion']}|{s['title']}" for s in plan["scenes"]]


def similarity(a: list[str], b: list[str]) -> float:
    n = max(len(a), len(b))
    return sum(1 for x, y in zip(a, b) if x == y) / n if n else 0.0


def _load(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def plan_with_history(slug: str, scenes: list[dict], history_path: str) -> dict:
    """Son 3 epizodla oxsarliq > 50% -> theme deyisir (lazim olsa ferqli salt ile yeniden)."""
    recent = [h for h in _load(history_path) if h.get("slug") != slug][-HISTORY_WINDOW:]
    plan = plan_motion(slug, scenes)

    def worst(p: dict) -> float:
        return max((similarity(signature(p), h.get("signature") or []) for h in recent), default=0.0)
    if worst(plan) <= SIMILARITY_MAX:
        return plan
    first = plan["theme"]
    for salt in range(1, 4 * len(THEMES)):
        theme = THEMES[(THEMES.index(first) + 1 + (salt - 1) % (len(THEMES) - 1)) % len(THEMES)]
        cand = plan_motion(slug, scenes, theme=theme, salt=salt)
        if worst(cand) <= SIMILARITY_MAX:
            return cand
    return cand


def remember(history_path: str, slug: str, plan: dict) -> None:
    """plan: plan_motion neticesi ve ya {"theme", "signature"} (remotion_build props-dan)."""
    data = [h for h in _load(history_path) if h.get("slug") != slug]
    sig = plan.get("signature") or signature(plan)
    data.append({"slug": slug, "theme": plan["theme"], "signature": sig})
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(data[-HISTORY_KEEP:], f, ensure_ascii=False, indent=1)


# --- Faza 3.7: nitqle sinxron vurgu (reqem seslenende qisa pulse/glow) ---
PULSE_FRAMES = 12            # <= 400 ms (30 fps)
MAX_FLASH_PER_S = 3
BIG_GAP_S = 20.0             # her 20 s-de <= 1 "boyuk" effekt
NUMERIC_KINDS = {"stats", "bars", "counter", "ring", "table", "threshold", "timeseries", "usmap", "equation",
                 "compare", "line"}
BIG_KINDS = {"table", "threshold"}


def emphasis(props: dict) -> list[dict]:
    """[{at: qlobal kadr, frames, big}] - reqemli elementin reveal-i ve foto overlay-i; boyuk effekt qerar
    vizuallarinda ve overlay-de, 20 s-de bir. Saniyede 3-den cox flash yoxdur."""
    fps = props["fps"]
    start = props["introFrames"]
    cands: list[tuple[int, bool]] = []
    for s in props["scenes"]:
        v = s.get("visual")
        if v and v.get("kind") in NUMERIC_KINDS:
            rev = s.get("reveal") or []
            cands += [(start + f, v["kind"] in BIG_KINDS and k == len(rev) - 1) for k, f in enumerate(rev)]
        elif s.get("overlay"):
            cands.append((start + s["overlay"]["from"], True))
        start += s["frames"]
    out: list[dict] = []
    last_big = -10 ** 9
    for at, big in sorted(cands):
        if sum(1 for e in out if at - e["at"] < fps) >= MAX_FLASH_PER_S:
            continue
        big = big and at - last_big >= BIG_GAP_S * fps
        if big:
            last_big = at
        out.append({"at": at, "frames": PULSE_FRAMES, "big": big})
    return out


def signature_of_props(props: dict) -> list[str]:
    """Remotion props-dan eyni imza (signature) - tarixce ve QA ucun."""
    return [f"{s.get('variant')}|{s.get('transition')}|{s.get('motion') if not s.get('visual') else None}|"
            f"{s.get('titleVariant')}" for s in props["scenes"]]
