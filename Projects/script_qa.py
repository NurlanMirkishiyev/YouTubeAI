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


def _outside(values: list[float], allowed: list[float]) -> list[float]:
    return [v for v in values if not any(abs(v - x) <= 1e-6 * max(1.0, abs(x)) for x in allowed)]


def cold_open_problems(line: str, allowed: list[float] | None = None) -> list[str]:
    """Faza 1.2: allowed verilibse (case modelinin reqemleri) Cold Open-un her reqemi modelden olmalidir."""
    words = line.split()
    if not words:
        return ["Cold Open bosdur"]
    probs = []
    if len(words) > COLD_OPEN_MAX_WORDS:
        probs.append(f"Cold Open {len(words)} soz (max {COLD_OPEN_MAX_WORDS})")
    if not _figures(" ".join(words[:FIRST_SECONDS_WORDS])):
        probs.append(f"Cold Open-un ilk {FIRST_SECONDS_WORDS} sozunde (~3 s) konkret reqem yoxdur")
    if allowed is not None:
        bad = _outside(_figures(line), allowed)
        if bad:
            probs.append(f"Cold Open reqemi case modelinde yoxdur: {', '.join(f'{v:g}' for v in bad)}")
    return probs


def model_result(plan: dict) -> tuple[dict | None, str]:
    """plan.model_result (ve ya plan.model-dan hesab) -> (netice, xeta)."""
    import case_model as cm
    if isinstance(plan.get("model_result"), dict):
        return plan["model_result"], ""
    if not isinstance(plan.get("model"), dict):
        return None, "planda case model (model) yoxdur"
    try:
        return cm.evaluate(plan["model"]), ""
    except cm.CaseModelError as e:
        return None, f"case model hesablanmir: {e}"


def _owner(plan: dict) -> str:
    return str((plan.get("case") or {}).get("owner") or "").strip().split(" ")[0]


_RULE = re.compile(r"\b(if|when|unless|once|as long as|only)\b", re.I)
_EXAMPLE = re.compile(r"\b(for example|for instance|imagine|picture this|let's say|say you|like when|such as)\b", re.I)
MAX_FIGURE_MENTIONS = 2     # eyni reqem: bir defe deyilir, bir defe hesabda islenir - qalani tekrardir


def _label(v: float, text: str) -> str:
    from visuals import unit_of
    unit = unit_of(v, text)
    s = f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}".rstrip("0").rstrip(".")
    return f"${s}" if unit == "$" else f"{s}%" if unit == "%" else s


def _mentions(text: str) -> list[float]:
    """Her deyilis ayrica (figures() tekrari bir defe sayir): "$1,150 ... $1,150" -> [1150, 1150]."""
    from math_check import find_numbers
    shown = _figures(text)
    return [v for _, _, v in find_numbers(text) if any(abs(v - x) < 1e-9 for x in shown)]


def repeated_figures(secs: dict[str, str]) -> list[str]:
    """E2E 2026-10-05: "$2,000 per project" 4 bolmede; 2026-10-07: "$1,150" bir bolmede 3 sehnede. Istifadeci
    (2026-10-07): her reqem en cox MAX_FIGURE_MENTIONS defe, qerar reqemi de. Ilk ve son deyilis qalir,
    ortadakilarin bolmeleri yeniden yazilir."""
    body = [h for h in secs if h == "Hook" or h.startswith("Section ") or h == "Common Mistakes"]
    decision = [h for h in secs if h.startswith("Section ")][-1:]
    where: dict[float, list[str]] = {}
    for h in body:
        for v in _mentions(secs[h]):
            key = next((k for k in where if abs(k - v) < 1e-9), v)
            where.setdefault(key, []).append(h)
    probs = []
    for v, heads in where.items():
        if len(heads) > MAX_FIGURE_MENTIONS:
            # ilk deyilis + qerar bolmesi saxlanir (real probe 2026-10-07: duzelis qerar bolmesinden reqemleri silirdi)
            order = [0] + [i for i, h in enumerate(heads) if h in decision and i] + list(range(1, len(heads)))
            keep = list(dict.fromkeys(order))[:MAX_FIGURE_MENTIONS]
            lbl = _label(v, secs[heads[0]])
            probs += [f"{h}: reqem {lbl} {len(heads)} defe tekrarlanir (bu bolmede "   # #97: yazici kvotani bilir
                      f"{sum(1 for i in keep if heads[i] == h)} qalir)"
                      for h in dict.fromkeys(heads[i] for i in range(len(heads)) if i not in keep)]
    return probs


