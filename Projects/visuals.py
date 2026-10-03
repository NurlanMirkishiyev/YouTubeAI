"""Reyestr #45 (istifadeci 2026-10-03): sehnelerin ~60%-i analitik Remotion animasiyasi, qalani foto.
LLM her sehne ucun chart spec teklif edir; burada deterministik yoxlanir:
- spec sxemi (Remotion komponenti ne gozleyirse) ve qisa metn (ekranda oxunsun);
- HER reqem (deyerler + etiketlerdeki reqemler) hemin sehnenin danisiginda deyilmelidir - hesab sehvi
  QETI olmur (#34/#40); equation-da hesab Python-da yoxlanir;
- kecmeyen spec reqemsiz "keypoints"-e, o da alinmasa fotoya dusur (fail-closed).
"""
from __future__ import annotations

import math
import re
from typing import Callable

from llm import LLMError, chat_json
from math_check import find_numbers

KINDS = ("bars", "line", "compare", "ring", "equation", "flow", "timeline", "counter", "keypoints")
ANIM_SHARE = 0.6                # istifadeci 2026-10-03: ~60% animasiya
MAX_RUN = 3                     # ardicil en cox 3 animasiya - arada foto nefes verir
# E2E break-even (2026-10-04): 40 animasiyanin 22-si keypoints idi - "analitik" gorunmurdu
KEYPOINTS_SHARE = 0.3
MIN_LETTERS = 3                 # LLM numuneni kocurub ".." yazirdi
_LETTER = re.compile(r"[A-Za-z]")
CHUNK = 12
TITLE_MAX, LABEL_MAX, LINE_MAX = 40, 22, 32
UNITS = ("$", "%", "")
OPS = {"+": "+", "-": "-", "−": "-", "×": "×", "x": "×", "*": "×", "÷": "÷", "/": "÷"}
LIMITS = {"bars": (2, 5), "line": (3, 6), "flow": (3, 5), "timeline": (3, 5), "keypoints": (2, 4),
          "equation": (2, 3)}

SYSTEM = """You are the motion designer of a premium business explainer video for adults (25-45).
Most scenes get an ANALYTICAL ANIMATION (chart/diagram) drawn in code next to the host owl; the rest keep a photo.
For each numbered scene propose the ONE animation that best explains what the narration says right now.

Kinds and JSON fields (labels <= 22 characters, titles <= 40, steps/points <= 32, English):
- bars: {"kind":"bars","title":..,"unit":"$"|"%"|"","items":[{"label":..,"value":number}] 2-5}
- line: {"kind":"line","title":..,"unit":..,"points":[{"label":..,"value":number}] 3-6}  (a trend over time)
- compare: {"kind":"compare","title":..,"left":{"label":..,"value":number|null,"note":..},"right":{...}}
- ring: {"kind":"ring","title":..,"value":percent 0-100,"label":..}
- equation: {"kind":"equation","title":..,"op":"+"|"-"|"×"|"÷","terms":[{"label":..,"value":number|null}] 2-3,
  "result":{"label":..,"value":number|null}}   e.g. Revenue - Costs = Profit
- flow: {"kind":"flow","title":..,"steps":[..] 3-5}   (a process / cause and effect chain)
- timeline: {"kind":"timeline","title":..,"events":[{"label":..,"when":..}] 3-5}
- counter: {"kind":"counter","title":..,"value":number,"unit":..,"label":..}   (one big number)
- keypoints: {"kind":"keypoints","title":..,"points":[..] 2-4}

STRICT number rule: use ONLY numbers that are said in THAT scene's narration, exactly as said.
Never compute, estimate, round or invent a number. If the narration has no numbers, use flow, compare,
timeline, keypoints or equation WITHOUT values (value null). No digits inside labels unless said.
Also give "points": 2-4 short phrases WITHOUT any numbers that summarise the scene (fallback),
and "score": 0-10 how much an animation helps here (10 = numbers/comparison/process; 0 = pure emotion or
a vivid object that a photo shows better)."""

USER = """Video topic: {topic}

Prefer real analysis: bars, line, compare, ring, equation, counter whenever the scene has numbers or a
comparison; flow or timeline for processes. Use keypoints only when nothing else fits. Every animation title
must be different from all other titles in the video.

Return JSON exactly, e.g.:
{{"scenes": [{{"n": 1, "score": 8, "visual": {{"kind": "compare", "title": "Rent vs coffee beans",
"unit": "", "left": {{"label": "Fixed cost", "value": null, "note": "Same every month"}},
"right": {{"label": "Variable cost", "value": null, "note": "Grows with each cup"}}}},
"points": ["Fixed costs stay put", "Variable costs follow sales"]}}]}}

Scenes:
{scenes}"""


def _text(s: object) -> str:
    return " ".join(str(s or "").split())


def _num(v: object) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def grounded_values(narration: str) -> list[float]:
    return [v for _, _, v in find_numbers(narration)]


_PERCENT_AFTER = re.compile(r"\s*(?:%|per\s?cent)", re.I)


