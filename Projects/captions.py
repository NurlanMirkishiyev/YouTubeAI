"""#54 (istifadeci 2026-10-05): altyazi SSENARIDEN yaradilir, whisper yalniz soz vaxtlarini verir.
Evvel altyazi whisper-in yazdigi idi: "$9 .99", "Marketing Strategy Retailers are..." (basliq cumleye yapisirdi),
sehv esidilen sozler. Indi: her seslenen hisse (intro karti, bolme basligi + sehne, outro) oz zaman pencereside
ssenari sozlerine (to_display: "$4,000", "15%") whisper vaxtlari uygunlasdirilir (ses formasinda - to_speech).
Elave yoxlama (#54, "reqemler duzgun ingilis telaffuzu ile oxunsun"): ssenarideki her reqem hemin pencerede
whisper-in esitdiyi reqemler arasinda olmalidir - yoxdursa TTS onu sehv oxuyub.
Istifade: Projects\\.venv\\Scripts\\python Projects\\captions.py Episodes\\<slug>
Cixis: captions.words.json (Remotion), captions.srt (YouTube), captions_qa.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from math_check import find_numbers  # noqa: E402
from speech import to_display, to_speech  # noqa: E402
import qa_stamp  # noqa: E402

MAX_CHARS = 42      # bir altyazi setri (Whisper/make_srt.py ile eyni)
MAX_DUR = 5.0
_TOKEN = re.compile(r"[a-z0-9]+")


def _speech_tokens(word: str) -> list[str]:
    return _TOKEN.findall(to_speech(word).lower())


def _flatten(words: list[str]) -> tuple[list[str], list[int]]:
    tokens, owner = [], []
    for i, w in enumerate(words):
        for t in _speech_tokens(w):
            tokens.append(t)
            owner.append(i)
    return tokens, owner


def _fill(times: list[tuple[float, float] | None], t0: float, t1: float) -> list[tuple[float, float]]:
    """Uygunlasmayan sozler qonsu vaxtlar arasinda beraber paylanir (sira qorunur)."""
    out = list(times)
    i = 0
    while i < len(out):
        if out[i] is not None:
            i += 1
            continue
        j = i
        while j < len(out) and out[j] is None:
            j += 1
        lo = out[i - 1][1] if i > 0 else t0
        hi = out[j][0] if j < len(out) else t1
        hi = max(hi, lo)
        step = (hi - lo) / (j - i)
        for k in range(i, j):
            out[k] = (round(lo + (k - i) * step, 3), round(lo + (k - i + 1) * step, 3))
        i = j
    return out


def align_segment(text: str, whisper: list[dict], t0: float, t1: float) -> list[dict]:
    """Ssenari metni (display formasi) + pencerdeki whisper sozleri -> [{"word": " soz", "start", "end"}]."""
    shown = to_display(text).split()
    s_tok, s_own = _flatten(shown)
    w_tok, w_own = _flatten([w["word"].strip() for w in whisper])
    times: list[tuple[float, float] | None] = [None] * len(shown)
    sm = difflib.SequenceMatcher(None, s_tok, w_tok, autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            si, wi = s_own[a + k], whisper[w_own[b + k]]
            st, en = float(wi["start"]), float(wi["end"])
            cur = times[si]
            times[si] = (min(cur[0], st), max(cur[1], en)) if cur else (st, en)
    filled = _fill(times, t0, t1)
    return [{"word": " " + w, "start": round(st, 3), "end": round(en, 3)} for w, (st, en) in zip(shown, filled)]


def segments(data: dict) -> list[tuple[str, str, float, float]]:
    """(ad, seslenen metn, baslangic, son) - tts_gen-in yazdigi ardicilliqla."""
    texts = data.get("card_texts") or {}
    t = float(data["intro_seconds"])
    out = [("intro", texts.get("intro", ""), 0.0, t)]
    for i, s in enumerate(data["scenes"], 1):
        d = float(s["duration"])
        title = s.get("spoken_title")
        out.append((f"sc{i:02d}", (f"{title}. " if title else "") + s["narration"], t, t + d))
        t += d
    out.append(("outro", texts.get("outro", ""), t, t + float(data["outro_seconds"])))
    return out


def _in(w: dict, t0: float, t1: float) -> bool:
    mid = (float(w["start"]) + float(w["end"])) / 2
    return t0 <= mid < t1


def _values(text: str) -> list[float]:
    return [v for s, e, v in find_numbers(text) if text[s:e].lower() not in ("one", "a")]


def _missing(script: str, heard: str) -> list[float]:
    got = _values(heard)
    return [v for v in _values(script) if not any(math.isclose(v, g, rel_tol=1e-9, abs_tol=1e-6) for g in got)]


def build_captions(data: dict, whisper: list[dict]) -> tuple[list[dict], dict]:
    words: list[dict] = []
    report: dict = {"segments": {}}
    for name, text, t0, t1 in segments(data):
        if not text.strip():
            continue
        heard = [w for w in whisper if _in(w, t0, t1)]
        words += align_segment(text, heard, t0, t1)
        missing = _missing(to_display(text), "".join(w["word"] for w in heard))
        if missing:
            report["segments"][name] = {"missing_numbers": missing,
                                        "heard": "".join(w["word"] for w in heard).strip()[:300]}
    return words, report


def number_problems(report: dict) -> list[str]:
    return [f"{name}: ssenarideki {', '.join(f'{v:g}' for v in r['missing_numbers'])} seste esidilmedi "
            f"(whisper: {r['heard'][:120]!r})" for name, r in (report.get("segments") or {}).items()]


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(words: list[dict]) -> str:
    blocks, cur = [], []
    for w in words:
        cur.append(w)
        text = " ".join(x["word"].strip() for x in cur)
        too_long = len(text) > MAX_CHARS or cur[-1]["end"] - cur[0]["start"] > MAX_DUR
        if too_long and len(cur) > 1:
            blocks.append(cur[:-1])
            cur = [w]
        elif w["word"].rstrip().endswith((".", "?", "!")):
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return "".join(f"{i}\n{_ts(b[0]['start'])} --> {_ts(b[-1]['end'])}\n"
                   f"{' '.join(x['word'].strip() for x in b)}\n\n" for i, b in enumerate(blocks, 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    a = ap.parse_args()
    ep = a.episode_dir
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(ep, "narration.words.json"), encoding="utf-8") as f:
        whisper = json.load(f)
    words, report = build_captions(data, whisper)
    with open(os.path.join(ep, "captions.words.json"), "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ep, "captions.srt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(to_srt(words))
    report["problems"] = number_problems(report)
    qa_stamp.write(ep, "captions_qa.json", report)          # Faza 5.3: skriptin sha256-si ile
    print(f"[captions] {len(words)} soz, reqem problemi: {len(report['problems'])}")
    for p in report["problems"]:
        print("  ", p)


if __name__ == "__main__":
    main()