_REPEAT = re.compile(r"^(.*): reqem (\S+) \d+ defe tekrarlanir(?: \(bu bolmede (\d+) qalir\))?")


def _settle_paragraph(par: str, lbl: str, drop: int) -> tuple[str, int]:
    """Paraqrafda lbl-in ilk `drop` deyilisini duzeldir: yeni reqemsiz cumle silinir, qalaninda reqem sozle."""
    pat = re.compile(r"(?<![\w$.,])" + re.escape(lbl) + r"(?![\d,]|\.\d)")
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", par):
        if drop > 0 and pat.search(sent):
            drop -= 1
            rest = pat.sub("", sent)
            if not _figures(rest):
                continue                              # yalniz tekrar - cumle silinir
            sent = pat.sub("that amount", sent, count=1)
        out.append(sent)
    return " ".join(s for s in out if s), drop


def settle_repeats(markdown: str) -> str:
    """#105: LLM raundlarindan sonra qalan 'reqem N defe' tekrarini deterministik duzeldir (son deyilisler - qerar
    qaydasi - qalir). gpt-4o-mini sitatli telimata da emel etmirdi: 14 cehdin 7-si bu xeta ile dusdu."""
    for _ in range(3):
        probs = [m for p in repeated_figures(sections(markdown)) if (m := _REPEAT.match(p))]
        if not probs:
            break
        for m in probs:
            head, lbl, quota = m[1], m[2], int(m[3] or 0)
            body = sections(markdown).get(head, "")
            pat = re.compile(r"(?<![\w$.,])" + re.escape(lbl) + r"(?![\d,]|\.\d)")
            drop = max(0, len(pat.findall(body)) - quota)
            pars = []
            for par in body.split("\n\n"):
                par, drop = _settle_paragraph(par, lbl, drop)
                pars.append(par)
            new = "\n\n".join(p for p in pars if p.strip())
            if body and new != body:
                markdown = markdown.replace(body, new, 1)
    return markdown


def plan_problems(plan: dict) -> list[str]:
    """Plan seviyyesi (#59): ssenari yazilmazdan evvel - pozulsa outline yeniden istenir."""
    probs: list[str] = []
    decision = str(plan.get("decision") or "").strip()
    if not _QUESTION.match(decision):
        probs.append(f"biznes qerari sual deyil: {decision!r}")
    case = plan.get("case") or {}
    if str(case.get("state") or "").strip().lower() not in US_STATES:
        probs.append(f"case ABS-da deyil: {case.get('city')}, {case.get('state')}")
    answer = str(plan.get("answer") or "")
    if not (_RULE.search(answer) and _figures(answer)):
        probs.append(f"qerarin cavabi konkret sertli qayda deyil (sert + reqem lazimdir): {answer!r}")
    # Faza 1.1/1.3: qerar hesabi case modelinden; cavabdaki her reqem modelden (ve ya menbe figure-u)
    import case_model as cm
    result, why = model_result(plan)
    if why:
        probs.append(why)
    elif result["threshold"]["value"] <= 0:           # real probe: '$-2,000' - cavab bunu duzelde bilmez
        t = result["threshold"]
        probs.append(f"case model threshold musbet deyil ({t['value']:g}): the threshold must be positive - rewrite "
                     f"threshold.expr so that it computes: {t['meaning']}")
    elif plan.get("model") and (link := cm.threshold_link_problem(plan["model"], result)):
        probs.append(link)                             # #98: esik qerarin neticesini terpetmelidir
    elif _figures(answer):
        allowed = cm.allowed_numbers(result) + [float(x) for x in plan.get("source_figures") or []]
        bad = _outside(_figures(answer), allowed)
        if bad:
            probs.append(f"cavabdaki reqem case modelinde yoxdur (uydurma): {', '.join(f'{v:g}' for v in bad)}")
        th = result["threshold"]["value"]
        if _outside([th], _figures(answer)):      # real probe: cavab '80 customers', threshold 250
            probs.append(f"cavab modelin threshold deyerini ({cm.fmt(th, result['threshold']['unit'])}) demir")
    # Faza 1.5: analogiya reqemsiz bir cumledir
    for i, s in enumerate(plan.get("sections") or [], 1):
        if isinstance(s, dict) and _figures(str(s.get("analogy") or "")):
            probs.append(f"bolme {i}: analogiyada reqem var - analogiya reqemsiz gundelik tesvirdir")
    return probs


