"""Plan: sehnelerin 40%-i animasiya (beraber paylanmis), 60%-i foto. GPT her sehneye foto promptu, bayqus pozasi ve
animasiya teklifleri verir; animasiya yalniz danisiqdan (grounding), nov novbelesir. GPT xetasi -> VISUAL + quote (balans xetasi istisna: dayanir)."""
from __future__ import annotations

import json
import math
import re

import generate
import grounding
import llm

ANIM_SHARE = 0.40
KIND_CAP = 0.25
ROTATION = [k for k in grounding.KINDS if k != "quote"]

SYSTEM = """You plan visuals for an explainer video. For EVERY scene return:
- "photo_prompt": one realistic photograph (12-30 words) that shows what the narration and the section's VISUAL
  direction describe. Realistic documentary photo, natural light. No readable text, letters or logos in the photo.
  The owl mascot is drawn separately: NEVER put an owl, a mascot or a cartoon character in the photo - show real
  people and real objects instead. Every photo_prompt must be clearly different from every other scene of the
  video (different place, people, objects or camera angle) - never repeat or lightly reword an earlier prompt.
- "owl": what the cartoon owl presenter does in this scene (6-14 words): pose, expression and at most one prop that
  fits the narration. Every scene gets a different pose - never repeat a pose used in another scene.
- "anim": a list of 5 animation ideas of DIFFERENT kinds for this scene. At least 2 of them must be text kinds
  (flow, list, versus, timeline) built from narration words. Every label, step, item, event, left and right
  must be an EXACT fragment copied from that scene's narration (same words, same order, at most 7 words) - never paraphrase,
  summarise or add words that are not in the narration. When a scene has a "PREFERRED KIND" line, put that
  kind first if the narration supports it; otherwise best first. Use ONLY numbers and words
  that appear in the scene narration - never compute, round or invent. Kinds and fields:
  counter {value, prefix "$" or "", suffix "", "%", " thousand", " million" or " billion", label}
  bars {items: [{label, value}] 2-4}
  percent {value 0-100, label}
  flow {steps: [2-4 short phrases]}
  list {items: [2-4 short phrases]}
  versus {left, right}
  timeline {events: [2-4 short phrases]}
  Labels and phrases are 1-5 words copied from the narration.
Answer ONLY JSON: {"scenes": [{"n", "photo_prompt", "owl", "anim": [...]}]}"""


MASCOT = re.compile(r"\b(?:the|an|a)\s+(?:cartoon\s+)?owl(?:\s+mascot)?\b|\b(?:the|a)\s+mascot\b", re.I)


def photo_safe(prompt: str) -> str:
    """Bayqus ayrica qatdadir - fotoda bayqus / maskot olmur, yerine adi insan."""
    out = MASCOT.sub(lambda m: "A person" if m.group(0)[0].isupper() else "a person", prompt)
    return re.sub(r"\bowls?\b", "person", out, flags=re.I)


def _obj(**props) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_STR, _NUM = {"type": "string"}, {"type": "number"}
_STRS = {"type": "array", "items": _STR}


def _kind(name: str, **props) -> dict:
    return _obj(kind={"type": "string", "enum": [name]}, **props)


ANIM_SCHEMAS = [
    _kind("counter", value=_NUM, prefix={"type": "string", "enum": ["$", ""]},
          suffix={"type": "string", "enum": ["", "%", " thousand", " million", " billion"]}, label=_STR),
    _kind("bars", items={"type": "array", "items": _obj(label=_STR, value=_NUM)}),
    _kind("percent", value=_NUM, label=_STR),
    _kind("flow", steps=_STRS),
    _kind("list", items=_STRS),
    _kind("versus", left=_STR, right=_STR),
    _kind("timeline", events=_STRS),
]
SCHEMA = _obj(scenes={"type": "array", "items": _obj(
    n={"type": "integer"}, photo_prompt=_STR, owl=_STR, anim={"type": "array", "items": {"anyOf": ANIM_SCHEMAS}})})
BATCH_TRIES = 2


