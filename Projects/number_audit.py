"""Ikinci qat: skriptdeki HER reqem ayrica yoxlanir - fail-closed (istifadeci 2026-10-02: "birdefelik hell et").
Real hal (why-9-99): "three clients a month at $50 an hour ... instead of earning $600 for those three clients,
you'd pull in $649.97 for four clients". math_check-in 3 baxisi ferqli ifade verdi -> "cogunluq eyni duzgun
deyeri tapsin" qaydasi susdu, saat sayi ise metnde umumiyyetle yox idi (duzgun deyer yoxdur).

Prinsip:
  1. Reqemler deterministik tapilir ve metnde isarelenir (`$600⟦7⟧`) - LLM reqem "unuda" bilmez.
  2. LLM her isare ucun rol verir: given (verilmis), result (evvelki reqemlerden ifade), missing (girisler yoxdur).
  3. Reqem yalniz cogunluq onu "given" ve ya Python-da DUZGUN hesablanmis "result" sayanda kecir.
     Ifadenin operandlari reqemden EVVELKI metnde olmalidir (math_check._grounded, sabitler vahid sozu ile).
  4. Kecmeyen reqem -> abzas yeniden yazdirilir -> butun skript yeniden yoxlanir.
  5. Raundlar bitib hele problem qalirsa: cumle reqemsiz yazilir (yoxlanir), olmursa cumle silinir.
     Yoxlanmamis hesab videoya hec vaxt dusmur.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Callable

import math_check as mc

ROUNDS = 3
PASSES = 3
MARK = "⟦{}⟧"
_PERCENT = re.compile(r"%|\s+per\s?cent\b", re.I)   # faiz neticesi vahidi ile yoxlanir (_check_one)


BATCH = 26   # markerler her sorguda A..Z - iki herfli marker (BG) gpt-4o-da 'G' olurdu


def _sentences(para: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for sent in mc._SPLIT.split(para):
        start = para.find(sent, pos)
        out.append((start, sent))
        pos = start + len(sent)
    return out


def _price_ending(sent: str, start: int) -> bool:
    """'those .99 prices' - qiymet sonlugu etiketidir (oncesinde reqem yoxdur), hesab iddiasi deyil."""
    return start > 0 and sent[start - 1] == "." and not sent[start - 2:start - 1].isdigit()


_PRONOUN_BEFORE = re.compile(r"\b(?:the|this|that|which|another|each|any)\s+$", re.I)
_UNIT_AFTER = re.compile(r"\s*(?:-\s*)?(?:cents?|dollars?|bucks?|percent|per\s?cent|%)", re.I)


def _pronoun_one(sent: str, start: int, end: int) -> bool:
    """'but the one priced at $9.99' - 'one' evezlikdir; 'that one cent difference' ise mebleqdir."""
    return (sent[start:end].lower() == "one" and bool(_PRONOUN_BEFORE.search(sent[:start]))
            and not _UNIT_AFTER.match(sent, end))


def _number_text(body: str, start: int, end: int) -> str:
    if start > 0 and body[start - 1] == "$":
        start -= 1
    unit = _PERCENT.match(body, end)
    if unit:
        end = unit.end()
    return body[start:end]


def marked_sections(markdown: str) -> list[dict]:
    """Reqemi olan her bolme: {section, marked, numbers:[{n, text, value, sentence, paragraph, context}]}.
    context = bolmenin reqemden EVVELKI metni (girisler neticeden evvel deyilir)."""
    sections: list[dict] = []
    cur = {"section": "", "paras": []}
    title = ""
    for block in re.split(r"\n\s*\n", markdown):
        para = block.strip()
        if not para:
            continue
        if para.startswith("#"):
            head = para.splitlines()[0]
            if head.startswith("# "):
                title = head[2:].strip()   # basliqdaki reqemler (mes. $9.99) movzunun verilmis sertidir
            if head.startswith("## "):
                sections.append(cur)
                cur = {"section": head[3:].strip(), "paras": []}
            para = "\n".join(para.splitlines()[1:]).strip()
            if not para:
                continue
        cur["paras"].append(para)
    sections.append(cur)

    out, n, earlier = [], 0, title
    for sec in sections:
        numbers, before = [], earlier   # Recap evvelki bolmelerin girislerine istinad edir
        for pi, para in enumerate(sec["paras"]):
            for s_off, sent in _sentences(para):
                for start, end, value in mc.find_numbers(sent):
                    if _price_ending(sent, start) or _pronoun_one(sent, start, end):
                        continue
                    n += 1
                    text = _number_text(sent, start, end)
                    t_end = s_off + start - (1 if text.startswith("$") else 0) + len(text)
                    numbers.append({"n": n, "text": text, "value": value, "sentence": sent,
                                    "paragraph": para, "section": sec["section"], "pi": pi, "at": t_end,
                                    "context": (before + " " + para[:s_off + start]).strip()})
            before = (before + " " + para).strip()
        if numbers:
            out.append({"section": sec["section"], "paras": sec["paras"], "numbers": numbers,
                        "earlier": earlier})
        earlier = before
    return out


def batches(sec: dict, only: list[dict] | None = None) -> list[tuple[str, dict[str, int]]]:
    """Bolme metni, secilmis reqemler ⟦A⟧..⟦Z⟧ ile isarelenib; her partiyada en cox BATCH reqem.
    -> [(metn, {marker: n})]. Markerde reqem yoxdur (reqemli marker LLM-de operand kimi qarisirdi)."""
    nums = only if only is not None else sec["numbers"]
    out = []
    for k in range(0, len(nums), BATCH):
        part = nums[k:k + BATCH]
        tags = {chr(65 + i): num["n"] for i, num in enumerate(part)}
        paras = list(sec["paras"])
        for t, num in sorted(zip(tags, part), key=lambda x: -x[1]["at"]):
            p = paras[num["pi"]]
            paras[num["pi"]] = p[:num["at"]] + MARK.format(t) + p[num["at"]:]
        out.append(("\n\n".join(paras), tags))
    return out


def _parse_marked(data: dict, tags: dict[str, int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for it in data.get("numbers") or []:
        if not isinstance(it, dict):
            continue
        key = re.sub(r"[^A-Z]", "", str(it.get("n", "")).upper())
        if key in tags:
            out[tags[key]] = it
    return out


def _restates(num: dict, expr: str) -> bool:
    """'instead of making ten dollars' - evvel deyilmis reqemin tekrari (ifade operatorsuz, eyni deyer)."""
    try:
        if not expr.strip() or mc._has_operator(expr):
            return False
        value = mc.safe_eval(expr)
    except (ValueError, SyntaxError):
        return False
    return abs(value - num["value"]) <= 1e-9 * max(1.0, abs(value)) and mc._grounded(value, num["context"])


def _said_before(num: dict) -> bool:
    """Reqem basliqda/evvelki metnde artiq deyilib (real hal: Hook-da basliqdaki '$9.99').
    Kicik tam ededler (0-12) her yerde var - onlarin tekrari subut sayilmir."""
    v = num["value"]
    if float(v).is_integer() and abs(v) <= 12:
        return False
    return any(abs(x - v) <= 1e-9 * max(1.0, abs(v)) for _, _, x in mc.find_numbers(num["context"]))


def _vote(num: dict, ans: dict | None) -> tuple[str, float | None, str]:
    """-> (ok | wrong | unverified | none, duzgun deyer, sebeb). Evvel deyilmis reqemin tekrari 'unverified'
    ola bilmez (sehv hesab 'wrong' kimi yene tutulur)."""
    v = _vote_raw(num, ans)
    return ("ok", None, "") if v[0] == "unverified" and _said_before(num) else v


def _vote_raw(num: dict, ans: dict | None) -> tuple[str, float | None, str]:
    if not isinstance(ans, dict):
        return "none", None, "yoxlanmayib"
    role = str(ans.get("role", "")).lower()
    if role == "given":
        return "ok", None, ""
    if role != "result":
        return "unverified", None, "girisler metnde yoxdur"
    if _restates(num, str(ans.get("expr", ""))):
        return "ok", None, ""
    s = {"id": num["n"], "section": num["section"], "sentence": num["sentence"],
         "paragraph": num["paragraph"], "context": num["context"]}
    p = mc._check_one(s, {"claimed_text": num["text"], "expr": ans.get("expr", ""), "approx": True})
    if p is None:
        return "ok", None, ""
    if p.get("correct") is not None:
        return "wrong", p["correct"], p["reason"]
    return "unverified", None, p["reason"]


def judge(sections: list[dict], passes: list[dict]) -> list[dict]:
    """Reqem yalniz cogunluq onu tesdiq edende VE hec bir baxis onu hesabla tekzib etmeyende kecir;
    sehv deyeri ancaq cogunluq eyni duzgun deyeri tapanda verilir."""
    need = len(passes) // 2 + 1
    problems = []
    for sec in sections:
        for num in sec["numbers"]:
            votes = [_vote(num, p.get(num["n"])) for p in passes]
            # Python-da subut olunmus sehv ('wrong') "given" ses coxlugu ile ortulmur (why-9-99 'just a dollar')
            if sum(v[0] == "ok" for v in votes) >= need and not any(v[0] == "wrong" for v in votes):
                continue
            correct, reason = None, next((v[2] for v in votes if v[0] != "ok"), "tesdiq olunmadi")
            for kind, val, why in votes:
                same = [v for v in votes if v[0] == "wrong" and v[1] is not None and val is not None
                        and abs(v[1] - val) <= mc.EXACT_TOL * max(1.0, abs(val))]
                if kind == "wrong" and len(same) >= need:
                    correct, reason = val, why
                    break
            problems.append({"id": f"n{num['n']}", "n": num["n"], "section": num["section"],
                             "text": num["text"], "sentence": num["sentence"], "paragraph": num["paragraph"],
                             "reason": f"'{num['text']}' tesdiq olunmadi: {reason}", "correct": correct})
    return problems


Extract = Callable[[list[dict]], dict]
Rewrite = Callable[[str, list[dict]], str]
Plain = Callable[[str], str]
Focus = Callable[[list[dict]], dict]


def _values(text: str) -> Counter:
    return Counter(round(v, 4) for _, _, v in mc.find_numbers(text))


def _valid_paragraph(new: str, old: str, problems: list[dict]) -> bool:
    """Bir abzas, basliqsiz, uzunluq yaxin; bayraqsiz reqemlerin hamisi yerinde qalir (real hal: duzgun
    '$9.99' yenidən yazilanda '$10' oldu - yalniz yoxlamadan kecmeyen reqem deyise biler)."""
    new = (new or "").strip()
    if not new or re.search(r"\n\s*\n", new) or any(line.lstrip().startswith("#") for line in new.splitlines()):
        return False
    if not 0.5 <= len(new.split()) / max(1, len(old.split())) <= 2.0:
        return False
    flagged = sum((_values(p["text"]) for p in problems), Counter())
    missing = (_values(old) - flagged) - _values(new)
    if missing:
        print(f"  RED: yeni abzasda bayraqsiz reqemler deyisib: {sorted(missing)}", flush=True)
    return not missing


def strip_sentences(md: str, problems: list[dict], plain: Plain) -> str:
    """Son care: problemli cumle reqemsiz yazilir; yeni cumlede reqem qalirsa cumle silinir."""
    done = set()
    for p in problems:
        key = (p["paragraph"], p["sentence"])
        if key in done:
            continue
        done.add(key)
        para = next((b.strip() for b in re.split(r"\n\s*\n", md) if p["sentence"] in b), None)
        if para is None:
            continue
        new = (plain(p["sentence"]) or "").strip()
        if not new or "\n" in new or mc.find_numbers(new):
            print(f"  cumle silindi (reqemsiz yazilmadi): {p['sentence']}", flush=True)
            new_para = re.sub(r"\s{2,}", " ", para.replace(p["sentence"], "", 1)).strip()
        else:
            print(f"  cumle reqemsiz yazildi: {p['sentence']} -> {new}", flush=True)
            new_para = para.replace(p["sentence"], new, 1)
        md = md.replace(para, new_para, 1) if new_para else md.replace(para + "\n\n", "", 1).replace(para, "", 1)
    return md


def second_look(sections: list[dict], problems: list[dict], focus: Focus | None, passes: int) -> list[dict]:
    """Duzgun deyeri olmayan sual altindaki reqemler ayrica, fokuslu suallarla yeniden yoxlanir (real hal:
    '3 dollar fee on 20 dollars = 15 percent' umumi baxisda 3 defe 'missing' oldu). Yene tesdiq olunmasa qalir."""
    suspects = {p["n"] for p in problems if p["correct"] is None}
    if not focus or not suspects:
        return problems
    nums = [n for sec in sections for n in sec["numbers"] if n["n"] in suspects]
    still = {p["n"] for p in judge([{"numbers": nums}], [focus(nums) for _ in range(passes)])}
    return [p for p in problems if p["correct"] is not None or p["n"] in still]


def audit_and_fix(md: str, extract: Extract, rewrite: Rewrite, plain: Plain, rounds: int = ROUNDS,
                  passes: int = PASSES, focus: Focus | None = None) -> tuple[str, list[dict]]:
    def audit(text: str) -> list[dict]:
        secs = marked_sections(text)
        if not secs:
            return []
        return second_look(secs, judge(secs, [extract(secs) for _ in range(passes)]), focus, passes)

    for _ in range(rounds):
        problems = audit(md)
        if not problems:
            return md, []
        by_para: dict[str, list[dict]] = {}
        for p in problems:
            by_para.setdefault(p["paragraph"], []).append(p)
        for para, probs in by_para.items():
            print(f"  tesdiqsiz reqem ({len(probs)}): {probs[0]['reason']}", flush=True)
            new = rewrite(para, probs)
            if _valid_paragraph(new, para, probs):
                md = md.replace(para, new.strip(), 1)
    problems = audit(md)
    if problems:
        md = strip_sentences(md, problems, plain)
        problems = audit(md)
    return md, problems


# ---------------------------------------------------------------- LLM hisseleri

EXTRACT_SYSTEM = """You audit every number in a video script. You never judge whether a number is right -
a program does that. You only say where each number comes from. Be literal and complete."""

EXTRACT_USER = """Every number in the text below is followed by a marker like ⟦G⟧ (the letters are only labels,
never numbers).
For EVERY marker return its role:
- "given": stated as a premise - a price, a fee, a count, a rate, an assumption of the example,
  a general fact - and NOT presented as following from other numbers.
