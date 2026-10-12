"""Yalniz TTS ucun telaffuz: reqemler ingilis sozlerine. Ekran/altyazi metni deyismir."""
from __future__ import annotations

import re

from num2words import num2words

NUM = r"\d+(?:,\d{3})*(?:\.\d+)?"
DECADE = re.compile(r"\b(\d*0)s\b")
ORDINAL = re.compile(r"\b(\d+)(st|nd|rd|th)\b")
LETTER_EDGE = re.compile(r"(?<=\d)(?=[A-Za-z])|(?<=[A-Za-z])(?=\d)")
MONEY = re.compile(r"\$(" + NUM + r")(\s*(?:thousand|million|billion|trillion))?")
PERCENT = re.compile(r"(" + NUM + r")\s?%")
NUMBER = re.compile(NUM)
CENTS = re.compile(r"\d+(?:,\d{3})*\.\d{2}")


def _cardinal(raw: str) -> str:
    """'1,234.50' -> 'one thousand two hundred and thirty-four point five zero' (fraction digit by digit)."""
    clean = raw.replace(",", "")
    if "." not in clean:
        return num2words(int(clean))
    whole, frac = clean.split(".")
    return f"{num2words(int(whole))} point " + " ".join(num2words(int(d)) for d in frac)


def _number(m: re.Match) -> str:
    raw = m.group(0)
    if re.fullmatch(r"(19|20)\d\d", raw):
        return num2words(int(raw), to="year")
    return _cardinal(raw)


def _decade(m: re.Match) -> str:
    n = int(m.group(1))
    words = num2words(n, to="year") if 1900 <= n <= 2099 else num2words(n)
    return words[:-1] + "ies" if words.endswith("y") else words + "s"


def _ordinal(m: re.Match) -> str:
    return num2words(int(m.group(1)), to="ordinal")


def _money(m: re.Match) -> str:
    raw, scale = m.group(1), m.group(2)
    if scale is None and CENTS.fullmatch(raw):
        whole, cents = raw.replace(",", "").split(".")
        dollars, cents_n = int(whole), int(cents)
        dollar_word = "dollar" if dollars == 1 else "dollars"
        cent_word = "cent" if cents_n == 1 else "cents"
        return f"{num2words(dollars)} {dollar_word} and {num2words(cents_n)} {cent_word}"
    if scale is None and raw.replace(",", "") == "1":
        return "one dollar"
    return f"{_cardinal(raw)}{scale or ''} dollars"


def to_speech(text: str) -> str:
    text = DECADE.sub(_decade, text)
    text = ORDINAL.sub(_ordinal, text)
    text = LETTER_EDGE.sub(" ", text)
    text = MONEY.sub(_money, text)
    text = PERCENT.sub(lambda m: f"{_cardinal(m.group(1))} percent", text)
    return NUMBER.sub(_number, text)
