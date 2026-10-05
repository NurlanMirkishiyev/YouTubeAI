"""Reyestr #54 (istifadeci 2026-10-05): reqemlerin ses ve altyazi formasi.
- to_speech: TTS-e gedecek metn - "$4,000" -> "four thousand dollars", "15%" -> "fifteen percent", ilin
  oxunusu ("2023" -> "twenty twenty-three"). Kokoro reqemi ozu oxuyanda "$9.99", "1994-2020" sehv oxunurdu.
- to_display: altyazi metni - pul/faiz ve >= 10 sozle yazilan reqemler "$4,000" / "15%" / "2,500" formasina.
Ikisi de saf funksiyadir; TTS venv-de de islemelidir (yalniz num2words + math_check).
"""
from __future__ import annotations

import re

from num2words import num2words

from math_check import find_numbers

_SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "k": 1e3, "m": 1e6, "bn": 1e9}
_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_MONEY = re.compile(rf"\$({_NUM})(?:\s?(thousand|million|billion)\b|(k|m|bn)\b)?", re.I)
_PERCENT = re.compile(rf"({_NUM})\s?%")
_RANGE_YEARS = re.compile(r"\b((?:19|20)\d\d)\s?[-–]\s?((?:19|20)\d\d)\b")
# cumle sonundaki "in 2023." da ildir - noqte/vergul yalniz ardinca reqem gelende (2023.5, 2,023) il deyil
_YEAR = re.compile(r"(?<![\d$])(?<![\d][,.])\b((?:19|20)\d\d)\b(?![\d%]|[,.]\d)")
_TIMES = re.compile(rf"\b({_NUM})x\b")
_ORDINAL = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b")
_PLAIN = re.compile(rf"(?<![\w$.,])({_NUM})(?![\w%])")


def _words(value: float) -> str:
    """1.5 -> 'one point five', 2500 -> 'two thousand five hundred' (and-siz, ABS ingiliscesi)."""
    text = num2words(int(value)) if float(value).is_integer() else num2words(value)
    return text.replace(" and ", " ").replace(",", "")


def _value(raw: str) -> float:
    return float(raw.replace(",", ""))


def _money(m: re.Match) -> str:
    raw, scale_word, scale_short = m.group(1), m.group(2), m.group(3)
    scale = (scale_word or scale_short or "").lower()
    value = _value(raw)
    if scale:
        if scale_word:
            return f"{_words(value)} {scale} dollars"
        return f"{_words(value * _SCALES[scale])} dollars"
    dollars, cents = int(value), round((value - int(value)) * 100)
    if dollars == 0 and cents:
        return f"{_words(cents)} cent{'s' if cents != 1 else ''}"
    text = f"{_words(dollars)} dollar{'s' if dollars != 1 else ''}"
    return text + (f" and {_words(cents)} cent{'s' if cents != 1 else ''}" if cents else "")


def to_speech(text: str) -> str:
    text = _RANGE_YEARS.sub(lambda m: f"{m.group(1)} to {m.group(2)}", text)
    text = _MONEY.sub(_money, text)
    text = _PERCENT.sub(lambda m: f"{_words(_value(m.group(1)))} percent", text)
    text = _TIMES.sub(lambda m: f"{_words(_value(m.group(1)))} times", text)
    text = _ORDINAL.sub(lambda m: num2words(int(m.group(1)), to="ordinal"), text)
    text = _YEAR.sub(lambda m: num2words(int(m.group(1)), to="year"), text)
    return _PLAIN.sub(lambda m: _words(_value(m.group(1))), text)


_AFTER_MONEY = re.compile(r"\s+dollars?\b(?:\s+and\s+\w+(?:-\w+)?\s+cents?\b)?", re.I)
_AFTER_CENTS = re.compile(r"\s+cents?\b", re.I)
_AFTER_PERCENT = re.compile(r"\s*(?:%|per\s?cent\b)", re.I)
_SPELLED_MIN = 10         # "three steps" sozle qalir, "twenty-three" -> "23"


def _fmt(value: float, money: bool = False) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}" if money else f"{value:,.6f}".rstrip("0")


def _is_year(span: str) -> bool:
    return bool(re.fullmatch(r"(?:19|20)\d\d", span))


def to_display(text: str) -> str:
    """Altyazi: pul -> "$4,000", faiz -> "15%", boyuk reqem -> "2,500"; il ve kicik sozle reqem toxunulmur."""
    out, last = [], 0
    for start, end, value in find_numbers(text):
        if start < last:
            continue
        span = text[start:end]
        before = text[start - 1:start]
        money = _AFTER_MONEY.match(text, end)
        cents = _AFTER_CENTS.match(text, end) and "cent" not in span.lower()
        percent = _AFTER_PERCENT.match(text, end)
        spelled = not any(ch.isdigit() for ch in span)
        if not spelled and any(ch.isalpha() for ch in span):
            continue                                # "1.5 million" oldugu kimi qalir
        if "cent" in span.lower() or "dollar" in span.lower():
            new, stop = f"${_fmt(value, money=True)}", end
        elif money and before != "$":
            new, stop = f"${_fmt(value, money=True)}", money.end()
        elif cents:
            new, stop = f"${_fmt(value / 100, money=True)}", cents.end()
        elif percent and spelled:
            new, stop = f"{_fmt(value)}%", percent.end()
        elif before == "$":
            new, stop = _fmt(value, money=True), end
        elif (not spelled and not _is_year(span)) or (spelled and value >= _SPELLED_MIN):
            new, stop = _fmt(value), end
        else:
            continue
        out.append(text[last:start])
        out.append(new)
        last = stop
    out.append(text[last:])
    return "".join(out)
