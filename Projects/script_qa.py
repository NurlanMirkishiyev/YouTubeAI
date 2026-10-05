"""#59 (istifadeci 2026-10-05) - ssenari keyfiyyet qapisi, HER yeni videoda (script_gen cagirir, verify_script yoxlayir):
- deterministik (story_problems): biznes qerari sualdir; case ABS-dadir; Cold Open ilk ~3 saniyede (9 soz) konkret
  reqem deyir; case sahibi Hook-da ve HER tedris bolmesinde var (bir hekaye xetti); Recap-da reqem/ad/misal yox;
  yoxlanmis menbe adi + reqemi skriptde eyni abzasda;
- gpt-4o redaktor (review_loop): terifler ve analogiyalar duzgundur, vəd olunan qerara cavab verilir, misal tekrari
  yoxdur, Recap yalniz neticelerdir - problemli bolme gosterisle yeniden yazilir (en cox REVIEW_ROUNDS raund).
Hesabat: script_qa.json (skriptin sha256-si) - olmadan ve ya problem varsa script_gen merhelesi kecmir.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Callable

from research import citation_problems

REPORT = "script_qa.json"
REVIEW_ROUNDS = 2
COLD_OPEN_MAX_WORDS = 16
# Kokoro ~199 soz/deq: 3 saniye ~ 10 soz; giris kartinda reqem ilk 9 sozde deyilmelidir
FIRST_SECONDS_WORDS = 9
REVIEW_MODEL = "gpt-4o"

US_STATES = {s.lower() for s in (
    "Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia Hawaii Idaho Illinois "
    "Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts Michigan Minnesota Mississippi Missouri "
    "Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania Tennessee Texas Utah Vermont Virginia Washington "
    "Wisconsin Wyoming").split()} | {"new hampshire", "new jersey", "new mexico", "new york", "north carolina",
                                     "north dakota", "rhode island", "south carolina", "south dakota",
                                     "west virginia", "district of columbia", "washington, d.c."}
_QUESTION = re.compile(r"^(should|when|how|which|what|is|are|do|does|can|will|would)\b.*\?$", re.I)
_SECTION = re.compile(r"^## (.+?)\n(.*?)(?=^## |\Z)", re.M | re.S)


def sections(markdown: str) -> dict[str, str]:
    return {m[1].strip(): m[2].strip() for m in _SECTION.finditer(markdown)}


def replace_section(markdown: str, heading: str, body: str) -> str:
    def sub(m: re.Match) -> str:
        return f"## {m[1]}\n\n{body.strip()}\n\n" if m[1].strip() == heading else m[0]
    return _SECTION.sub(sub, markdown).rstrip() + "\n"


def _figures(text: str) -> list[float]:
    from visuals import figures
    return figures(text)


def cold_open_problems(line: str) -> list[str]:
    words = line.split()
    if not words:
        return ["Cold Open bosdur"]
    probs = []
    if len(words) > COLD_OPEN_MAX_WORDS:
        probs.append(f"Cold Open {len(words)} soz (max {COLD_OPEN_MAX_WORDS})")
    if not _figures(" ".join(words[:FIRST_SECONDS_WORDS])):
        probs.append(f"Cold Open-un ilk {FIRST_SECONDS_WORDS} sozunde (~3 s) konkret reqem yoxdur")
    return probs


def _owner(plan: dict) -> str:
    return str((plan.get("case") or {}).get("owner") or "").strip().split(" ")[0]


def story_problems(markdown: str, plan: dict, source: dict | None) -> list[str]:
    probs: list[str] = []
    decision = str(plan.get("decision") or "").strip()
    if not _QUESTION.match(decision):
        probs.append(f"biznes qerari sual deyil: {decision!r}")
    case = plan.get("case") or {}
    if str(case.get("state") or "").strip().lower() not in US_STATES:
        probs.append(f"case ABS-da deyil: {case.get('city')}, {case.get('state')}")
    secs = sections(markdown)
    probs += cold_open_problems(secs.get("Cold Open", ""))
    owner = _owner(plan)
    if not owner:
        probs.append("case sahibinin adi yoxdur")
    else:
        for head, body in secs.items():
            if (head == "Hook" or head.startswith("Section ")) and owner.lower() not in body.lower():
                probs.append(f"{head}: case sahibi {owner} yoxdur (hekaye xetti qirilir)")
    recap = secs.get("Recap", "")
    if _figures(recap):
        probs.append("Recap: reqem var - yalniz neticeler deyilmelidir")
    if owner and owner.lower() in recap.lower():
        probs.append(f"Recap: case ({owner}) yeniden danisilir - yalniz neticeler")
    if source is None:
        probs.append("yoxlanmis menbe yoxdur")
    else:
        probs += citation_problems(markdown, source)
    return probs


REVIEW_SYSTEM = """You are the fact-checking editor of a business explainer video for US small-business owners.
Read the whole script and judge it strictly. Answer ONLY JSON:
{"definitions_ok": bool, "analogies_ok": bool, "answers_decision": bool, "repeats": ["..."],
 "recap_only_conclusions": bool,
 "fixes": [{"section": "exact heading without ##", "problem": "...", "instruction": "what to change"}]}