- "result": presented as following from numbers stated EARLIER in the text (a total, earnings, a
  difference, savings, a loss, a share, a percentage, a per-week/month/year amount). Give "expr": a
  formula with digits and + - * / ( ) only, built from those earlier numbers, that computes it.
  Never copy the stated result into the formula. Money is in dollars (forty cents -> 0.40).
  A percentage is part / whole (a three dollar fee on a twenty dollar sale is a loss of 3 / 20).
  An amount saved, paid more or less, or a gap between two prices is a "result" even when it is said
  casually ("saving money, even if it's just a dollar" after $9.99 and $10 -> "10 - 9.99").
- "missing": presented as a result, but the earlier text does not state every input needed
  (for example a total for clients paid per hour when the hours are never stated), or no formula
  from the earlier numbers gives it.

Return JSON only: {{"numbers": [{{"n": "A", "role": "given"}}, {{"n": "B", "role": "result", "expr": "20 * 4"}},
{{"n": "C", "role": "missing"}}]}}

Text:
{text}"""

FOCUS_USER = """Look only at the number(s) marked {markers} in the text below (markers are letters, never
numbers). For each one decide carefully:
- "given" if it is a premise (price, fee, count, rate, assumption) or repeats a number said earlier;
- "result" if it follows from numbers stated EARLIER - then give "expr" with digits and + - * / ( ) only,
  built from those earlier numbers (a percentage is part / whole: a 3 dollar fee on 20 dollars -> 3 / 20);
  an amount saved or a gap between two prices is a "result" even when said casually
  ("even if it's just a dollar" after $9.99 and $10 -> "10 - 9.99");
