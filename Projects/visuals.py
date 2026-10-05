"""Reyestr #45 (istifadeci 2026-10-03): sehnelerin ~60%-i analitik Remotion animasiyasi, qalani foto.
LLM her sehne ucun chart spec teklif edir; burada deterministik yoxlanir:
- spec sxemi (Remotion komponenti ne gozleyirse) ve qisa metn (ekranda oxunsun);
- HER reqem (deyerler + etiketlerdeki reqemler) hemin sehnenin danisiginda deyilmelidir - hesab sehvi
  QETI olmur (#34/#40); equation-da hesab Python-da yoxlanir;
- kecmeyen spec fotoya dusur (fail-closed); #57: reqemli sehne hemise butun reqemlerini gosteren animasiyadir
  (LLM bacarmasa deterministik data kartlari - stats_fallback), generik bullet (keypoints) yoxdur.
"""
from __future__ import annotations

import math
import re
from typing import Callable

from llm import LLMError, chat_json
from math_check import find_numbers

# #57 (istifadeci 2026-10-05): "generik bullet-ler olmasin" - keypoints artiq teklif/qebul olunmur;
# "her reqem qrafik ve ya kartla" - reqemli sehne hemise animasiyadir (stats = data kartlari)
KINDS = ("bars", "line", "compare", "ring", "equation", "flow", "timeline", "counter", "stats")
ANIM_SHARE = 0.6                # istifadeci 2026-10-03: ~60% animasiya (reqemli sehneler bundan asili deyil)
MAX_RUN = 3                     # reqemsiz sehnelerde ardicil en cox 3 animasiya - arada foto nefes verir
MIN_LETTERS = 3                 # LLM numuneni kocurub ".." yazirdi
_LETTER = re.compile(r"[A-Za-z]")
CHUNK = 12
TITLE_MAX, LABEL_MAX, LINE_MAX = 40, 22, 32
UNITS = ("$", "%", "")
OPS = {"+": "+", "-": "-", "−": "-", "×": "×", "x": "×", "*": "×", "÷": "÷", "/": "÷"}
LIMITS = {"bars": (2, 5), "line": (3, 6), "flow": (3, 5), "timeline": (3, 5), "equation": (2, 3), "stats": (1, 4)}

SYSTEM = """You are the motion designer of a premium business explainer video for US business owners.
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
- stats: {"kind":"stats","title":..,"cards":[{"value":number,"label":..}] 1-4}   (data cards: one card per figure)

STRICT number rule: use ONLY numbers that are said in THAT scene's narration, exactly as said.
Never compute, estimate, round or invent a number. EVERY figure said in the scene (dollar amounts, percentages,
counts written in digits) must appear in the animation - if a chart cannot hold them all, use stats cards.
If the narration has no numbers, use flow, compare, timeline or equation WITHOUT values (value null).
Never use bullet lists. No digits inside labels unless said.
Give "score": 0-10 how much an animation helps here (10 = numbers/comparison/process; 0 = pure emotion or
a vivid object that a photo shows better)."""

USER = """Video topic: {topic}

Prefer real analysis: bars, line, compare, ring, equation, counter whenever the scene has numbers or a
comparison; flow or timeline for processes; stats cards when the scene states several unrelated figures.
Every animation title must be different from all other titles in the video.

Return JSON exactly, e.g.:
{{"scenes": [{{"n": 1, "score": 8, "visual": {{"kind": "compare", "title": "Rent vs coffee beans",
"unit": "", "left": {{"label": "Fixed cost", "value": null, "note": "Same every month"}},
"right": {{"label": "Variable cost", "value": null, "note": "Grows with each cup"}}}}}}]}}

Scenes:
{scenes}"""


def _text(s: object) -> str:
    return " ".join(str(s or "").split())


def _num(v: object) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def grounded_values(narration: str) -> list[float]:
    """Tek 'one' sozu chart reqemini esaslandirmir ("One common mistake ... one cent" -> counter '1' kecirdi)."""
    return [v for s, e, v in find_numbers(narration) if narration[s:e].lower() != "one"]


_PERCENT_AFTER = re.compile(r"\s*(?:%|per\s?cent\b)", re.I)


def percent_values(narration: str) -> list[float]:
    """Yalniz faiz kimi deyilen reqemler ("40%", "forty percent") - ring bunlardan biri olmalidir."""
    return [v for _, end, v in find_numbers(narration) if _PERCENT_AFTER.match(narration, end)]