- definitions_ok: every business term is defined correctly (as an accountant or the SBA would define it).
- analogies_ok: every analogy maps correctly onto the concept (no misleading comparison).
- answers_decision: the script clearly answers the promised decision question with a usable rule.
- repeats: any example, story beat, analogy or explanation that is told more than once (empty if none).
- recap_only_conclusions: the Recap only states conclusions/rules - no examples, stories, names or numbers.
- fixes: one item per section that must change (exact heading). Empty when everything is fine."""


def review_problems(r: dict) -> list[str]:
    probs = []
    if r.get("definitions_ok") is not True:
        probs.append("anlayis terifi yanlis/qeyri-deqiq")
    if r.get("analogies_ok") is not True:
        probs.append("analogiya anlayisa uygun deyil")
    if r.get("answers_decision") is not True:
        probs.append("vəd olunan qerar sualina cavab verilmir")
    reps = [str(x) for x in (r.get("repeats") or []) if str(x).strip()]
    if reps:
        probs.append("tekrar: " + "; ".join(reps)[:200])
    if r.get("recap_only_conclusions") is not True:
        probs.append("Recap yalniz neticeleri demir")
    return probs


REWRITE_SYSTEM = """You rewrite ONE section of a narration script for a US business explainer video. Keep the same
length (within 10%), the same case person and numbers unless the instruction says otherwise. Plain narration
paragraphs only - no heading, no lists, no meta commentary. Write figures as digits ("$4,000", "15%")."""


def _review_user(markdown: str, plan: dict, topic: str) -> str:
    return (f"Video topic: {topic}\nPromised decision: {plan.get('decision')}\nIntended answer: {plan.get('answer')}\n\n"
            f"SCRIPT:\n{markdown}")


def _rewrite_user(markdown: str, plan: dict, heading: str, body: str, instruction: str) -> str:
    case = plan.get("case") or {}
    return (f"Decision of the video: {plan.get('decision')}\nCase followed through the video: {case.get('owner')}, "
            f"{case.get('business')} in {case.get('city')}, {case.get('state')}.\n\nFULL SCRIPT (context only):\n"
            f"{markdown}\n\nRewrite ONLY the section \"{heading}\". Instruction: {instruction}\n\nCurrent text:\n{body}")


def apply_fixes(markdown: str, plan: dict, fixes: list[dict], rewrite: Callable, **kw) -> str:
    secs = sections(markdown)
    for fx in fixes:
        head = str(fx.get("section") or "").strip().lstrip("#").strip()
        if head not in secs or head == "Cold Open":
            continue
        instruction = f"{fx.get('problem', '')}. {fx.get('instruction', '')}".strip(". ")
        print(f"  [qa] {head}: {instruction[:110]}", flush=True)
        new = rewrite(REWRITE_SYSTEM, _rewrite_user(markdown, plan, head, secs[head], instruction), **kw).strip()
        if new:
            markdown = replace_section(markdown, head, new)
            secs = sections(markdown)
    return markdown


def review_loop(markdown: str, plan: dict, source: dict | None, topic: str, review: Callable,
                rewrite: Callable, rounds: int = REVIEW_ROUNDS, **kw) -> tuple[str, list[str]]:
    """gpt-4o redaktor -> problemli bolmeler yeniden yazilir -> yeniden yoxlama. Son hokmun problemleri qaytarilir."""
    for k in range(rounds + 1):
        r = review(REVIEW_SYSTEM, _review_user(markdown, plan, topic), model=REVIEW_MODEL, temperature=0,
                   max_tokens=1500)
        probs = review_problems(r)
        print(f"  [qa] redaktor raund {k + 1}: {probs or 'OK'}", flush=True)
        if not probs or k == rounds:
            return markdown, probs
        markdown = apply_fixes(markdown, plan, r.get("fixes") or [], rewrite, **kw)
    return markdown, probs


STORY_FIX = {
    "owner": "Keep teaching the same idea, but follow the case: say what happens to {owner}'s business in this "
             "section, using {owner}'s name.",
    "recap": "State only the 3 conclusions as plain rules the viewer can apply. No examples, no stories, no names, "
             "no numbers.",
    "source": "Include this verified fact once, naming the source and the figure exactly: According to {cite_as}, "
              "{claim}",
}


def story_fixes(markdown: str, plan: dict, source: dict | None, source_section: str) -> list[dict]:
    """Deterministik problemler -> bolme duzelis gosterisleri (apply_fixes formati)."""
    owner = _owner(plan)
    fixes = []
    for p in story_problems(markdown, plan, source):
        head = p.split(":", 1)[0]
        if "case sahibi" in p:
            fixes.append({"section": head, "problem": "the case is missing", "instruction": STORY_FIX["owner"].format(owner=owner)})
        elif p.startswith("Recap"):
            fixes.append({"section": "Recap", "problem": "recap repeats examples", "instruction": STORY_FIX["recap"]})
        elif p.startswith("menbe") and source:
            fixes.append({"section": source_section, "problem": "the research source is missing",
                          "instruction": STORY_FIX["source"].format(**source)})
    return fixes


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_report(ep_dir: str, markdown: str, problems: list[str], **extra) -> None:
    with open(os.path.join(ep_dir, REPORT), "w", encoding="utf-8") as f:
        json.dump({"script_sha256": _sha(markdown), "problems": problems, **extra}, f, indent=2, ensure_ascii=False)


def report_problems(ep_dir: str) -> list[str]:
    path = os.path.join(ep_dir, REPORT)
    if not os.path.isfile(path):
        return [f"ssenari keyfiyyet yoxlamasi aparilmayib ({REPORT} yoxdur)"]
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    with open(os.path.join(ep_dir, "script.md"), encoding="utf-8") as f:
        script = f.read()
    if rep.get("script_sha256") != _sha(script):
        return ["skript keyfiyyet yoxlamasindan sonra deyisib - script_qa yeniden isledilmelidir"]
    return list(rep.get("problems") or [])
