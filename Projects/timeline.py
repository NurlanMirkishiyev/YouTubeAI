"""Epizod zaman xetti: bolme baslangiclari (YouTube fesilleri) ve intro/outro ehtiyat muddetleri."""
from __future__ import annotations

import re

INTRO_S = 4.0    # scenes.json-da intro_seconds yoxdursa (kohne epizod)
OUTRO_S = 6.0    # scenes.json-da outro_seconds yoxdursa


COLD_OPEN = "Cold Open"   # #56: ilk 3 saniyenin hook cumlesi - giris kartinda seslenir, sehne deyil


def cold_open(markdown: str) -> str | None:
    m = re.search(r"^## Cold Open\s*\n(.*?)(?=^## |\Z)", markdown, re.M | re.S)
    text = " ".join(m.group(1).split()) if m else ""
    return text or None


def intro_text(markdown: str, topic: str) -> str:
    """Giris kartinin seslendirdiyi metn: Cold Open (ilk 3 s-de reqem), kohne skriptde movzu basligi."""
    return cold_open(markdown) or topic


def display_title(section: str) -> str:
    return re.sub(r"^Section\s+\d+\s*:\s*", "", section).strip()


def spoken_titles(scenes: list[dict]) -> list[str | None]:
    """Bolmenin ilk sehnesi ucun seslendirilecek (ve lower-third) basliq; Hook basliqsiz baslayir."""
    out: list[str | None] = []
    for i, s in enumerate(scenes):
        first = i == 0 or scenes[i - 1]["section"] != s["section"]
        hook = re.match(r"hook\b", s["section"], re.I)
        out.append(display_title(s["section"]) if first and not hook else None)
    return out


def section_starts(scenes: list[dict], offset_s: float = 0.0) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    t = offset_s
    for s in scenes:
        if not out or out[-1][0] != s["section"]:
            out.append((s["section"], round(t, 2)))
        t += float(s["duration"])
    return out