def ask_gpt(system: str, user: str) -> dict:
    return llm.chat_json(system, user, schema=SCHEMA, max_tokens=8000)


def assign_types(n: int) -> list[str]:
    return ["anim" if math.floor((i + 1) * ANIM_SHARE + 0.5) > math.floor(i * ANIM_SHARE + 0.5) else "photo"
            for i in range(n)]


def kind_order(i: int) -> list[str]:
    return ROTATION[i % len(ROTATION):] + ROTATION[:i % len(ROTATION)]


def pick_anim(candidates: list[dict], text: str, prev_kind: str | None, counts: dict[str, int], n_anim: int,
              variant: int) -> dict:
    cap = max(1, math.floor(n_anim * KIND_CAP))
    valid = [s for s in (grounding.validate(c, text) for c in candidates or [])
             if s and s["kind"] != "quote" and s["kind"] != prev_kind]
    for spec in valid:
        if counts.get(spec["kind"], 0) < cap:
            return {**spec, "variant": variant}
    if prev_kind == "quote" and valid:          # iki quote ardicil olmasin - limit bir defe asilir
        return {**valid[0], "variant": variant}
    enum = grounding.enumeration(text)          # danisiqdaki sadalama - sozbesoz list
    if enum and prev_kind != "list":
        return {**enum, "variant": variant}
    return {**grounding.quote_for(text), "variant": variant}


DEFAULT_POSES = [
    "standing and explaining with one wing raised, friendly", "thinking with a wing on the chin",
    "pointing to the side with a wing, excited", "holding a smartphone and looking at it, curious",
    "holding a small notebook and a pencil, focused", "shrugging with both wings open, playful",
    "giving a thumbs up with one wing, smiling", "holding a magnifying glass, investigating",
    "leaning forward with wings on the knees, attentive", "counting on the feathers of one wing, explaining",
    "holding a coffee mug, relaxed and smiling", "arms crossed confidently, smiling",
]
ANGLES = ["wide shot", "close-up", "over-the-shoulder view", "top-down view", "side view", "low-angle view",
          "candid moment", "shallow depth of field"]
USED_SHOWN = 40         # son N istifade olunmus photo/owl GPT-ye gosterilir


def _user(scenes: list[dict], title: str, preferred: dict[int, str] | None = None,
          notes: dict[int, str] | None = None, used: list[str] | None = None) -> str:
    parts = [f"VIDEO: {title}"]
    if used:
        parts.append("ALREADY USED in other scenes (photo prompts and owl poses must be clearly different):\n"
                     + "\n".join(f"- {u}" for u in used[-USED_SHOWN:]))
    for s in scenes:
        pref = f"\nPREFERRED KIND: {preferred[s['n']]}" if preferred and s["n"] in preferred else ""
        note = f"\n{notes[s['n']]}" if notes and s["n"] in notes else ""
        parts.append(f"SCENE {s['n']}: section={s['section']!r}\nVISUAL: {s['visual']}\nNARRATION: {s['text']}{pref}{note}")
    return "\n\n".join(parts)


def _rejected_note(cands: list) -> str:
    return ("REJECTED (contained words or numbers that are not in this narration - copy exact fragments instead): "
            + json.dumps(cands, ensure_ascii=False))


def _item(r) -> tuple[int, dict] | None:
    try:
        return int(r["n"]), r
    except (TypeError, ValueError, KeyError):
        return None


def _ask_batch(scenes: list[dict], title: str, ask, preferred: dict[int, str] | None = None,
               notes: dict[int, str] | None = None, used: list[str] | None = None) -> dict[int, dict]:
    for attempt in range(1, BATCH_TRIES + 1):
        try:
            res = ask(SYSTEM, _user(scenes, title, preferred, notes, used))
            pairs = (_item(r) for r in res.get("scenes", []))
            return dict(p for p in pairs if p)
        except Exception as e:  # noqa: BLE001 - plan ssenari sebebile dayanmir; balans xetasi istisnadir
            if llm.is_balance_error(e):
                raise
            print(f"  plan: GPT xetasi cehd {attempt} ({str(e)[:120]})", flush=True)
    print(f"  plan: sehne {scenes[0]['n']}-{scenes[-1]['n']} GPT cavab vermedi", flush=True)
    return {}


