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
  people and real objects instead.
- "owl": what the cartoon owl presenter does in this scene (6-14 words): pose, expression and at most one prop that
  fits the narration.
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


def _user(scenes: list[dict], title: str, preferred: dict[int, str] | None = None,
          rejected: dict[int, list] | None = None) -> str:
    parts = [f"VIDEO: {title}"]
    for s in scenes:
        pref = f"\nPREFERRED KIND: {preferred[s['n']]}" if preferred and s["n"] in preferred else ""
        rej = (f"\nREJECTED (contained words or numbers that are not in this narration - copy exact fragments "
               f"instead): {json.dumps(rejected[s['n']], ensure_ascii=False)}" if rejected and s["n"] in rejected else "")
        parts.append(f"SCENE {s['n']}: section={s['section']!r}\nVISUAL: {s['visual']}\nNARRATION: {s['text']}{pref}{rej}")
    return "\n\n".join(parts)


def _item(r) -> tuple[int, dict] | None:
    try:
        return int(r["n"]), r
    except (TypeError, ValueError, KeyError):
        return None


def _ask_batch(scenes: list[dict], title: str, ask, preferred: dict[int, str] | None = None,
               rejected: dict[int, list] | None = None) -> dict[int, dict]:
    for attempt in range(1, BATCH_TRIES + 1):
        try:
            res = ask(SYSTEM, _user(scenes, title, preferred, rejected))
            pairs = (_item(r) for r in res.get("scenes", []))
            return dict(p for p in pairs if p)
        except Exception as e:  # noqa: BLE001 - plan ssenari sebebile dayanmir; balans xetasi istisnadir
            if llm.is_balance_error(e):
                raise
            print(f"  plan: GPT xetasi cehd {attempt} ({str(e)[:120]})", flush=True)
    print(f"  plan: sehne {scenes[0]['n']}-{scenes[-1]['n']} VISUAL + quote istifade olunur", flush=True)
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
    for i in range(0, len(bad), batch):
        for n, r in _ask_batch(bad[i:i + batch], title, ask, preferred, rejected).items():
            if n in rejected:
                got[n] = {**got.get(n, {}), "anim": _cands(r) + rejected[n]}
    print(f"  plan: {len(bad)} animasiya sehnesi redd sebebi ile yeniden soruldu", flush=True)


def plan_scenes(data: dict, ask=ask_gpt, batch: int = 6) -> dict:
    scenes = [dict(s) for s in data["scenes"]]
    types = assign_types(len(scenes))
    preferred: dict[int, str] = {}
    for s, t in zip(scenes, types):
        if t == "anim":
            preferred[s["n"]] = kind_order(len(preferred))[0]
    got: dict[int, dict] = {}
    for i in range(0, len(scenes), batch):
        got.update(_ask_batch(scenes[i:i + batch], data["title"], ask, preferred))
    _repair(scenes, types, got, data["title"], ask, preferred, batch)
    n_anim, counts, prev, k = types.count("anim"), {}, None, 0
    for s, t in zip(scenes, types):
        r = got.get(s["n"], {})
        s["type"] = t
        s["photo_prompt"] = photo_safe(str(r.get("photo_prompt") or s["visual"] or s["text"]))[:400]
        s["owl"] = str(r.get("owl") or "standing and explaining, friendly")[:200]
        s["anim"] = None
        if t == "anim":
            cands = _cands(r)
            order = kind_order(k)
            cands = sorted(cands, key=lambda c: order.index(c["kind"]) if isinstance(c, dict) and c.get("kind") in order else 99)
            s["anim"] = pick_anim(cands, s["text"], prev, counts, n_anim, k % 2)
            counts[s["anim"]["kind"]] = counts.get(s["anim"]["kind"], 0) + 1
            prev, k = s["anim"]["kind"], k + 1
    return {**data, "scenes": scenes}


def main(ep: str) -> None:
    path = f"{ep}/scenes.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = plan_scenes(data)
    generate.atomic_json(path, out)
    kinds = [s["anim"]["kind"] for s in out["scenes"] if s["anim"]]
    print(f"  plan: {len(out['scenes'])} sehne, animasiya {len(kinds)}: "
          + ", ".join(f"{k}x{kinds.count(k)}" for k in sorted(set(kinds))), flush=True)