- "missing" only if the earlier text really does not contain every input needed.
Return JSON only: {{"numbers": [{{"n": "G", "role": "result", "expr": "3 / 20"}}]}}

Earlier parts of the script (inputs may come from here):
{earlier}

Text:
{text}"""
EARLIER_CHARS = 4000

REWRITE_SYSTEM = """You fix numbers in narration for an ELI5 business video read aloud by a TTS voice.
Keep the voice, the example and the length. Arithmetic must be exactly right."""

REWRITE_USER = """A program could not verify these numbers in the paragraph below:
{errors}

Rewrite the paragraph so that every computed figure follows exactly from inputs stated BEFORE it:
state every input explicitly (count, price, hours, period), use simple round numbers, compute step by
step and say the correct result. If that makes the example clumsy, drop the computed figure and say it
in words without a number. Keep every other sentence as it is. One paragraph, no heading, no lists.
Return JSON only: {{"paragraph": "..."}}

Paragraph:
{paragraph}"""

PLAIN_SYSTEM = "You rewrite one narration sentence. Output JSON only."

PLAIN_USER = """Rewrite this sentence so it contains NO numbers at all (no digits, no number words, no
amounts, no percentages). Keep its meaning in qualitative words and keep it short.
Return JSON only: {{"sentence": "..."}}