def _cands(r: dict) -> list:
    return r.get("anim") if isinstance(r.get("anim"), list) else []


def _grounded(cands: list, text: str) -> bool:
    return any((v := grounding.validate(c, text)) and v["kind"] != "quote" for c in cands)


def _repair(scenes: list[dict], types: list[str], got: dict[int, dict], title: str, ask,
            preferred: dict[int, str], batch: int) -> None:
    """Hec bir namizedi danisiqdan kecmeyen animasiya sehneleri reddin sebebi ile GPT-ye bir defe de verilir."""
    bad = [s for s, t in zip(scenes, types) if t == "anim" and not _grounded(_cands(got.get(s["n"], {})), s["text"])]
    if not bad:
        return
    rejected = {s["n"]: _cands(got.get(s["n"], {})) for s in bad}
    notes = {n: _rejected_note(c) for n, c in rejected.items()}
    for n, r in _ask_all(_chunks(bad, batch), title, ask, preferred, got, notes).items():
        got[n] = {**got.get(n, {}), "anim": _cands(r) + rejected[n]}
    print(f"  plan: {len(bad)} animasiya sehnesi redd sebebi ile yeniden soruldu", flush=True)


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", str(s).lower()).split())


def _used(got: dict[int, dict]) -> list[str]:
    out: list[str] = []
    for n in sorted(got):
        out += [f"photo: {got[n].get('photo_prompt', '')}", f"owl: {got[n].get('owl', '')}"]
    return out


def _chunks(scenes: list[dict], batch: int) -> list[list[dict]]:
    return [scenes[i:i + batch] for i in range(0, len(scenes), batch)]


def _ask_all(chunks: list[list[dict]], title: str, ask, preferred: dict[int, str], got: dict[int, dict],
             notes: dict[int, str] | None = None) -> dict[int, dict]:
    """Batch-lar ardicil; her batch evvelkilerin photo/owl-larini ALREADY USED kimi gorur."""
    out: dict[int, dict] = {}
    for chunk in chunks:
        wanted = {s["n"] for s in chunk}
        res = _ask_batch(chunk, title, ask, preferred, notes, _used({**got, **out}))
        out.update({n: r for n, r in res.items() if n in wanted})
    return out


def _duplicates(scenes: list[dict], got: dict[int, dict]) -> dict[int, str]:
    """Evvelki sehne ile eyni photo_prompt ve ya owl pozasi olan sehneler -> GPT ucun qeyd."""
    first: dict[str, int] = {}
    notes: dict[int, str] = {}
    for s in scenes:
        r = got.get(s["n"], {})
        for key in ("photo_prompt", "owl"):
            v = norm(r.get(key, ""))
            if not v:
                continue
            if f"{key}:{v}" in first:
                notes[s["n"]] = notes.get(s["n"], "DUPLICATE:") + (
                    f" your {key} repeats scene {first[f'{key}:{v}']} ({r[key]!r}) - write a clearly different one.")
            else:
                first[f"{key}:{v}"] = s["n"]
    return notes


def _dedupe(scenes: list[dict], got: dict[int, dict], title: str, ask, preferred: dict[int, str], batch: int) -> None:
    notes = _duplicates(scenes, got)
    if not notes:
        return
    dup = [s for s in scenes if s["n"] in notes]
    for n, r in _ask_all(_chunks(dup, batch), title, ask, preferred, got, notes).items():
        got[n] = {**got.get(n, {}), "photo_prompt": r.get("photo_prompt") or "", "owl": r.get("owl") or ""}
    print(f"  plan: {len(dup)} sehnenin tekrar foto/poza promptu yeniden yazildi", flush=True)


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[0].split()[:20]) if parts and parts[0] else ""


