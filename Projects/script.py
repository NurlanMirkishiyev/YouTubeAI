"""Ssenari .md -> basliq + bolmeler -> sehneler. Ssenari YOXLANMIR, metn sozbesoz qalir (yalniz ** * --- silinir).
Iki format: (A) **NARRATION:** / **VISUAL:** isareli istehsal ssenarisi; (B) sade metn (her abzas danisiqdir).
Qayda: VISUAL narrasiyani BITIRMIR (sonrakı VISUAL davam bolmesi acir, cont=True). Narrasiya baslayandan sonra
yalniz VISUAL/NARRATION label-dir; qalan her **X:** setri danisiq metnidir."""
from __future__ import annotations

import os
import re

TIMECODE = re.compile(r"^\s*\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}\s*[—–-]\s*")
LABEL = re.compile(r"^\*\*\s*([A-Za-z ]+?)\s*:\s*\*\*\s*(.*)$")     # **VISUAL:** text
MARKED = re.compile(r"^\s*\*\*\s*NARRATION\s*:\s*\*\*", re.M | re.I)  # **NARRATION:** label
BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")                       # "- ", "* ", "1. "
TABLE_SEP = re.compile(r"^[\s|:\-]+$")                               # |---|:--| ayirici setr
SENTENCE = re.compile(r"(?:(?<=[.!?…])|(?<=[.!?…][\"”’)]))\s+(?=[\"“‘(]?[A-Z0-9$])")


def clean(text: str) -> str:
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)
    return " ".join(text.split())


def _is_item(block: str) -> bool:
    return block.startswith("|") or bool(BULLET.match(block))


def _item(block: str) -> str:
    """Siyahi/cədvəl setri -> mətn (marker silinir, cədvəl hüceyrələri vergüllə). Ayirici setr -> ''."""
    if block.startswith("|"):
        if TABLE_SEP.match(block):
            return ""
        cells = [c.strip() for c in block.strip("|").split("|")]
        return clean(", ".join(c for c in cells if c))
    return clean(BULLET.sub("", block, count=1))


def _blocks(lines: list[str]) -> list[str]:
    """Ardicil mətn setrləri bir blok; boş setr / --- bloku bitirir; siyahi və cədvəl setri ayrı blokdur."""
    out: list[str] = []
    cur: list[str] = []

    def flush() -> None:
        if cur:
            out.append(" ".join(cur))
            cur.clear()
    for ln in lines:
        s = ln.strip()
        if not s or s == "---":
            flush()
        elif _is_item(s):
            flush()
            out.append(s)
        else:
            cur.append(s)
    flush()
    return out


def _read_section(name: str, body: list[str], marked: bool) -> list[dict]:
    """Bir bolmenin setrlerini oxuyur. VISUAL narrasiyadan sonra gelsə davam bolmesi (cont) acilir."""
    secs = [{"name": name, "visual": "", "paragraphs": []}]
    started = not marked                       # narrasiya bu bolmede baslayib (plain mode: hemise)
    for b in _blocks(body):
        m = LABEL.match(b)
        label = m.group(1).upper() if m else ""
        cur = secs[-1]
        if label == "VISUAL":
            text = clean(m.group(2))
            if started and cur["paragraphs"]:
                cur = {"name": name, "visual": text, "paragraphs": [], "cont": True}
                secs.append(cur)
            else:
                cur["visual"] = text
        elif label == "NARRATION":
            started = True
            if m.group(2).strip():
                cur["paragraphs"].append(clean(m.group(2)))
        elif not started:
            continue                           # NARRATION-dan evvel: meta (**Format:** ...) ve s. atilir
        elif _is_item(b):
            if _item(b):
                cur["paragraphs"].append(_item(b))
        else:
            cur["paragraphs"].append(clean(b))  # narrasiya daxilində hər **X:** setri danisiqdir
    return [s for s in secs if s["paragraphs"]]


def parse(markdown: str, fallback_title: str) -> dict:
    lines = markdown.replace("\r\n", "\n").split("\n")
    title, heads = "", []                      # heads: [(name, [lines])]
    pre: list[str] = []
    for ln in lines:
        if ln.startswith("# ") and not title:
            title = clean(ln[2:])
        elif ln.startswith("## "):
            heads.append((clean(TIMECODE.sub("", ln[3:])), []))
        elif heads:
            heads[-1][1].append(ln)
        else:
            pre.append(ln)
    marked = bool(MARKED.search(markdown))
    sections: list[dict] = []
    if not marked:
        sections += _read_section("", pre, marked=False)
    for name, body in heads:
        sections += _read_section(name, body, marked)
    return {"title": title or fallback_title, "sections": sections}


def _sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in SENTENCE.split(paragraph) if s.strip()]


def split_scenes(sections: list[dict], max_words: int = 40) -> list[dict]:
    scenes: list[dict] = []
    for sec in sections:
        cur: list[str] = []
        first = not sec.get("cont", False)     # davam bolmesinin 1-ci sehnesi bolme basi deyil

        def flush() -> None:
            nonlocal cur, first
            if cur:
                scenes.append({"n": len(scenes) + 1, "section": sec["name"], "section_start": first,
                               "visual": sec["visual"], "text": " ".join(cur), "type": None,
                               "photo_prompt": "", "owl": "", "anim": None, "duration": 0.0})
                cur, first = [], False
        for para in sec["paragraphs"]:
            for s in _sentences(para):
                if cur and len(" ".join(cur + [s]).split()) > max_words:
                    flush()
                cur.append(s)
        flush()
    return scenes


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower().replace("’", "").replace("'", "")).strip("-")[:80]


def build(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        parsed = parse(f.read(), os.path.splitext(os.path.basename(path))[0])
    slug = slugify(parsed["title"]) or slugify(os.path.splitext(os.path.basename(path))[0]) or "video"
    return {"title": parsed["title"], "slug": slug,
            "scenes": split_scenes(parsed["sections"])}
