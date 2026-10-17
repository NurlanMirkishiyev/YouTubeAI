"""Ssenari .md -> basliq + bolmeler -> sehneler. Ssenari YOXLANMIR, metn sozbesoz qalir (yalniz ** * --- silinir).
Format ne olursa olsun yalniz danisiq oxunur. Her blok tesnif olunur:
  - danisiq etiketi (NARRATION / Voiceover / VO / Narrator / Script ...) -> narrasiya baslayir;
  - rejissor etiketi (VISUAL(S) / On-screen text / B-roll / SFX / Camera / [..] / (..) ...) -> oxunmur;
  - meta etiket (Format / Language / Thumbnail ...) ve meta bolmeler (Video title / Thumbnail idea / Editing /
    Production notes / Core takeaway ...) -> oxunmur.
Etiket istenilen formada ola biler: **X:** metn, **X**: metn, tek setrde **X**, ### X, X: metn (yalniz taninan X).
Danisiq etiketi olan ssenaride (A) yalniz etiketden sonraki metn oxunur; etiketsiz ssenaride (B) her abzas danisiqdir.
VISUAL narrasiyani BITIRMIR (sonraki VISUAL davam bolmesi acir, cont=True). Narrasiya daxilinde taninmayan **X:**
setri danisiq metnidir. suspicious() qalan rejissor qeydine oxsar cumleleri gosterir (yalniz xeberdarliq)."""
from __future__ import annotations

import os
import re

TIMECODE = re.compile(r"^\s*\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}\s*[—–-]\s*")
TIMECODE_END = re.compile(r"\s*[(\[]\s*\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}\s*[)\]]\s*$")
SCENE_NO = re.compile(r"^(?:scene|part|chapter|section|segment|act|step)\s*#?\s*\d+\s*(?:[—–:.-]\s*|$)", re.I)
BOLD_LABEL = re.compile(r"^\*\*\s*([^*:\n]{1,40}?)\s*(?::\s*\*\*|\*\*\s*:|\*\*)\s*(.*)$")   # **X:** / **X**: / **X**
HEAD_LABEL = re.compile(r"^#{3,6}\s*(.+?)\s*:?\s*$")                                     # ### X
PLAIN_LABEL = re.compile(r"^([A-Za-z][A-Za-z .\-/’']{0,30}?)\s*:\s*(.*)$")              # X: metn
BRACKETED = re.compile(r"^(?:\[[^\[\]]*\]|\([^()]*\))$")                                 # [Cut to ...] / (Music)
BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")                       # "- ", "* ", "1. "
TABLE_SEP = re.compile(r"^[\s|:\-]+$")                               # |---|:--| ayirici setr
SENTENCE = re.compile(r"(?:(?<=[.!?…])|(?<=[.!?…][\"”’)]))\s+(?=[\"“‘(]?[A-Z0-9$])")
QUOTED = re.compile(r"[“\"]([^”\"]{2,60})[”\"]")

SPEECH = {"narration", "narrator", "voiceover", "voice over", "vo", "script", "host", "dialogue", "speaker",
          "spoken text", "narration text", "voiceover text", "read"}
VISUAL = {"visual", "visuals", "b roll", "broll", "footage", "stock footage", "shot", "shots", "camera", "scene",
          "illustration", "scene description", "setting", "image", "images"}
DIRECTION = VISUAL | {
    "on screen text", "onscreen text", "on screen", "screen text", "text on screen", "text", "sfx", "sound",
    "sound effect", "sound effects", "music", "graphics", "graphic", "motion graphics", "animation", "animations",
    "transition", "cut to", "note", "notes", "editor note", "editors note", "director note", "direction",
    "directions", "stage direction", "visual direction", "visual directions", "visual notes", "visual note", "lower third", "caption", "captions", "title card", "end card", "overlay",
    "cue", "visual cue", "pause", "beat"}
META = {"format", "language", "target runtime", "runtime", "narration language", "visual identity", "duration",
        "tone", "audience", "target audience", "thumbnail", "thumbnail idea", "thumbnail text", "video title",
        "title", "tags", "description", "keywords", "style", "length", "word count", "pacing", "cta"}
META_SECTION = re.compile(r"\bvideo title\b|^title$|thumbnail|editing|production|^notes?\b|\bnotes$|visual plan|"
                          r"shot list|b-?roll list|description|^tags\b|keywords|\bseo\b|references|^sources\b|"
                          r"takeaway|end screen", re.I)
DIRECTION_START = re.compile(r"^(?:cut to|fade (?:in|out|to)|zoom (?:in|out|to)|pan (?:to|across)|on-?screen|"
                             r"animate|b-?roll|sfx\b|transition to)", re.I)


def clean(text: str) -> str:
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)
    return " ".join(text.split())


def _norm(name: str) -> str:
    """'NARRATOR (V.O.)' / '[VOICEOVER]' / 'Voiceover 2' -> 'narrator' / 'voiceover' / 'voiceover'."""
    bare = re.sub(r"[(\[][^()\[\]]*[)\]]", " ", name)
    name = (bare if bare.strip() else name.strip("[]() ")).lower()
    name = re.sub(r"\s*#?\d+\s*$", "", name)
    name = name.replace(".", "").replace("’", "").replace("'", "")
    return " ".join(re.sub(r"[-_/]", " ", name).split())


def label(block: str) -> tuple[str, str, str]:
    """Blok -> (nov, ad, qalan metn). nov: speech | direction | meta | heading (taninmayan ###) | '' (adi metn)."""
    if BRACKETED.match(block):
        return "direction", "", ""
    m = HEAD_LABEL.match(block)
    if m:
        name = _norm(m.group(1))
        return _kind(name) or "heading", name, ""
    for rx in (BOLD_LABEL, PLAIN_LABEL):
        m = rx.match(block)
        if m:
            name = _norm(m.group(1))
            if _kind(name):
                return _kind(name), name, m.group(2).strip()
    return "", "", block


