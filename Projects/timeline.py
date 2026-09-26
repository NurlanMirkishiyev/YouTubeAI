"""Epizod zaman xetti: bolme baslangiclari (YouTube fesilleri) ve intro/outro ehtiyat muddetleri."""
from __future__ import annotations

import re

INTRO_S = 4.0    # scenes.json-da intro_seconds yoxdursa (kohne epizod)
OUTRO_S = 6.0    # scenes.json-da outro_seconds yoxdursa


def display_title(section: str) -> str:
    return re.sub(r"^Section\s+\d+\s*:\s*", "", section).strip()


def section_starts(scenes: list[dict], offset_s: float = 0.0) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    t = offset_s
    for s in scenes:
        if not out or out[-1][0] != s["section"]:
            out.append((s["section"], round(t, 2)))
        t += float(s["duration"])
    return out