_LEGAL = re.compile(r"\b(sued|lawsuits?|fined|convicted|indicted|fraud|settled|scam(?:med)?|charged with|"
                    r"violat(?:ed|ion)|illegal(?:ly)?|guilty|penalt(?:y|ies))\b", re.I)
_CAP_WORD = re.compile(r"\b[A-Z][a-zA-Z&.'-]*")
# dovlet qurumlari ve cumle evvelinde boyuk herfle gelen adi sozler - ad sayilmir
NOT_NAMES = {"irs", "sba", "ftc", "sec", "dol", "osha", "u.s", "us", "usa", "fda", "census", "bureau", "federal",
             "state", "department", "the", "if", "when", "she", "he", "they", "her", "his", "a", "an", "in", "so",
             "but", "and", "or", "this", "that", "for", "at", "on", "by", "under", "after", "before", "even", "i"}


def _bare(word: str) -> str:
    return re.sub(r"'s$", "", word.lower().strip(".,;:!?\"()"))


def legal_claim_problems(markdown: str, plan: dict) -> list[str]:
    """Faza 5.5 (2026-10-08): real sexs/sirket haqqinda menbesiz huquqi iddia olmur. Huquqi ittiham sozu olan
    cumlede case sahibi/biznesi/yeri ve dovlet qurumundan basqa xususi ad varsa -> problem (fail-closed)."""
    case = plan.get("case") or {}
    own = {_bare(w) for k in ("owner", "business", "city", "state") for w in str(case.get(k) or "").split()}
    probs = []
    for head, body in sections(markdown).items():
        for sent in re.split(r"(?<=[.!?])\s+", body):
            if not _LEGAL.search(sent):
                continue
            names = [w for w in _CAP_WORD.findall(sent) if _bare(w) not in own | NOT_NAMES]
            if names:
                probs.append(f"{head}: menbesiz huquqi iddia ({', '.join(names)}): {sent.strip()[:90]}")
    return probs


def story_problems(markdown: str, plan: dict, source: dict | None) -> list[str]:
    import case_model as cm
    probs = plan_problems(plan)
    secs = sections(markdown)
    result, _ = model_result(plan)
    allowed = None
    if result:
        allowed = cm.allowed_numbers(result) + ([float(source["figure"])] if source and source.get("figure")
                                                is not None else [])
    probs += cold_open_problems(secs.get("Cold Open", ""), allowed)
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
    if _EXAMPLE.search(recap):
        probs.append("Recap: misal var - yalniz neticeler deyilmelidir")
    probs += repeated_figures(secs)
    probs += legal_claim_problems(markdown, plan)
    if result:
        probs += cm.case_problems(markdown, {**plan, "model_result": result}, source)
    if source is None:
        probs.append("yoxlanmis menbe yoxdur")
    else:
        probs += citation_problems(markdown, source)
    return probs


