"""Ekrandaki animasiya YALNIZ sehne danisigindan: her reqem danisiqda yazilan ve ya sozle deyilen deyerdir, her yazi
parcasinin sozleri danisiqda var. Uygun gelmese None -> plan quote (danisiqdan cumle) gosterir. Ssenari yoxlanmir."""
from __future__ import annotations

import re

KINDS = ("counter", "bars", "percent", "flow", "list", "versus", "timeline", "quote")
SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
DIGITS = re.compile(r"(\d[\d,]*(?:\.\d+)?)(?:\s*(thousand|million|billion|trillion)\b)?", re.I)
WORD = re.compile(r"[a-z]+(?:-[a-z]+)?", re.I)
MAX_ITEMS = 4
MAX_PHRASE_WORDS = 7
# Remotion/src/anim/Icon.tsx ile eyni siyahi. Ikon yazi deyil - menaya uygun simvoldur (grounding teleb etmir).
ICONS = ("money", "coin", "chart-up", "chart-down", "users", "user", "phone", "cart", "bag", "tag", "crown",
         "diamond", "star", "clock", "calendar", "globe", "building", "factory", "bulb", "target", "shield",
         "heart", "lock", "gift", "rocket", "megaphone", "check", "warning", "scale", "gear", "truck", "store",
         "brain", "eye", "handshake", "spark")


def _spoken(text: str) -> set[float]:
    out: set[float] = set()
    total = cur = 0.0
    seen = False
    for w in [t.lower() for t in WORD.findall(text)] + ["."]:
        parts = w.split("-")
        if all(p in UNITS or p in TENS for p in parts):
            cur += sum(UNITS.get(p, TENS.get(p, 0)) for p in parts)
            seen = True
        elif w == "hundred" and seen:
            cur = (cur or 1) * 100
        elif w in SCALES and seen:
            if cur:
                out.add(cur)                    # "twenty thousand" -> 20 de (reqemle yazilanda oldugu kimi)
            total += (cur or 1) * SCALES[w]
            cur = 0.0
        elif w == "a" and not seen:
            continue
        else:
            if seen:
                out.add(total + cur)
            total = cur = 0.0
            seen = False
    return out


def numbers_in(text: str) -> set[float]:
    out = set()
    for m in DIGITS.finditer(text):
        v = float(m.group(1).replace(",", ""))
        out.add(v)
        if m.group(2):
            out.add(v * SCALES[m.group(2).lower()])
    return out | _spoken(text)


def _near(a: float, nums: set[float]) -> bool:
    return any(abs(a - n) <= 1e-6 * max(1.0, abs(n)) for n in nums)


def dollar_amounts(text: str) -> set[float]:
    """Dollar meblegleri: $5, $201 billion, five dollars, 201 billion dollars."""
    out = {float(m.group(1).replace(",", "")) for m in re.finditer(r"\$\s*(\d[\d,]*(?:\.\d+)?)", text)}
    for m in re.finditer(r"\bdollars?\b", text, re.I):
        before = re.split(r"[.!?;:,]", text[:m.start()])[-1].split()[-5:]
        out |= numbers_in(" ".join(before))
    return out


def _stem(w: str) -> str:
    return w.lower().rstrip("s")


def words_ok(label: str, text: str) -> bool:
    have = {_stem(w) for w in re.findall(r"[A-Za-z]+", text)}
    words = [w for w in re.findall(r"[A-Za-z]+", label) if len(w) >= 3]
    fits = len(label.split()) <= MAX_PHRASE_WORDS          # ekranda sigsin
    return bool(label.strip()) and fits and all(_stem(w) in have for w in words)


