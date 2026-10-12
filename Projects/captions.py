"""Altyazi ssenari metninden (sozbesoz); vaxt sehne sesi icinde herf uzunluguna gore paylanir."""
from __future__ import annotations

import json
import os
import re

import generate

# Durğu işarəsi (istəyə görə bağlayan dırnaq/mötərizə ilə) — bölgü nöqtəsi
_BREAK_RE = r"[,.;:!?][\"'”’)\]]*$"


def chunks(text: str, max_words: int = 7) -> list[str]:
    out, cur = [], []
    for w in text.split():
        cur.append(w)
        if len(cur) >= max_words or (len(cur) >= 3 and re.search(_BREAK_RE, w)):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def build(scenes: list[dict], tail: float = 0.35) -> list[dict]:
    caps, t0 = [], 0.0
    for s in scenes:
        dur = max(0.0, s["duration"])
        parts = chunks(s["text"])
        if not parts:
            t0 += dur
            continue
        speak = max(0.1, dur - tail)
        total = sum(len(p) for p in parts)
        t = t0
        for p in parts:
            d = speak * len(p) / total
            caps.append({"start": round(t, 3), "end": round(t + d, 3), "text": p})
            t += d
        caps[-1]["end"] = round(t0 + dur, 3)
        t0 += dur
    return caps


def _ts(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def to_srt(caps: list[dict]) -> str:
    return "\n".join(f"{i}\n{_ts(c['start'])} --> {_ts(c['end'])}\n{c['text']}\n" for i, c in enumerate(caps, 1))


def main(ep: str) -> None:
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    caps = build(data["scenes"])
    with open(os.path.join(ep, f"{data['slug']}.srt"), "w", encoding="utf-8") as f:
        f.write(to_srt(caps))
    generate.atomic_json(os.path.join(ep, "captions.json"), caps)   # done isaresi en sonda
