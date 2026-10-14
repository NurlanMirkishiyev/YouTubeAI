"""Altyazi ssenari metninden (sozbesoz). Her sozun vaxti TTS soz vaxtlarindan (voice/scNN.words.json) gelir -
ekranda oxunan soz rengle izlenir. Reqemler TTS-de soze cevrildiyi ucun ($15 -> fifteen dollars) ekran sozleri
danisilan sozlerle difflib ile uygunlasdirilir; uygun gelmeyen soz qonsulari arasinda paylanir.
Vaxt fayli yoxdursa (kohne epizod) vaxt sehne sesi icinde herf uzunluguna gore paylanir."""
from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher

import generate
from speech import to_speech

# Durğu işarəsi (istəyə görə bağlayan dırnaq/mötərizə ilə) — bölgü nöqtəsi
_BREAK_RE = r"[,.;:!?—][\"'”’)\]]*$"
PIECE = re.compile(r"[a-z0-9]+")


def chunks(text: str, max_words: int = 6) -> list[str]:
    out, cur = [], []
    for w in text.split():
        cur.append(w)
        if len(cur) >= max_words or (len(cur) >= 3 and re.search(_BREAK_RE, w)):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def _pieces(word: str) -> list[str]:
    return PIECE.findall(word.lower().replace("’", "").replace("'", ""))


def _proportional(words: list[str], start: float, end: float) -> list[tuple[float, float]]:
    total = sum(len(w) for w in words) or 1
    out, t = [], start
    for w in words:
        d = (end - start) * len(w) / total
        out.append((t, t + d))
        t += d
    return out


def word_spans(words: list[str], speak: float, toks: list[dict] | None) -> list[tuple[float, float]]:
    """Ekran sozlerinin (start, end) vaxtlari sehnenin evvelinden."""
    if not toks:
        return _proportional(words, 0.0, speak)
    disp = [(i, p) for i, w in enumerate(words) for p in _pieces(to_speech(w))]
    spoken = [(t["s"], t["e"], p) for t in toks for p in _pieces(t["w"])]
    hit: dict[int, list[tuple[float, float]]] = {}
    sm = SequenceMatcher(None, [p for _, p in disp], [p for *_, p in spoken], autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            s, e, _ = spoken[blk.b + k]
            hit.setdefault(disp[blk.a + k][0], []).append((s, e))
    spans: list[tuple[float, float] | None] = [
        (min(s for s, _ in hit[i]), max(e for _, e in hit[i])) if i in hit else None for i in range(len(words))]
    i = 0
    while i < len(words):                      # uygun gelmeyen ardicil sozler qonsular arasinda paylanir
        if spans[i] is not None:
            i += 1
            continue
        j = i
        while j < len(words) and spans[j] is None:
            j += 1
        lo = spans[i - 1][1] if i > 0 else 0.0
        hi = spans[j][0] if j < len(words) else max(lo, speak)
        spans[i:j] = _proportional(words[i:j], lo, max(lo, hi))
        i = j
    return [(round(s, 3), round(e, 3)) for s, e in spans]


def build(scenes: list[dict], tail: float = 0.35, timings: dict | None = None) -> list[dict]:
    caps, t0 = [], 0.0
    for s in scenes:
        dur = max(0.0, s["duration"])
        parts = chunks(s["text"])
        if not parts:
            t0 += dur
            continue
        words = [w for p in parts for w in p.split()]
        spans = word_spans(words, max(0.1, dur - tail), (timings or {}).get(s.get("n")))
        k = 0
        scene_caps = []
        for p in parts:
            n = len(p.split())
            ws = [{"start": round(t0 + a, 3), "end": round(t0 + b, 3), "text": w}
                  for w, (a, b) in zip(p.split(), spans[k:k + n])]
            scene_caps.append({"start": ws[0]["start"], "end": ws[-1]["end"], "text": p, "words": ws})
            k += n
        scene_caps[0]["start"] = round(t0, 3)
        for a, b in zip(scene_caps, scene_caps[1:]):   # bosluq yoxdur: altyazi novbetinin evveline qeder qalir
            a["end"] = b["start"]
        scene_caps[-1]["end"] = round(t0 + dur, 3)
        caps += scene_caps
        t0 += dur
    return caps


def _ts(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def to_srt(caps: list[dict]) -> str:
    return "\n".join(f"{i}\n{_ts(c['start'])} --> {_ts(c['end'])}\n{c['text']}\n" for i, c in enumerate(caps, 1))


def _timings(ep: str, scenes: list[dict]) -> dict:
    out = {}
    for s in scenes:
        path = os.path.join(ep, "voice", f"sc{s['n']:02d}.words.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                out[s["n"]] = json.load(f)
    return out


def main(ep: str) -> None:
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    caps = build(data["scenes"], timings=_timings(ep, data["scenes"]))
    with open(os.path.join(ep, f"{data['slug']}.srt"), "w", encoding="utf-8") as f:
        f.write(to_srt(caps))
    generate.atomic_json(os.path.join(ep, "captions.json"), caps)   # done isaresi en sonda