def percent_values(narration: str) -> list[float]:
    """Yalniz faiz kimi deyilen reqemler ("40%", "forty percent") - ring bunlardan biri olmalidir."""
    return [v for _, end, v in find_numbers(narration) if _PERCENT_AFTER.match(narration, end)]


def _said(value: float, narration: str, pool: list[float] | None = None) -> bool:
    vals = grounded_values(narration) if pool is None else pool
    return any(math.isclose(value, v, rel_tol=1e-9, abs_tol=1e-6) for v in vals)


def _text_ok(s: str, limit: int, narration: str) -> bool:
    """Bos deyil, qisa, icindeki her reqem (soz ve ya reqem) danisiqda deyilib."""
    return len(_LETTER.findall(s)) >= MIN_LETTERS and len(s) <= limit and all(_said(v, narration) for _, _, v in find_numbers(s))


def _value_ok(v: object, narration: str, optional: bool = False) -> tuple[bool, float | None]:
    if v is None and optional:
        return True, None
    x = _num(v)
    return (x is not None and _said(x, narration)), x


def _labelled(items: object, lo: int, hi: int, narration: str, optional: bool = False) -> list[dict] | None:
    if not isinstance(items, list) or not lo <= len(items) <= hi:
        return None
    out = []
    for it in items:
        if not isinstance(it, dict):
            return None
        label = _text(it.get("label"))
        ok, val = _value_ok(it.get("value"), narration, optional)
        if not ok or not _text_ok(label, LABEL_MAX, narration):
            return None
        out.append({"label": label, "value": val})
    return out


def _lines(items: object, lo: int, hi: int, narration: str) -> list[str] | None:
    if not isinstance(items, list) or not lo <= len(items) <= hi:
        return None
    out = [_text(x) for x in items]
    return out if all(_text_ok(x, LINE_MAX, narration) for x in out) else None


def _arith_ok(op: str, terms: list[float], result: float) -> bool:
    acc = terms[0]
    for t in terms[1:]:
        if op == "÷" and t == 0:
            return False
        acc = {"+": acc + t, "-": acc - t, "×": acc * t, "÷": acc / t if t else acc}[op]
    return math.isclose(acc, result, rel_tol=0.005, abs_tol=0.005)


def _side(d: object, narration: str) -> dict | None:
    if not isinstance(d, dict):
        return None
    label, note = _text(d.get("label")), _text(d.get("note"))
    ok, val = _value_ok(d.get("value"), narration, optional=True)
    if not ok or not _text_ok(label, LABEL_MAX, narration) or (note and not _text_ok(note, LINE_MAX, narration)):
        return None
    return {"label": label, "value": val, "note": note}


def _build(kind: str, v: dict, narration: str) -> dict | None:
    unit = v.get("unit") if v.get("unit") in UNITS else ""
    if kind in ("bars", "line"):
        key = "items" if kind == "bars" else "points"
        items = _labelled(v.get(key), *LIMITS[kind], narration)
        return items and {key: items, "unit": unit}
    if kind == "compare":
        left, right = _side(v.get("left"), narration), _side(v.get("right"), narration)
        return left and right and {"left": left, "right": right, "unit": unit}
    if kind == "ring":
        ok, val = _value_ok(v.get("value"), narration)
        label = _text(v.get("label"))
        good = ok and 0 < val <= 100 and _said(val, narration, percent_values(narration))             and _text_ok(label, LABEL_MAX, narration)
        return {"value": val, "label": label} if good else None
    if kind == "counter":
        ok, val = _value_ok(v.get("value"), narration)
        label = _text(v.get("label"))
        return {"value": val, "unit": unit, "label": label} if ok and _text_ok(label, LABEL_MAX, narration) else None
    if kind == "equation":
        op = OPS.get(_text(v.get("op")))
        terms = _labelled(v.get("terms"), *LIMITS["equation"], narration, optional=True)
        result = _labelled([v.get("result")], 1, 1, narration, optional=True)
        if not op or not terms or not result:
            return None
        vals = [t["value"] for t in terms]
        if None not in vals and result[0]["value"] is not None and not _arith_ok(op, vals, result[0]["value"]):
            return None
        return {"op": op, "terms": terms, "result": result[0], "unit": unit}
    if kind == "timeline":
        ev = v.get("events")
        if not isinstance(ev, list) or not LIMITS["timeline"][0] <= len(ev) <= LIMITS["timeline"][1]:
            return None
        out = [{"label": _text(e.get("label")), "when": _text(e.get("when"))} for e in ev if isinstance(e, dict)]
        good = len(out) == len(ev) and all(_text_ok(e["label"], LABEL_MAX, narration)
                                           and (not e["when"] or _text_ok(e["when"], LABEL_MAX, narration))
                                           for e in out)
        return {"events": out} if good else None
    key = "steps" if kind == "flow" else "points"
    lines = _lines(v.get(key), *LIMITS[kind], narration)
    return lines and {key: lines}