_MONEY_AFTER = re.compile(r"\s*(?:dollars?|bucks?)\b", re.I)


def unit_of(value: float, narration: str) -> str:
    """Reqemin danisiqdaki vahidi: "$4" / "four dollars" -> "$", "40%" / "forty percent" -> "%", qalan "".
    E2E break-even: chart-a vahidi LLM verirdi - "four dollars" ekranda "4" idi, "100 cups" ise "$100" ola bilerdi."""
    for start, end, v in find_numbers(narration):
        if not math.isclose(v, value, rel_tol=1e-9, abs_tol=1e-6):
            continue
        span = narration[start:end].lower()
        money = "dollar" in span or "cent" in span or _MONEY_AFTER.match(narration, end)
        if narration[max(0, start - 1):start] == "$" or money:
            return "$"
        if _PERCENT_AFTER.match(narration, end):
            return "%"
    return ""                   # hec bir deyilisde vahid yoxdur (eyni reqem bir yerde vahidli ola biler)


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
        out.append({"label": label, "value": val, "unit": unit_of(val, narration) if val is not None else ""})
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
    return {"label": label, "value": val, "note": note, "unit": unit_of(val, narration) if val is not None else ""}


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
        good = ok and _text_ok(label, LABEL_MAX, narration)
        return {"value": val, "unit": unit_of(val, narration), "label": label} if good else None
    if kind == "equation":
        op = OPS.get(_text(v.get("op")))
        terms = _labelled(v.get("terms"), *LIMITS["equation"], narration, optional=True)
        result = _labelled([v.get("result")], 1, 1, narration, optional=True)
        if not op or not terms or not result:
            return None
        vals = [t["value"] for t in terms]
        if None not in vals and result[0]["value"] is not None and not _arith_ok(op, vals, result[0]["value"]):
            return None
        res = result[0]
        if op in "+-":          # toplama/cixmada butun hedler eyni vahiddedir ("400 - 200 = 200 dollars")
            shared = next((x["unit"] for x in (*terms, res) if x["unit"]), "")
            terms = [{**t, "unit": shared if t["value"] is not None else ""} for t in terms]
            res = {**res, "unit": shared if res["value"] is not None else ""}
        return {"op": op, "terms": terms, "result": res, "unit": unit}
    if kind == "timeline":
        ev = v.get("events")
        if not isinstance(ev, list) or not LIMITS["timeline"][0] <= len(ev) <= LIMITS["timeline"][1]:
            return None
        out = [{"label": _text(e.get("label")), "when": _text(e.get("when"))} for e in ev if isinstance(e, dict)]
        good = len(out) == len(ev) and all(_text_ok(e["label"], LABEL_MAX, narration)
                                           and (not e["when"] or _text_ok(e["when"], LABEL_MAX, narration))
                                           for e in out)
        return {"events": out} if good else None
    if kind == "stats":
        cards = _labelled(v.get("cards"), *LIMITS["stats"], narration)
        return cards and {"cards": cards} if cards and all(c["value"] is not None for c in cards) else None
    lines = _lines(v.get("steps"), *LIMITS[kind], narration)
    return lines and {"steps": lines}


def validate_visual(v: object, narration: str) -> dict | None:
    """Kecerli spec -> normallasdirilmis spec; her hansi qayda pozulsa None."""
    if not isinstance(v, dict) or v.get("kind") not in KINDS:
        return None
    title = _text(v.get("title"))
    if not _text_ok(title, TITLE_MAX, narration):
        return None
    body = _build(v["kind"], v, narration)
    return {"kind": v["kind"], "title": title, **body} if body else None


_YEAR = re.compile(r"(?:19|20)\d\d")
_STOP = {"and", "or", "but", "to", "that", "which", "so", "because", "if", "when", "while", "than", "then",
         "with", "is", "are", "was", "were", "it", "this", "you", "your"}
_LEAD = {"a", "an", "the", "in", "of", "per", "for", "on", "at", "dollars", "dollar", "percent", "cents"}
_WORDS = re.compile(r"[A-Za-z][A-Za-z'-]*")
_CLAUSE = re.compile(r"[.,;:!?]")


