"""Faza 2.1 (istifadeci 2026-10-07): qerar bolmesinin deterministik vizuallari - LLM-siz, plan.model_result-dan.
- table: neticelerin evvel / sonra / ferq setirleri;
- threshold: break-even - modelde bir deyisen deyisdikce neticenin evvelki seviyyeni kesdiyi noqte (curve) ve ya
  esik + bugunku deyer (gauge).
Ekranda yalniz sehne danisiginda deyilen reqemler gorunur (#45 fail-closed); deyilmeyen xana bos qalir.
"""
from __future__ import annotations

import math
import re

import case_model as cm

TITLE_TABLE = "Before and after"
TITLE_THRESHOLD = "The break-even point"
CURVE_POINTS = 24
CROSS_TOL = 0.03          # tapilan kesisme threshold-dan en cox 3% ferqlene biler
SPOKEN_TOL = 0.01         # ekranda deyilen kimi: "67%" = 0.6667
LABEL_MAX = 22


def _label(text: str) -> str:
    words = re.findall(r"[A-Za-z']+", str(text).replace("_", " "))
    out = ""
    for w in words:
        if len((out + " " + w).strip()) > LABEL_MAX:
            break
        out = (out + " " + w).strip()
    return out[:1].upper() + out[1:]


def _spoken(value: float, narration: str, exact: bool = True) -> float | None:
    """Danisiqda deyilen eyni reqem (exact) ve ya ~1% yaxin/faiz formasi (threshold yuvarlaq deyilir)."""
    from visuals import grounded_values
    for v in grounded_values(narration):
        if math.isclose(v, value, rel_tol=1e-9, abs_tol=1e-6):
            return v
    if exact:
        return None
    for v in grounded_values(narration):
        for form in (value, value * 100):
            if math.isclose(v, form, rel_tol=SPOKEN_TOL, abs_tol=1e-6):
                return v
    return None


def decision_table(result: dict, narration: str) -> dict | None:
    from visuals import unit_of
    rows = []
    for k, d in result["delta"].items():
        b, a = result["before"][k], result["after"][k]
        sb, sa = _spoken(b, narration), _spoken(a, narration)
        if sb is None or sa is None:
            continue
        unit = unit_of(sa, narration) or ("$" if result["units"].get(k) == "$" else "")
        rows.append({"label": _label(result.get("labels", {}).get(k, k)), "before": b, "after": a,
                     "delta": d if _spoken(abs(d), narration) is not None else None, "unit": unit})
    if not rows:
        return None
    return {"kind": "table", "title": TITLE_TABLE, "columns": ["Before", "After", "Change"], "rows": rows[:4]}


def _with(model: dict, name: str, value: float) -> dict:
    return {**model, "variables": [{**v, "value": value} if v.get("name") == name else v
                                   for v in model.get("variables") or []]}


def find_curve(model: dict, result: dict) -> dict | None:
    """Bir deyisen x deyisdikce after_r(x) evvelki before_r seviyyesini threshold-da kesirse - break-even egrisi."""
    raw = float(result["threshold"]["raw"])
    for name, value in result["variables"].items():
        for r in result["delta"]:
            base = result["before"][r]

            def f(x: float) -> float | None:
                try:
                    return cm.evaluate(_with(model, name, x))["after"][r] - base
                except cm.CaseModelError:
                    return None
            if f(raw) is None or abs(f(raw)) > CROSS_TOL * max(1.0, abs(base)):
                continue
            hi = 2 * max(raw, abs(value)) or 1.0
            pts = []
            for i in range(CURVE_POINTS + 1):
                x = hi * i / CURVE_POINTS
                y = f(x)
                if y is None:
                    break
                pts.append([round(x, 6), round(y + base, 6)])
            if len(pts) == CURVE_POINTS + 1:
                return {"var": name, "result": r, "cross": raw, "points": pts,
                        "x_label": _label(result.get("labels", {}).get(name, name)), "y_label": _label(r)}
    return None


def _current(result: dict, narration: str, threshold: float) -> dict | None:
    """Esikle eyni kemiyyetin bugunku deyeri (mes. 40 customers vs 27 lazim) - yalniz deyilibse."""
    words = set(re.findall(r"[a-z]+", (result["threshold"]["name"] + " " + result["threshold"]["meaning"]).lower()))
    for name, value in result["variables"].items():
        unit = result["var_units"].get(name, "")
        noun = unit if unit not in ("$", "%", "share") else ""
        if not noun or noun.rstrip("s") not in {w.rstrip("s") for w in words}:
            continue
        if math.isclose(value, threshold) or _spoken(value, narration) is None:
            continue
        return {"value": value, "label": "Today"}
    return None


def decision_threshold(plan: dict, narration: str) -> dict | None:
    from visuals import unit_of
    result = plan["model_result"]
    t = result["threshold"]
    shown = _spoken(t["value"], narration, exact=False)
    if shown is None and t["raw"] != t["value"]:
        shown = _spoken(t["raw"], narration, exact=False)
    if shown is None:
        return None
    curve = find_curve(plan.get("model") or {}, result) if plan.get("model") else None
    baseline = None
    if curve:
        b = result["before"][curve["result"]]
        if _spoken(b, narration) is not None:
            baseline = {"value": b, "label": _label("today " + curve["result"]), "unit": unit_of(b, narration)}
        curve = {**curve, "baseline": baseline}
    return {"kind": "threshold", "title": TITLE_THRESHOLD,
            "threshold": {"value": shown, "unit": unit_of(shown, narration), "label": _label(t["name"]) or "Break-even"},
            "current": _current(result, narration, t["value"]), "curve": curve}


def decision_section(scenes: list[dict]) -> list[int]:
    heads = [s["section"] for s in scenes if str(s.get("section", "")).startswith("Section ")]
    last = heads[-1] if heads else None
    return [i for i, s in enumerate(scenes) if last and s["section"] == last]


def decision_visuals(scenes: list[dict], plan: dict) -> dict[int, dict]:
    """Qerar bolmesine mecburi: threshold (esik deyilen ilk sehne) + table (evvel/sonra deyilen ilk diger sehne)."""
    if not isinstance(plan.get("model_result"), dict):
        return {}
    idx = decision_section(scenes)
    thr = [(i, sp) for i in idx if (sp := decision_threshold(plan, scenes[i]["narration"]))]
    tab = [(i, sp) for i in idx if (sp := decision_table(plan["model_result"], scenes[i]["narration"]))]
    # #122: ikisi eyni sehnede deyilirse table orada, threshold esiyin deyildiyi basqa sehnede
    pairs = [(t, b) for t in thr for b in tab if t[0] != b[0]]
    if pairs:
        (ti, ts), (bi, bs) = pairs[0]
        return {ti: ts, bi: bs}
    out: dict[int, dict] = {}
    if thr:
        out[thr[0][0]] = thr[0][1]
    elif tab:
        out[tab[0][0]] = tab[0][1]
    return out