def unique_guard(scenes: list[dict]) -> None:
    """GPT-den sonra da bos / tekrar qalan photo_prompt: sehnenin oz VISUAL + ilk cumlesi (+ bucaq);
    owl: DEFAULT_POSES-dan istifade olunmayani."""
    seen_p: set[str] = set()
    seen_o: set[str] = set()
    for s in scenes:
        p = s.get("photo_prompt") or ""
        if not norm(p) or norm(p) in seen_p:
            base = photo_safe(f"{s.get('visual', '')} {_first_sentence(s.get('text', ''))}".strip())[:300]
            p, i = base, 0
            while norm(p) in seen_p:
                p = f"{base}, {ANGLES[i % len(ANGLES)]}" + (f" {i // len(ANGLES) + 1}" if i >= len(ANGLES) else "")
                i += 1
            s["photo_prompt"] = p
        seen_p.add(norm(p))
        o = s.get("owl") or ""
        if not norm(o) or norm(o) in seen_o:
            free = [x for x in DEFAULT_POSES if norm(x) not in seen_o]
            o = free[0] if free else f"{DEFAULT_POSES[len(seen_o) % len(DEFAULT_POSES)]}, variation {len(seen_o)}"
            s["owl"] = o
        seen_o.add(norm(o))


def plan_scenes(data: dict, ask=ask_gpt, batch: int = 6) -> dict:
    scenes = [dict(s) for s in data["scenes"]]
    types = assign_types(len(scenes))
    preferred: dict[int, str] = {}
    for s, t in zip(scenes, types):
        if t == "anim":
            preferred[s["n"]] = kind_order(len(preferred))[0]
    got = _ask_all(_chunks(scenes, batch), data["title"], ask, preferred, {})
    missing = [s for s in scenes if s["n"] not in got]
    if missing:
        print(f"  plan: GPT {len(missing)} sehneni buraxdi - yeniden sorusulur", flush=True)
        got.update(_ask_all(_chunks(missing, batch), data["title"], ask, preferred, got))
    _repair(scenes, types, got, data["title"], ask, preferred, batch)
    _dedupe(scenes, got, data["title"], ask, preferred, batch)
    n_anim, counts, prev, k = types.count("anim"), {}, None, 0
    for s, t in zip(scenes, types):
        r = got.get(s["n"], {})
        s["type"] = t
        s["photo_prompt"] = photo_safe(str(r.get("photo_prompt") or ""))[:400]
        s["owl"] = str(r.get("owl") or "")[:200]
        s["anim"] = None
        if t == "anim":
            cands = _cands(r)
            order = kind_order(k)
            cands = sorted(cands, key=lambda c: order.index(c["kind"]) if isinstance(c, dict) and c.get("kind") in order else 99)
            s["anim"] = pick_anim(cands, s["text"], prev, counts, n_anim, k % 2)
            counts[s["anim"]["kind"]] = counts.get(s["anim"]["kind"], 0) + 1
            prev, k = s["anim"]["kind"], k + 1
    unique_guard(scenes)
    return {**data, "scenes": scenes}


GREETING_MAX, FAREWELL_MAX = 16, 26
CTA = "Subscribe for more!"
BOOKEND_SYSTEM = """You write the INTRO and OUTRO lines spoken by the cartoon owl host of the YouTube channel
"ELI5 Business" (simple business explainers). Use the video title and its opening narration to stay on topic.
- "greeting": the owl greets the viewer, names the channel ELI5 Business and says what today's video is about
  (max 16 words, friendly, no numbers or facts that are not in the title or narration).
- "farewell": the owl thanks the viewer, says goodbye in a way that fits the topic and asks them to subscribe
  (max 26 words, must contain the word "subscribe").
- "bg_prompt": one realistic photograph (12-30 words) for the background of the intro and outro that fits the
  topic. No readable text, letters or logos. NEVER an owl, mascot or cartoon character.
- "owl_intro": the owl's pose for the greeting (6-14 words): waving hello, with at most one prop that fits the topic.
- "owl_outro": the owl's pose for the farewell (6-14 words): waving goodbye with one wing and pointing up with the
  other, smiling. No props, no buttons, no signs (the subscribe button is drawn separately).
Answer ONLY JSON."""
BOOKEND_SCHEMA = _obj(greeting=_STR, farewell=_STR, bg_prompt=_STR, owl_intro=_STR, owl_outro=_STR)