def figures(narration: str) -> list[float]:
    """#57: ekranda gorunmeli reqemler - reqemle yazilan, pul ve faiz; il (1994, 2023) ve kicik sozle sayilar
    ("three months") yox. Tekrar deyer bir defe."""
    out: list[float] = []
    for start, end, v in find_numbers(narration):
        span = narration[start:end]
        if span.lower() in ("one", "a"):
            continue
        unit = unit_of(v, narration)
        if _YEAR.fullmatch(span) and not unit:
            continue
        if (any(ch.isdigit() for ch in span) or unit) and not any(math.isclose(v, x) for x in out):
            out.append(v)
    return out


def _context_label(narration: str, start: int, end: int) -> str:
    """Kart etiketi danisiqdan: reqemden sonraki 1-3 soz ("$4,000 in rent" -> "Rent"), olmasa evvelki 2 soz."""
    after = _WORDS.findall(_CLAUSE.split(narration[end:], maxsplit=1)[0])
    while after and after[0].lower() in _LEAD:
        after = after[1:]
    words: list[str] = []
    for w in after:
        if w.lower() in _STOP or len(words) == 3:
            break
        words.append(w)
    if len("".join(words)) < MIN_LETTERS:
        before = _WORDS.findall(_CLAUSE.split(narration[:start])[-1])
        words = [w for w in before if w.lower() not in _STOP][-2:]
    label = " ".join(words)[:LABEL_MAX].strip()
    return label[:1].upper() + label[1:] if label else ""


def stats_fallback(narration: str, title: str = "") -> dict | None:
    """Deterministik data kartlari: sehnedeki her reqem oz kartinda (LLM chart-i reqemi buraxanda)."""
    wanted = figures(narration)
    cards, seen = [], []
    for start, end, v in find_numbers(narration):
        if not any(math.isclose(v, x) for x in wanted) or any(math.isclose(v, x) for x in seen):
            continue
        seen.append(v)
        cards.append({"value": v, "label": _context_label(narration, start, end) or "Key figure"})
    if not cards:
        return None
    cards = cards[:LIMITS["stats"][1]]
    title = title if _text_ok(title, TITLE_MAX, narration) else (cards[0]["label"] or "Key figures")
    return validate_visual({"kind": "stats", "title": title, "cards": cards}, narration)


def shown_values(v: dict) -> list[float]:
    """Chart-da gorunen reqemler (deyerler + etiketlerdeki reqemler)."""
    vals: list[float] = []

    def walk(o: object) -> None:
        if isinstance(o, dict):
            for k, x in o.items():
                if k == "value" and isinstance(x, (int, float)) and not isinstance(x, bool):
                    vals.append(float(x))
                elif isinstance(x, str):
                    vals.extend(val for _, _, val in find_numbers(x))
                else:
                    walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(v)
    return vals


def covers_figures(v: dict | None, narration: str) -> bool:
    if not v:
        return False
    shown = shown_values(v)
    return all(any(math.isclose(f, x, rel_tol=1e-9, abs_tol=1e-6) for x in shown) for f in figures(narration))


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
                    titles: list[str] | None = None, forced: set[int] = frozenset()) -> set[int]:
    """forced (#57: reqemli sehneler) hemise animasiyadir. Qalanlari: en yuksek balli sehneler (bal < 0 = kecerli
    spec yoxdur), ilk sehne foto, ardicil MAX_RUN-dan cox animasiya olmur, eyni basliq iki defe olmur."""
    want = round(share * len(scores))
    titles = titles or [str(i) for i in range(len(scores))]
    picked = {i for i in forced if scores[i] >= 0}
    seen = {_title_key(titles[i]) for i in picked}
    for i in sorted(range(1, len(scores)), key=lambda k: (-scores[k], k)):
        if len(picked) >= want:
            break
        key = _title_key(titles[i])
        if i in picked or scores[i] < 0 or not _run_ok(picked | {i}, i) or key in seen:
            continue
        picked.add(i)
        seen.add(key)
    return picked


def _candidate(item: dict, narration: str) -> tuple[float, dict | None]:
    raw = item.get("visual") if isinstance(item.get("visual"), dict) else {}
    spec = validate_visual(raw, narration)
    score = _num(item.get("score"))
    return ((score if score is not None else 0.0) if spec else -1.0), spec


# why-9-99 (2026-10-04): LLM mucerred movzuda cox bullet verirdi; #57-den bullet (keypoints) umumiyyetle yoxdur
NO_KEYPOINTS = ("\n\nDo NOT use bullet lists for these scenes: choose flow, compare, timeline or equation "
                "(value null when the narration says no number).")