def _kind(name: str) -> str:
    return "speech" if name in SPEECH else "direction" if name in DIRECTION else "meta" if name in META else ""


def section_name(raw: str) -> str:
    name = TIMECODE_END.sub("", TIMECODE.sub("", raw))
    return clean(SCENE_NO.sub("", name.strip()))


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
    """Ardicil mətn setrləri bir blok; boş setr / --- bloku bitirir; siyahi, cədvəl, etiket ve ### setri ayrı blokdur."""
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
        elif _is_item(s) or s.startswith("#") or label(s)[0]:
            flush()
            out.append(s)
        else:
            cur.append(s)
    flush()
    return out


def _set_visual(secs: list[dict], name: str, text: str, started: bool) -> None:
    cur = secs[-1]
    if started and cur["paragraphs"]:
        secs.append({"name": name, "visual": text, "paragraphs": [], "cont": True})
    else:
        cur["visual"] = f"{cur['visual']} {text}".strip()


def _read_section(name: str, body: list[str], marked: bool) -> list[dict]:
    """Bir bolmenin setrlerini oxuyur. VISUAL narrasiyadan sonra gelse davam bolmesi (cont) acilir."""
    secs = [{"name": name, "visual": "", "paragraphs": []}]
    speaking = not marked                      # etiketsiz ssenaride her abzas danisiqdir
    started = False                            # bu bolmede danisiq baslayib
    held = ""                                  # tek setrlik rejissor etiketi (**Visuals**) -> novbeti bloklar onundur
    for b in _blocks(body):
        kind, lab, rest = label(b)
        if kind == "speech":
            speaking, held, started = True, "", True
            if rest:
                secs[-1]["paragraphs"].append(clean(rest))
            continue
        if kind in ("meta", "heading"):
            continue
        if kind == "direction":
            if rest:
                if lab in VISUAL:
                    _set_visual(secs, name, clean(rest), started)
            elif lab:
                held = lab
                if marked:
                    speaking = False
            continue
        if held:                               # etiketli ssenaride novbeti danisiq etiketine qeder, etiketsizde 1 blok
            if held in VISUAL:
                _set_visual(secs, name, clean(b), started)
            if not marked:
                held = ""
            continue
        if not speaking:
            continue                           # danisiq etiketinden evvel / rejissor bloku daxilinde
        text = _item(b) if _is_item(b) else clean(b)
        if text:
            secs[-1]["paragraphs"].append(text)  # narrasiya daxilinde taninmayan **X:** setri danisiqdir
            started = True
    for i in range(len(secs) - 1, 0, -1):       # bolmenin sonundaki VISUAL (Voiceover formati) bolmenin ozunundur
        if not secs[i]["paragraphs"] and secs[i].get("cont") and not secs[i - 1]["visual"]:
            secs[i - 1]["visual"] = secs[i]["visual"]
    return [s for s in secs if s["paragraphs"]]


def _section_text(body: list[str]) -> str:
    return " ".join(clean(_item(b) if _is_item(b) else b) for b in _blocks(body)).strip()


def parse(markdown: str, fallback_title: str) -> dict:
    lines = markdown.replace("\r\n", "\n").split("\n")
    title, heads = "", []                      # heads: [(name, [lines])]
    pre: list[str] = []
    for ln in lines:
        if ln.startswith("# ") and not title:
            title = clean(ln[2:])
        elif ln.startswith("## "):
            heads.append((ln[3:].strip(), []))
        elif heads:
            heads[-1][1].append(ln)
        else:
            pre.append(ln)
    marked = any(label(b)[0] == "speech" for b in _blocks(lines))
    out = _parse(title, pre, heads, marked, fallback_title)
    if marked and not out["sections"]:        # etiketler danisiq vermedi -> etiketsiz kimi oxunur (video dayanmir)
        out = _parse(title, pre, heads, False, fallback_title)
    return out


def _parse(title: str, pre: list[str], heads: list, marked: bool, fallback_title: str) -> dict:
    sections: list[dict] = []
    video_title, idea, idea_text = "", "", ""
    if not marked:
        sections += _read_section("", pre, marked=False)
    for raw, body in heads:
        name = section_name(raw)
        if META_SECTION.search(clean(raw)):
            low = _norm(clean(raw))
            if low in ("video title", "title") and not video_title:
                video_title = next((clean(b) for b in _blocks(body)), "")
            elif "thumbnail" in low and not idea:
                idea = _section_text(body)
                q = QUOTED.search("\n".join(body))
                idea_text = clean(q.group(1)) if q else ""
            continue
        sections += _read_section(name, body, marked)
    return {"title": video_title or title or fallback_title, "sections": sections,
            "thumbnail_idea": idea, "thumbnail_text": idea_text}


def suspicious(scenes: list[dict]) -> list[tuple[int, str]]:
    """Narrasiyada qalan rejissor qeydine oxsar cumleler (n, cumle). Yalniz xeberdarliq - video dayanmir."""
    out = []
    for s in scenes:
        for sent in _sentences(s["text"]):
            kind = label(sent)[0]
            if kind in ("direction", "meta", "speech") or DIRECTION_START.match(sent):
                out.append((s["n"], sent))
    return out


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
    return {"title": parsed["title"], "slug": slug, "scenes": split_scenes(parsed["sections"]),
            "thumbnail_idea": parsed["thumbnail_idea"], "thumbnail_text": parsed["thumbnail_text"]}