def ask_bookends(system: str, user: str) -> dict:
    return llm.chat_json(system, user, schema=BOOKEND_SCHEMA, max_tokens=800)


def _cap(text: str, limit: int) -> str:
    """Cumle serhedinde limit-e qeder kesir; birinci cumle de uzundursa ilk limit soz."""
    out: list[str] = []
    for sent in re.split(r"(?<=[.!?])\s+", " ".join(str(text).split())):
        if len(" ".join(out + [sent]).split()) > limit:
            break
        out.append(sent)
    return " ".join(out) if out else " ".join(str(text).split()[:limit]).rstrip(",;:") + "."


def _with_cta(text: str) -> str:
    if "subscribe" in text.lower():
        return text
    return f"{_cap(text, FAREWELL_MAX - len(CTA.split()))} {CTA}"


def bookends(title: str, texts: list[str], ask=ask_bookends) -> dict:
    """Intro salami / outro sagollasmasi (ssenariden kenar yegane metn - istifadeci 2026-10-13)."""
    user = f"VIDEO TITLE: {title}\nOPENING NARRATION: {' '.join(texts)[:1200]}"
    res: dict = {}
    for attempt in (1, 2):
        try:
            res = ask(BOOKEND_SYSTEM, user)
        except Exception as e:  # noqa: BLE001
            if llm.is_balance_error(e) or attempt == 2:
                raise
            print(f"  plan: intro/outro GPT xetasi ({str(e)[:100]}) - yeniden", flush=True)
            continue
        long = [k for k, lim in (("greeting", GREETING_MAX), ("farewell", FAREWELL_MAX))
                if len(str(res.get(k, "")).split()) > lim]
        if not long or attempt == 2:
            break
        user += f"\nTOO LONG last time: {', '.join(long)} - keep greeting <= {GREETING_MAX} words, " \
                f"farewell <= {FAREWELL_MAX} words."
    return {"greeting": _cap(res.get("greeting", ""), GREETING_MAX),
            "farewell": _with_cta(_cap(res.get("farewell", ""), FAREWELL_MAX)),
            "bg_prompt": photo_safe(str(res.get("bg_prompt", "")))[:400],
            "owl_intro": str(res.get("owl_intro", ""))[:200] or "waving hello, friendly",
            "owl_outro": str(res.get("owl_outro", ""))[:200] or "waving goodbye with one wing and pointing up with the other, smiling"}


def _bookend(n: int, kind: str, text: str, b: dict) -> dict:
    return {"n": n, "type": kind, "section": "", "section_start": False, "visual": "", "text": text,
            "photo_prompt": b["bg_prompt"], "owl": b[f"owl_{kind}"], "anim": None, "duration": 0.0}


def add_bookends(data: dict, ask=ask_bookends) -> dict:
    scenes = data["scenes"]
    if scenes and scenes[0].get("type") == "intro":
        return data
    content = [s for s in scenes if s.get("type") not in ("intro", "outro")]
    b = bookends(data["title"], [s["text"] for s in content[:3]], ask)
    last = max((s["n"] for s in content), default=0)
    return {**data, "scenes": [_bookend(0, "intro", b["greeting"], b), *content,
                               _bookend(last + 1, "outro", b["farewell"], b)]}


def main(ep: str) -> None:
    path = f"{ep}/scenes.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = add_bookends(plan_scenes(data))
    generate.atomic_json(path, out)
    kinds = [s["anim"]["kind"] for s in out["scenes"] if s["anim"]]
    print(f"  plan: {len(out['scenes']) - 2} sehne + intro/outro, animasiya {len(kinds)}: "
          + ", ".join(f"{k}x{kinds.count(k)}" for k in sorted(set(kinds))), flush=True)
    print(f"  plan: intro: {out['scenes'][0]['text']}\n  plan: outro: {out['scenes'][-1]['text']}", flush=True)