def validate_visual(v: object, narration: str) -> dict | None:
    """Kecerli spec -> normallasdirilmis spec; her hansi qayda pozulsa None."""
    if not isinstance(v, dict) or v.get("kind") not in KINDS:
        return None
    title = _text(v.get("title"))
    if not _text_ok(title, TITLE_MAX, narration):
        return None
    body = _build(v["kind"], v, narration)
    return {"kind": v["kind"], "title": title, **body} if body else None


def to_keypoints(v: object, narration: str) -> dict | None:
    """Reqemsiz ehtiyat: LLM-in "points"-inden reqem dasimayanlar (danisiqda deyilmeyen) saxlanir."""
    if not isinstance(v, dict):
        return None
    pts = [_text(p) for p in (v.get("points") or []) if isinstance(p, str)]
    pts = [p for p in pts if _text_ok(p, LINE_MAX, narration)][:LIMITS["keypoints"][1]]
    title = _text(v.get("title"))
    if len(pts) < LIMITS["keypoints"][0] or not _text_ok(title, TITLE_MAX, narration):
        return None
    return {"kind": "keypoints", "title": title, "points": pts}


def _run_ok(picked: set[int], i: int) -> bool:
    lo = i
    while lo - 1 in picked:
        lo -= 1
    hi = i
    while hi + 1 in picked:
        hi += 1
    return hi - lo + 1 <= MAX_RUN


def _title_key(t: str) -> str:
    return "".join(_WORDCH.findall(t.lower()))


_WORDCH = re.compile(r"[a-z0-9]")


def choose_animated(scores: list[float], share: float = ANIM_SHARE, kinds: list[str] | None = None,
                    titles: list[str] | None = None) -> set[int]:
    """En yuksek balli sehneler (bal < 0 = kecerli spec yoxdur). Ilk sehne foto (intro-dan sonra canli kadr),
    ardicil MAX_RUN-dan cox animasiya olmur, keypoints <= KEYPOINTS_SHARE, eyni basliq iki defe olmur."""
    want = round(share * len(scores))
    kinds = kinds or [""] * len(scores)
    titles = titles or [str(i) for i in range(len(scores))]
    kp_cap = max(1, round(KEYPOINTS_SHARE * want))
    picked: set[int] = set()
    seen: set[str] = set()
    for i in sorted(range(1, len(scores)), key=lambda k: (-scores[k], k)):
        if len(picked) >= want:
            break
        key = _title_key(titles[i])
        if scores[i] < 0 or not _run_ok(picked | {i}, i) or key in seen:
            continue
        if kinds[i] == "keypoints" and sum(1 for j in picked if kinds[j] == "keypoints") >= kp_cap:
            continue
        picked.add(i)
        seen.add(key)
    return picked


def _candidate(item: dict, narration: str) -> tuple[float, dict | None]:
    raw = item.get("visual") if isinstance(item.get("visual"), dict) else {}
    spec = validate_visual(raw, narration) or to_keypoints(
        {"title": raw.get("title"), "points": item.get("points") or raw.get("points")}, narration)
    score = _num(item.get("score"))
    return ((score if score is not None else 0.0) if spec else -1.0), spec


def _ask(scenes: list[dict], numbers: list[int], topic: str, chat: Callable, llm_kw: dict) -> dict[int, dict]:
    listing = "\n".join(f"{n}. [{scenes[n - 1]['section']}] {scenes[n - 1]['narration']}" for n in numbers)
    try:
        data = chat(SYSTEM, USER.format(topic=topic, scenes=listing), max_tokens=4000, **llm_kw)
    except LLMError as e:
        print(f"  animasiya plani xetasi: {str(e)[:120]} - bu sehneler foto qalir", flush=True)
        return {}
    out = {}
    for it in data.get("scenes") or []:
        try:
            out[int(it.get("n"))] = it
        except (TypeError, ValueError, AttributeError):
            continue
    return out


def plan_visuals(scenes: list[dict], topic: str, chat: Callable = chat_json, share: float = ANIM_SHARE,
                 **llm_kw) -> list[dict | None]:
    """Her sehne ucun animasiya spec-i ve ya None (foto)."""
    scores: list[float] = []
    specs: list[dict | None] = []
    for start in range(0, len(scenes), CHUNK):
        numbers = list(range(start + 1, min(len(scenes), start + CHUNK) + 1))
        got = _ask(scenes, numbers, topic, chat, llm_kw)
        for n in numbers:
            score, spec = _candidate(got.get(n) or {}, scenes[n - 1]["narration"])
            scores.append(score)
            specs.append(spec)
    picked = choose_animated(scores, share, kinds=[sp["kind"] if sp else "" for sp in specs],
                             titles=[sp["title"] if sp else "" for sp in specs])
    print(f"  animasiya: {len(picked)}/{len(scenes)} sehne ("
          + ", ".join(f"{k}x{sum(1 for i in picked if specs[i]['kind'] == k)}" for k in KINDS
                      if any(specs[i]["kind"] == k for i in picked)) + ")", flush=True)
    return [specs[i] if i in picked else None for i in range(len(scenes))]