REVIEW_SYSTEM = """You are the fact-checking editor of a business explainer video for US small-business owners.
Read the whole script and judge it strictly. Answer ONLY JSON:
{"definitions_ok": bool, "analogies_ok": bool, "answers_decision": bool, "repeats": ["..."],
 "recap_only_conclusions": bool, "consistent": bool, "source_faithful": bool, "single_case": bool,
 "fixes": [{"section": "exact heading without ##", "problem": "...", "instruction": "what to change"}]}
- definitions_ok: every business term is defined correctly (as an accountant or the SBA would define it).
- analogies_ok: every analogy maps correctly onto the concept (no misleading comparison).
- answers_decision: the script answers the promised decision with a concrete rule that has a condition and a
  threshold the viewer can check (e.g. "raise prices if your costs rose more than 5% and fewer than 1 in 10
  clients would leave"). A vague answer ("find a balance", "it depends", "consider your value") is false.
- repeats: any example, story beat, analogy or explanation told more than once - including restating facts
  already given (re-introducing who the owner is or what the business is, repeating the same price or figure
  without new meaning). Empty if none. A figure may be said at most twice in the video (introduced once, then used
  once in the decision rule) - a second mention is NOT a repeat; only a third mention or a re-told example is.
- recap_only_conclusions: the Recap only states conclusions/rules - no examples, stories, names or numbers.
- consistent: the case story never contradicts itself (same prices, decision and facts throughout; the case stays
  in third person about the owner; a figure is not used before it was introduced). The Cold Open is a deliberate
  teaser that states the key result BEFORE the story - its figures are not a consistency error.
- source_faithful: the verified fact is stated as given in VERIFIED FACT, and nothing more is attributed to the
  source (no added conclusions such as "without losing customers").
- single_case: every example is about the case owner's business; analogies are one-sentence everyday images
  without numbers. False if any example, story or calculation is about another business, company or industry
  (e.g. "a chef pricing a recipe", "a trucking company raising rates").
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
    if r.get("consistent") is not True:
        probs.append("hekaye ziddiyyetlidir (case faktlari/qerar uygun gelmir)")
    if r.get("source_faithful") is not True:
        probs.append("menbe tehrif olunub (fakta elave iddia yazilib)")
    if r.get("single_case") is not True:
        probs.append("basqa biznes misali var - yalniz case izlenmelidir")
    if r.get("recap_only_conclusions") is not True:
        probs.append("Recap yalniz neticeleri demir")
    return probs


REWRITE_SYSTEM = """You rewrite ONE section of a narration script for a US business explainer video. Keep the same
length (within 10%), the same case person and numbers unless the instruction says otherwise. Plain narration
paragraphs only - no heading, no lists, no meta commentary. Write figures as digits ("$4,000", "15%")."""


def _review_user(markdown: str, plan: dict, topic: str, source: dict | None = None) -> str:
    year = f", {source.get('year')} report" if source and source.get("year") else ""    # #93: il skriptde deyilir
    fact = f"VERIFIED FACT ({source.get('cite_as')}{year}): {source.get('claim')}\n" if source else ""
    return (f"Video topic: {topic}\nPromised decision: {plan.get('decision')}\nIntended answer: {plan.get('answer')}\n"
            f"{fact}\nSCRIPT:\n{markdown}")


def _rewrite_user(markdown: str, plan: dict, heading: str, body: str, instruction: str) -> str:
    case = plan.get("case") or {}
    return (f"Decision of the video: {plan.get('decision')}\nCase followed through the video: {case.get('owner')}, "
            f"{case.get('business')} in {case.get('city')}, {case.get('state')}.\n\nFULL SCRIPT (context only):\n"
            f"{markdown}\n\nRewrite ONLY the section \"{heading}\". Instruction: {instruction}\n\nCurrent text:\n{body}")


def apply_fixes(markdown: str, plan: dict, fixes: list[dict], rewrite: Callable, **kw) -> str:
    secs = sections(markdown)
    merged: dict[str, list[str]] = {}       # real probe: bir bolme bir raundda bir defe yeniden yazilir
    for fx in fixes:
        head = str(fx.get("section") or "").strip().lstrip("#").strip()
        text = f"{fx.get('problem', '')}. {fx.get('instruction', '')}".strip(". ")
        if text not in merged.setdefault(head, []):
            merged[head].append(text)
    for head, texts in merged.items():
        if head not in secs or head == "Cold Open":
            continue
        instruction = "\n- ".join([""] + texts).strip() if len(texts) > 1 else texts[0]
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
        r = review(REVIEW_SYSTEM, _review_user(markdown, plan, topic, source), model=REVIEW_MODEL, temperature=0,
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
    heads = sorted(sections(markdown), key=len, reverse=True)
    for p in story_problems(markdown, plan, source):
        # basliqda ozu ":" var ("Section 3: Testing") - problem metni real basliqla tutusdurulur
        head = next((h for h in heads if p.startswith(h + ":")), p.split(":", 1)[0])
        if "case sahibi" in p:
            fixes.append({"section": head, "problem": "the case is missing", "instruction": STORY_FIX["owner"].format(owner=owner)})
        elif p.startswith("Recap"):
            fixes.append({"section": "Recap", "problem": "recap repeats examples", "instruction": STORY_FIX["recap"]})
        elif ": reqem " in p and "tekrarlanir" in p:
            lbl = p.split(": reqem ", 1)[1].split(" ", 1)[0]
            left = re.search(r"bu bolmede (\d+) qalir", p)
            keep = (f"Say {lbl} exactly once in this section (in the decision rule); every other mention of it here "
                    if left and int(left[1]) == 1 else f"Do not restate {lbl} - it was already said earlier; ")
            quota = int(left[1]) if left else 0
            sents = [s for s in re.split(r"(?<=[.!?])\s+", sections(markdown).get(head, "")) if lbl in s]
            drop, kept = (sents[:-1], sents[-1:]) if quota == 1 and len(sents) > 1 else (sents, [])
            quoted = (" Change exactly these sentences: " + " ".join(f'"{s}"' for s in drop)
                      + (f' Keep {lbl} in: "{kept[0]}"' if kept else "")) if drop else ""   # #101: sitat
            fixes.append({"section": head, "problem": f"{lbl} is restated",
                          "instruction": keep + "refer to it in words (e.g. 'that amount', 'the same cost') without "
                                         "the number, and do not re-introduce the business." + quoted})
        elif "evvel/sonra cutu" in p or "threshold deyeri" in p:
            result, _ = model_result(plan)
            import case_model as cm
            t = result["threshold"] if result else {}
            fixes.append({"section": head, "problem": "the decision figures are missing",
                          "instruction": "In ONE sentence state a before and after pair of the case model, e.g. '"
                                         + (cm._pair_hint(result) if result else "") + "', and state the threshold "
                                         + (cm.fmt(t["value"], t["unit"]) if t else "") + " (" + str(t.get("meaning", ""))
                                         + ") as the condition of the decision. Use exactly these figures."
                                         + ("\nCASE MODEL:\n" + cm.figures_text(result) if result else "")})
        elif "deyisen buraxilib" in p or "case modelinde yoxdur" in p or "case modeli ile uygun deyil" in p:
            result, _ = model_result(plan)
            import case_model as cm
            fixes.append({"section": head, "problem": "a figure does not follow the case model",
                          "instruction": "Use exactly these figures of the case model and no other case numbers; "
                                         "every calculation must include all variables (e.g. customers who leave). "
                                         "Remove the wrong figure: " + p.split(":", 1)[-1].strip()
                                         + ("\nCASE MODEL:\n" + cm.figures_text(result) if result else "")})
        elif p.startswith("menbe kohnedir") and source:          # #92: telimat ili adlandirir
            fixes.append({"section": source_section, "problem": "the source is older than 3 years: say its year",
                          "instruction": f"In the sentence that cites {source.get('cite_as') or 'the source'}, "
                                         f"say the year of the report explicitly: \"According to "
                                         f"{source.get('cite_as') or 'the source'}'s {source.get('year')} report, ...\" "
                                         "Keep the figure and the source name exactly as they are."})
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
