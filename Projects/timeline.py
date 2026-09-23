"""Epizod zaman xetti: montage muddetleri, intro/outro, SRT surusmesi, bolme baslangiclari."""
from __future__ import annotations

import re

INTRO_S = 4.0    # intro karti; narration bu qeder surusur
OUTRO_S = 6.0    # outro karti; narration bitenden sonra

_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def plan_timeline(scene_durs: list[float], xfade: float,
                  intro_s: float = 0.0, outro_s: float = 0.0) -> list[float]:
    """montage.py ucun klip muddetleri. montage her kecidde xfade qeder ortusme yaradir
    (total = sum(d) - xfade*(n-1)), ona gore sonuncudan basqa her klip xfade qeder uzadilir."""
    clips = ([intro_s] if intro_s > 0 else []) + [float(d) for d in scene_durs] \
        + ([outro_s] if outro_s > 0 else [])
    if not clips:
        raise ValueError("bos timeline")
    return [round(d + xfade, 3) for d in clips[:-1]] + [round(clips[-1], 3)]


def montage_total(durs: list[float], xfade: float) -> float:
    return sum(durs) - xfade * (len(durs) - 1)


def _fmt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def shift_srt(text: str, offset_s: float) -> str:
    def rep(m: re.Match) -> str:
        t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
        return _fmt(max(0.0, t + offset_s))
    return _TS.sub(rep, text)


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


def first_of_section(scenes: list[dict]) -> list[bool]:
    return [i == 0 or scenes[i - 1]["section"] != s["section"] for i, s in enumerate(scenes)]