ALL_FIGURES = ("\n\nShow EVERY figure the narration says in these scenes (each dollar amount, percentage and "
               "digit count) - use bars, compare, equation or stats cards so none is left out.")


def _ask(scenes: list[dict], numbers: list[int], topic: str, chat: Callable, llm_kw: dict,
         note: str = "") -> dict[int, dict]:
    listing = "\n".join(f"{n}. [{scenes[n - 1]['section']}] {scenes[n - 1]['narration']}" for n in numbers)
    try:
        data = chat(SYSTEM, USER.format(topic=topic, scenes=listing) + note, max_tokens=4000, **llm_kw)
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


def _ask_all(scenes: list[dict], numbers: list[int], topic: str, chat: Callable, llm_kw: dict,
             note: str = "") -> dict[int, dict]:
    """CHUNK-larla sorusur; LLM-in buraxdigi sehneler bir defe yeniden sorusulur (why-9-99: 64-68 bos qaldi)."""
    got: dict[int, dict] = {}
    for start in range(0, len(numbers), CHUNK):
        part = numbers[start:start + CHUNK]
        got.update(_ask(scenes, part, topic, chat, llm_kw, note))
        missing = [n for n in part if n not in got]
        if missing:
            got.update(_ask(scenes, missing, topic, chat, llm_kw, note))
    return got


def _pick(scores: list[float], specs: list[dict | None], share: float, forced: set[int]) -> set[int]:
    return choose_animated(scores, share, kinds=[sp["kind"] if sp else "" for sp in specs],
                           titles=[sp["title"] if sp else "" for sp in specs], forced=forced)


def _cover_figures(scenes: list[dict], scores: list[float], specs: list[dict | None], topic: str,
                   chat: Callable, llm_kw: dict) -> set[int]:
    """#57: reqemli sehnenin spec-i butun reqemleri gostermelidir - yoxsa yeniden sorusulur, sonra data kartlari."""
    numeric = [i for i, s in enumerate(scenes) if figures(s["narration"])]
    retry = [i + 1 for i in numeric if not covers_figures(specs[i], scenes[i]["narration"])]
    more = _ask_all(scenes, retry, topic, chat, llm_kw, ALL_FIGURES) if retry else {}
    for n in retry:
        narr = scenes[n - 1]["narration"]
        score, spec = _candidate(more.get(n) or {}, narr)
        if not covers_figures(spec, narr):
            old = specs[n - 1]
            spec, score = stats_fallback(narr, old["title"] if old else ""), max(score, 5.0)
        scores[n - 1], specs[n - 1] = (score, spec) if spec else (-1.0, None)
    return {i for i in numeric if specs[i] is not None}


def plan_visuals(scenes: list[dict], topic: str, chat: Callable = chat_json, share: float = ANIM_SHARE,
                 **llm_kw) -> list[dict | None]:
    """Her sehne ucun animasiya spec-i ve ya None (foto). Reqemli sehneler hemise butun reqemleri gosteren
    animasiyadir (#57); pay catmasa kecmeyen reqemsiz sehneler bullet-siz yeniden sorusulur."""
    got = _ask_all(scenes, list(range(1, len(scenes) + 1)), topic, chat, llm_kw)
    pairs = [_candidate(got.get(n) or {}, scenes[n - 1]["narration"]) for n in range(1, len(scenes) + 1)]
    scores, specs = [p[0] for p in pairs], [p[1] for p in pairs]
    forced = _cover_figures(scenes, scores, specs, topic, chat, llm_kw)
    picked = _pick(scores, specs, share, forced)
    if len(picked) < round(share * len(scenes)):
        retry = [i + 1 for i in range(1, len(scenes)) if i not in picked and specs[i] is None]
        more = _ask_all(scenes, retry, topic, chat, llm_kw, NO_KEYPOINTS) if retry else {}
        for n in retry:
            score, spec = _candidate(more.get(n) or {}, scenes[n - 1]["narration"])
            if spec:
                scores[n - 1], specs[n - 1] = score, spec
        picked = _pick(scores, specs, share, forced)
    print(f"  animasiya: {len(picked)}/{len(scenes)} sehne, reqemli {len(forced)} ("
          + ", ".join(f"{k}x{sum(1 for i in picked if specs[i]['kind'] == k)}" for k in KINDS
                      if any(specs[i]["kind"] == k for i in picked)) + ")", flush=True)
    return [specs[i] if i in picked else None for i in range(len(scenes))]
