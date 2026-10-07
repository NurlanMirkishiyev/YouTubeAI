"""Faza 2.2/2.3 (istifadeci 2026-10-07; ideya: docs/referance/video_yarat_v4.py sehm qrafiki ve ABS xeritesi).
Sabit kodlanmis data yoxdur: reqemler sehne danisigindan (visuals._said ile yoxlanir).
- timeseries: zamanla deyisen reqemler; seyrek noqteler (< DENSE) xetti interpolasiya ile sixlasdirilir - o zaman
  ekranda "illustrative" qeydi; enis seqmentleri ayri rengde; hadise etiketi oz noqtesinde acilir.
- usmap: ABS konturu (reference koordinatlari) + nöqteler seed = slug hash ile; artim/azalma sayqaci.
"""
from __future__ import annotations

import hashlib
import math
import random

import layout

DENSE = 4               # bundan az deyilen noqte -> interpolasiya (illustrative)
TS_LIMITS = (2, 8)
EVENTS_MAX = 3
MAP_KEYS = (1, 4)
MAX_DOTS = 300          # boyuk saylarda bir noqte bir nece vahiddir (sayqac real reqemi gosterir)

# ABS (48 stat) konturu - reference skriptden (lon, lat)
US = [(-124.7, 48.4), (-122.8, 49.0), (-95.2, 49.0), (-89.6, 48.0), (-84.5, 46.5), (-83.5, 46.1),
      (-82.4, 43.0), (-83.1, 42.0), (-82.5, 41.7), (-79.8, 42.2), (-79.0, 43.3), (-76.3, 43.5),
      (-75.0, 44.8), (-71.5, 45.0), (-70.0, 46.7), (-69.2, 47.4), (-67.8, 47.1), (-67.0, 44.8),
      (-70.2, 43.6), (-70.8, 42.5), (-70.0, 41.8), (-71.5, 41.3), (-73.9, 40.6), (-74.0, 39.6),
      (-75.0, 38.9), (-76.0, 37.0), (-75.5, 35.2), (-77.9, 33.9), (-79.9, 32.7), (-81.4, 30.5),
      (-80.0, 26.7), (-80.4, 25.2), (-81.8, 26.1), (-82.6, 27.8), (-83.0, 29.1), (-84.3, 30.0),
      (-85.4, 29.7), (-86.8, 30.4), (-88.5, 30.4), (-89.6, 30.2), (-89.4, 29.0), (-90.5, 29.1),
      (-92.0, 29.6), (-94.0, 29.7), (-95.0, 29.1), (-97.2, 27.6), (-97.2, 25.9), (-99.5, 27.5),
      (-101.4, 29.8), (-103.1, 29.0), (-104.5, 29.6), (-106.5, 31.8), (-108.2, 31.8), (-111.1, 31.3),
      (-114.8, 32.5), (-117.1, 32.5), (-118.4, 34.0), (-120.6, 34.6), (-121.9, 36.6), (-122.5, 37.8),
      (-123.8, 39.8), (-124.4, 42.0), (-124.1, 44.5), (-124.0, 46.3)]
LON0, LON1, LAT0, LAT1 = -125.0, -66.5, 24.8, 49.5


def _interp(points: list[dict]) -> list[dict]:
    """Deyilen her iki noqte arasina bir ara noqte (label bos, shown False) - yalniz xettin formasi ucun."""
    out = []
    for a, b in zip(points, points[1:]):
        out += [a, {"label": "", "value": round((a["value"] + b["value"]) / 2, 4), "shown": False}]
    return out + [points[-1]]


def build_timeseries(v: dict, narration: str, said, text_ok, label_max: int) -> dict | None:
    pts = v.get("points")
    if not isinstance(pts, list) or not TS_LIMITS[0] <= len(pts) <= TS_LIMITS[1]:
        return None
    clean = []
    for p in pts:
        if not isinstance(p, dict) or not isinstance(p.get("value"), (int, float)) or isinstance(p.get("value"), bool):
            return None
        label = " ".join(str(p.get("label") or "").split())
        if not said(float(p["value"]), narration) or not text_ok(label, label_max, narration, letters=False):
            return None
        clean.append({"label": label, "value": float(p["value"]), "shown": True})
    events = []
    for e in v.get("events") or []:
        if not isinstance(e, dict) or not isinstance(e.get("index"), int) or not 0 <= e["index"] < len(clean):
            return None
        label = " ".join(str(e.get("label") or "").split())
        if not text_ok(label, label_max, narration):
            return None
        events.append({"index": e["index"], "label": label})
    illustrative = len(clean) < DENSE
    full = _interp(clean) if illustrative else clean
    pos = [i for i, p in enumerate(full) if p["shown"]]
    events = [{**e, "index": pos[e["index"]]} for e in events[:EVENTS_MAX]]
    segments = [{"from": i, "to": i + 1, "down": full[i + 1]["value"] < full[i]["value"]} for i in range(len(full) - 1)]
    unit = v.get("unit") if v.get("unit") in ("$", "%", "") else ""
    return {"unit": unit, "points": full, "events": events, "segments": segments, "illustrative": illustrative}


def build_usmap(v: dict, narration: str, said, text_ok, label_max: int) -> dict | None:
    keys = v.get("keys")
    if not isinstance(keys, list) or not MAP_KEYS[0] <= len(keys) <= MAP_KEYS[1]:
        return None
    out = []
    for k in keys:
        if not isinstance(k, dict) or not isinstance(k.get("value"), (int, float)) or isinstance(k.get("value"), bool):
            return None
        label = " ".join(str(k.get("label") or "").split())
        if k["value"] < 0 or not said(float(k["value"]), narration) or not text_ok(label, label_max, narration):
            return None
        out.append({"value": float(k["value"]), "label": label})
    unit_label = " ".join(str(v.get("unit_label") or "").split())
    if not text_ok(unit_label, label_max, narration):
        return None
    return {"unit_label": unit_label, "keys": out}


def _in_poly(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _projector():
    k = math.cos(math.radians(38))
    bx, by, bw, bh = layout.MAP_BOX
    s = min(bw / ((LON1 - LON0) * k), bh / (LAT1 - LAT0))
    mw, mh = (LON1 - LON0) * k * s, (LAT1 - LAT0) * s
    ox, oy = bx + (bw - mw) / 2, by + (bh - mh) / 2
    return lambda lon, lat: (round(ox + (lon - LON0) * k * s, 1), round(oy + (LAT1 - lat) * s, 1))


def seed_of(slug: str) -> int:
    return int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:12], 16)


def place_map(v: dict, slug: str) -> dict:
    """Konturu ve noqteleri elave edir - seed = slug hash (eyni epizod -> eyni xerite, ferqli -> ferqli)."""
    proj = _projector()
    peak = max(k["value"] for k in v["keys"])
    per_dot = max(1.0, math.ceil(peak / MAX_DOTS))
    n = int(math.ceil(peak / per_dot)) + 5
    rnd = random.Random(seed_of(slug))
    dots = []
    while len(dots) < n:
        lon, lat = rnd.uniform(LON0, LON1), rnd.uniform(LAT0, LAT1)
        if _in_poly(lon, lat, US) and rnd.random() < 0.3 + 0.7 * (lon - LON0) / (LON1 - LON0):
            dots.append(list(proj(lon, lat)))
    return {**v, "outline": [list(proj(*p)) for p in US], "dots": dots, "per_dot": per_dot,
            "counter": list(layout.MAP_COUNTER)}