def _num(x) -> float | None:
    try:
        return float(str(x).replace(",", "").replace("$", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _num_ok(x, nums: set[float]) -> float | None:
    v = _num(x)
    return v if v is not None and _near(v, nums) else None


def _strs(xs, text: str) -> list[str] | None:
    if not isinstance(xs, list):
        return None
    xs = [str(x).strip() for x in xs][:MAX_ITEMS]
    return xs if len(xs) >= 2 and all(words_ok(x, text) for x in xs) else None


def validate(spec: dict, text: str) -> dict | None:
    out = _validate(spec, text)
    if not out or out["kind"] == "quote":
        return out
    if spec.get("icon") in ICONS:
        out["icon"] = spec["icon"]
    items = out.get("steps") or out.get("items") or out.get("events") or (
        [out["left"], out["right"]] if out["kind"] == "versus" else None)
    icons = spec.get("icons")
    if isinstance(items, list) and isinstance(icons, list) and len(icons) >= len(items)             and all(i in ICONS for i in icons[:len(items)]):
        out["icons"] = icons[:len(items)]
    return out


def _validate(spec: dict, text: str) -> dict | None:
    if not isinstance(spec, dict) or spec.get("kind") not in KINDS:
        return None
    kind, nums = spec["kind"], numbers_in(text)
    if kind == "counter":
        v = _num_ok(spec.get("value"), nums)
        label = str(spec.get("label", "")).strip()
        raw = str(spec.get("suffix", "")).strip()
        norm = raw if raw in ("", "%") else " " + raw
        suffix = norm if norm in ("", "%", " thousand", " million", " billion") else ""
        if v is not None and suffix.strip() in SCALES and not _near(v * SCALES[suffix.strip()], nums):
            suffix = ""                         # miqyas sozu danisiqda bu reqemle deyilmeyib
        prefix = "$" if spec.get("prefix") == "$" and v is not None and _near(v, dollar_amounts(text)) else ""
        return ({"kind": kind, "value": v, "prefix": prefix, "suffix": suffix, "label": label}
                if v is not None and words_ok(label, text) else None)
    if kind == "percent":
        v = _num_ok(spec.get("value"), nums)
        label = str(spec.get("label", "")).strip()
        return {"kind": kind, "value": v, "label": label} if v is not None and 0 <= v <= 100 and words_ok(label, text) else None
    if kind == "bars":
        items = spec.get("items") if isinstance(spec.get("items"), list) else []
        good = [{"label": str(i.get("label", "")).strip(), "value": _num_ok(i.get("value"), nums)}
                for i in items[:MAX_ITEMS] if isinstance(i, dict)]
        good = [i for i in good if i["value"] is not None and words_ok(i["label"], text)]
        return {"kind": kind, "items": good} if len(good) >= 2 and len(good) == len(items[:MAX_ITEMS]) else None
    if kind in ("flow", "list", "timeline"):
        key = {"flow": "steps", "list": "items", "timeline": "events"}[kind]
        xs = _strs(spec.get(key), text)
        return {"kind": kind, key: xs} if xs else None
    if kind == "versus":
        left, right = str(spec.get("left", "")).strip(), str(spec.get("right", "")).strip()
        return {"kind": kind, "left": left, "right": right} if words_ok(left, text) and words_ok(right, text) else None
    q = str(spec.get("text", "")).strip()
    inner = q.rstrip("…").strip()
    return {"kind": "quote", "text": q} if inner and inner in text else None


def quote_for(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    short = [s for s in sentences if len(s.split()) <= 16]
    if short:
        return {"kind": "quote", "text": max(short, key=len)}
    words = list(re.finditer(r"\S+", text))
    end = words[min(13, len(words) - 1)].end() if words else 0
    return {"kind": "quote", "text": text[:end] + "…"}


ENUM_MAX_WORDS = 6


def enumeration(text: str) -> dict | None:
    """Danisiqdaki sadalama ("pay engineers, maintain servers, and keep everything working") -> sozbesoz list.
    Birinci elementin uzunlugu diger elementlerin en qisasi qeder (cumlenin evvelindeki "Companies have to" atilir)."""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        parts = [p.strip() for p in sentence.rstrip(".!?…").split(",")]
        if len(parts) < 3:
            continue
        rest = [re.sub(r"^(?:and|or)\s+", "", p, flags=re.I) for p in parts[1:]]
        if not all(rest) or any(len(p.split()) > ENUM_MAX_WORDS for p in rest):
            continue
        n = min(len(p.split()) for p in rest)
        items = [" ".join(parts[0].split()[-n:])] + rest
        spec = {"kind": "list", "items": items[:MAX_ITEMS]}
        if validate(spec, text):
            return spec
    return None