Sentence: {sentence}"""


def _kw(llm_kw: dict) -> dict:
    if llm_kw.get("provider", "openai") == "openai" and not llm_kw.get("model"):
        return {**llm_kw, "model": mc.MATH_MODEL}
    return llm_kw


def llm_extract(sections: list[dict], **llm_kw) -> dict:
    from llm import chat_json
    out: dict[int, dict] = {}
    for sec in sections:
        for text, tags in batches(sec):
            data = chat_json(EXTRACT_SYSTEM, EXTRACT_USER.format(text=text), temperature=0.3,
                             max_tokens=4000, **_kw(llm_kw))
            out.update(_parse_marked(data, tags))
    return out


def llm_focus(nums: list[dict], sections: list[dict], **llm_kw) -> dict:
    """Yalniz sual altindaki reqemler isarelenir (qalanlari adi metn kimi qalir)."""
    from llm import chat_json
    out: dict[int, dict] = {}
    for sec in sections:
        mine = [n for n in sec["numbers"] if n in nums]
        for text, tags in batches(sec, mine) if mine else []:
            markers = ", ".join(MARK.format(t) for t in tags)
            data = chat_json(EXTRACT_SYSTEM, FOCUS_USER.format(
                markers=markers, text=text, earlier=sec.get("earlier", "")[-EARLIER_CHARS:] or "(none)"),
                             temperature=0.3, max_tokens=1500, **_kw(llm_kw))
            out.update(_parse_marked(data, tags))
    return out


def llm_rewrite(paragraph: str, problems: list[dict], **llm_kw) -> str:
    from llm import chat_json
    errors = "\n".join(
        f"- {p['text']} in \"{p['sentence']}\": "
        + (f"wrong, the correct value is {mc._spell(p['correct'])}" if p.get("correct") is not None
           else "cannot be computed from the numbers stated before it")
        for p in problems)
    data = chat_json(REWRITE_SYSTEM, REWRITE_USER.format(errors=errors, paragraph=paragraph),
                     temperature=0.0, max_tokens=1500, **_kw(llm_kw))
    return str(data.get("paragraph") or "")


def llm_plain(sentence: str, **llm_kw) -> str:
    from llm import chat_json
    data = chat_json(PLAIN_SYSTEM, PLAIN_USER.format(sentence=sentence), temperature=0.0, max_tokens=300,
                     **_kw(llm_kw))
    return str(data.get("sentence") or "")


def check(md: str, **llm_kw) -> tuple[str, list[dict]]:
    """math_check.check_file-dan cagrilir: (duzeldilmis skript, qalan problemler)."""
    print(f"[math] her reqem ayrica yoxlanir ({PASSES} musteqil baxis)", flush=True)
    state: dict = {}

    def extract(secs: list[dict]) -> dict:
        state["secs"] = secs
        return llm_extract(secs, **llm_kw)

    return audit_and_fix(md, extract, lambda p, pr: llm_rewrite(p, pr, **llm_kw),
                         lambda s: llm_plain(s, **llm_kw),
                         focus=lambda nums: llm_focus(nums, state["secs"], **llm_kw))


def audit_llm(md: str, **llm_kw) -> list[dict]:
    """Duzelissiz yoxlama (math_check-in son yoxlamasi ucun) - ikinci baxis daxil."""
    secs = marked_sections(md)
    if not secs:
        return []
    probs = judge(secs, [llm_extract(secs, **llm_kw) for _ in range(PASSES)])
    return second_look(secs, probs, lambda nums: llm_focus(nums, secs, **llm_kw), PASSES)
