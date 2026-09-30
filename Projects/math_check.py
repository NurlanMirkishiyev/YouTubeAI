"""Skriptdeki hesablamalarin deterministik yoxlanmasi (istifadeci 2026-09-30: reqem sehvi QETI olmur).
Real hal: "a hundred dishes a week -> $20 savings. Over a month, that's eight hundred dollars."

Prinsip: LLM hesablamir, yalniz tercume edir.
  1. Reqem olan HER cumle deterministik tapilir (numeric_sentences) - LLM cumle "unuda" bilmez.
  2. LLM her cumle ucun: hesablama neticesidirmi, ifade (20 * 4), iddianin metndeki sozleri.
  3. Iddia olunan deyer metnden Python-da oxunur (parse_number), ifade Python-da hesablanir (safe_eval),
     ifadenin operandlari bolmede gecen reqemlerden ve ya standart sabitlerden olmalidir.
  4. Sehv abzas LLM-e duzgun deyerle yeniden yazdirilir, butun skript tekrar yoxlanir.
  5. Netice math_check.json-a skriptin sha256-si ile yazilir; verify_script onu teleb edir.
Istifade: python Projects\\math_check.py Episodes\\<slug> [--provider openai]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPORT = "math_check.json"
ROUNDS = 3
PASSES = 3          # musteqil LLM baxisi - sehv yalniz cogunluq razilasanda
MATH_MODEL = "gpt-4o"   # 4o-mini real skriptde ifadeleri qarisdirirdi (80 -> 8000)
EXACT_TOL = 0.01
APPROX_TOL = 0.10
HEDGES = re.compile(r"\b(roughly|about|around|nearly|almost|approximately|close to|over|more than|"
                    r"less than|under|just over|just under|or so|some)\b", re.I)
# vaxt/vahid cevrilmeleri ve faiz - metnde yazilmasa da ifadede ola biler
CONSTANTS = {1, 2, 3, 4, 4.3, 4.33, 4.345, 5, 7, 10, 12, 24, 26, 30, 52, 60, 100, 365, 1000}

UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)}
SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9}
_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?|[a-z]+")


def _tokens(text: str) -> list[tuple[str, int, int]]:
    low = text.lower().replace("-", " ").replace("’", "'")
    return [(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(low)]


def _is_num_word(t: str) -> bool:
    return t in UNITS or t in TENS or t == "hundred" or t in SCALES


def _digit(t: str) -> float | None:
    return float(t.replace(",", "")) if t[0].isdigit() else None


def _run(toks: list[str], i: int) -> tuple[float, int] | None:
    """toks[i]-den baslayan soz/reqem ardicilligi -> (deyer, novbeti indeks)."""
    total, current, seen = 0.0, 0.0, False
    n = len(toks)
    while i < n:
        t = toks[i]
        nxt = toks[i + 1] if i + 1 < n else ""
        d = _digit(t)
        if d is not None and not seen:
            current, seen = d, True
        elif t in UNITS or t in TENS:
            current += UNITS.get(t, 0) + TENS.get(t, 0)
            seen = True
        elif t == "hundred" and (seen or current == 0):
            current = (current or 1) * 100
            seen = True
        elif t in SCALES and (seen or current == 0):
            total += (current or 1) * SCALES[t]
            current, seen = 0.0, True
        elif t == "a" and not seen and nxt in ("hundred", *SCALES):
            current = 1
        elif t == "and" and seen and _is_num_word(nxt) and toks[i - 1] in ("hundred", *SCALES):
            pass
        elif t == "point" and seen and (nxt in UNITS or (nxt[:1].isdigit())):
            frac, k, j = "", i + 1, i + 1
            while j < n and (toks[j] in UNITS and UNITS[toks[j]] < 10 or toks[j].isdigit()):
                frac += str(UNITS.get(toks[j], toks[j]))
                j += 1
            current += float("0." + frac)
            i = j
            continue
        else:
            break
        i += 1
    return (total + current, i) if seen else None


def find_numbers(text: str) -> list[tuple[int, int, float]]:
    """Metndeki butun reqem ifadeleri -> [(baslangic, son, deyer)]. 'two dollars and fifty cents' = 2.5,
    'forty cents' = 0.4, 'half' = 0.5, '1.5 million' = 1.5e6."""
    tk = _tokens(text)
    words = [t for t, _, _ in tk]
    out: list[tuple[int, int, float]] = []
    i = 0
    while i < len(tk):
        if words[i] == "half":
            out.append((tk[i][1], tk[i][2], 0.5))
            i += 1
            continue
        got = _run(words, i)
        if not got:
            i += 1
            continue
        value, j = got
        start, end = tk[i][1], tk[j - 1][2]
        nxt = words[j] if j < len(words) else ""
        if nxt in ("dollar", "dollars") and j + 2 < len(words) and words[j + 1] == "and":
            cents = _run(words, j + 2)
            if cents and cents[1] < len(words) and words[cents[1]] in ("cent", "cents"):
                value += cents[0] / 100
                end = tk[cents[1]][2]
                j = cents[1] + 1
        elif nxt in ("cent", "cents"):
            value /= 100
            end = tk[j][2]
        out.append((start, end, value))
        i = max(j, i + 1)
    return out


def parse_number(text: str) -> float | None:
    found = find_numbers(text)
    return found[0][2] if found else None


_OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a ** b}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        try:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        except ZeroDivisionError as e:
            raise ValueError("sifra bolme") from e
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    raise ValueError("icaze verilmeyen ifade: " + type(node).__name__)


def safe_eval(expr: str) -> float:
    """Yalniz reqem ve + - * / ** ( ) - eval() yox."""
    try:
        tree = ast.parse(str(expr).replace(",", ""), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"ifade oxunmur: {expr}") from e
    return _eval(tree)


def _operands(expr: str) -> list[float]:
    tree = ast.parse(str(expr).replace(",", ""), mode="eval")
    return [float(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)]


def _has_operator(expr: str) -> bool:
    tree = ast.parse(str(expr).replace(",", ""), mode="eval")
    return any(isinstance(n, ast.BinOp) for n in ast.walk(tree))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("-", " ").lower()).strip()


_SPLIT = re.compile(r"(?<=[.!?])[\"”']?\s+")


def numeric_sentences(markdown: str) -> list[dict]:
    """Reqem olan her narration cumlesi: {id, section, paragraph, sentence, context}.
    context = bolmenin bu cumleye qederki metni (operandlarin menbeyi)."""
    out: list[dict] = []
    section, before = "", ""
    for block in re.split(r"\n\s*\n", markdown):
        para = block.strip()
        if not para:
            continue
        if para.startswith("#"):
            head = para.splitlines()[0]
            section = head.lstrip("#").strip() if head.startswith("## ") else section
            before = ""
            rest = "\n".join(para.splitlines()[1:]).strip()
            if not rest:
                continue
            para = rest
        for sent in _SPLIT.split(para):
            sent = sent.strip()
            if sent and find_numbers(sent):
                out.append({"id": len(out) + 1, "section": section, "paragraph": para,
                            "sentence": sent, "context": (before + " " + sent).strip()})
            before = (before + " " + sent).strip()
    return out


def _grounded(value: float, context: str) -> bool:
    if any(abs(value - c) < 1e-9 for c in CONSTANTS):
        return True
    low = context.lower()
    for start, end, v in find_numbers(context):
        unit = low[end:end + 9].lstrip()
        forms = [v]
        if unit.startswith(("percent", "%", "per cent")) or low[start:end + 1].endswith("%"):
            forms.append(v / 100)          # faiz: 2 percent -> 0.02
        if low[start:end].endswith(("cent", "cents")):
            forms.append(v * 100)          # sent: forty cents -> 40
        if any(abs(value - x) <= 1e-9 * max(1.0, abs(x)) for x in forms):
            return True
    return False


def _problem(s: dict, reason: str, **extra) -> dict:
    return {"id": s["id"], "section": s["section"], "sentence": s["sentence"],
            "paragraph": s["paragraph"], "reason": reason, **extra}


def _check_one(s: dict, it: dict) -> dict | None:
    claimed_text = str(it.get("claimed_text", "")).strip()
    expr = str(it.get("expr", "")).strip()
    if not claimed_text or _norm(claimed_text) not in _norm(s["sentence"]):
        return _problem(s, f"iddia '{claimed_text}' metnde yoxdur")
    claimed = parse_number(claimed_text)
    if claimed is None:
        return _problem(s, f"iddiada reqem yoxdur: '{claimed_text}'")
    try:
        correct = safe_eval(expr)
        if not _has_operator(expr):
            return _problem(s, f"ifade hesablama deyil: '{expr}'")
        loose = [v for v in _operands(expr) if not _grounded(v, s["context"])]
    except (ValueError, SyntaxError) as e:
        return _problem(s, f"ifade hesablanmir: {e}")
    if loose:
        return _problem(s, f"ifadede metnde olmayan reqem: {loose} ({expr})", expr=expr)
    approx = bool(it.get("approx")) and bool(HEDGES.search(s["sentence"]))
    tol = APPROX_TOL if approx else EXACT_TOL
    targets = [correct]
    if "percent" in claimed_text.lower() or "%" in claimed_text:
        targets.append(correct * 100)
    if "cent" in claimed_text.lower() or re.search(r"\bcents?\b", s["context"].lower()):
        targets.append(correct / 100)      # ifade sentle, iddia dollarla (40 - 20 -> 0.20)
    if any(abs(claimed - t) <= max(tol * abs(t), 0.005) for t in targets):
        return None
    best = targets[-1] if len(targets) > 1 and abs(correct) < 1 else correct
    return _problem(s, f"'{claimed_text}' = {claimed:g}, amma {expr} = {best:g}",
                    expr=expr, claimed=claimed, correct=best)


def check_items(sents: list[dict], items: list[dict]) -> list[dict]:
    """LLM tercumesini deterministik yoxlayir. Yoxlanmamis reqemli cumle de problemdir."""
    by_id: dict[int, dict] = {}
    for it in items:
        try:
            by_id[int(it.get("id"))] = it
        except (TypeError, ValueError):
            continue
    problems = []
    for s in sents:
        it = by_id.get(s["id"])
        if it is None:
            problems.append(_problem(s, "cumle yoxlanmayib (LLM qaytarmadi)"))
        elif it.get("calc"):
            p = _check_one(s, it)
            if p:
                problems.append(p)
    return problems


Extract = Callable[[list[dict]], list[dict]]
Rewrite = Callable[[str, list[dict]], dict]   # (abzas, problemler) -> {id: duzeldilmis cumle}


def _index(items: list[dict]) -> dict[int, dict]:
    by_id: dict[int, dict] = {}
    for it in items:
        try:
            by_id[int(it.get("id"))] = it
        except (TypeError, ValueError):
            continue
    return by_id


def judge(sents: list[dict], passes: list[list[dict]]) -> list[dict]:
    """Bir nece musteqil LLM tercumesi -> konsensus. Cumle yalniz cogunluq EYNI duzgun deyeri tapanda
    sehv sayilir (real hal: tek bir baxis '20 * 4 * 100' yazib duzgun 80-i 8000-e "duzeltdi").
    Formati pozuq cavab (reqemsiz iddia, operatorsuz ifade, uydurma operand) ses vermir."""
    need = len(passes) // 2 + 1
    maps = [_index(items) for items in passes]
    problems = []
    for s in sents:
        valid, wrong = 0, []
        for m in maps:
            it = m.get(s["id"])
            if it is None:
                continue
            if not it.get("calc"):
                valid += 1
                continue
            p = _check_one(s, it)
            if p is None:
                valid += 1
            elif p.get("correct") is not None:
                valid += 1
                wrong.append(p)
        if not valid:
            problems.append(_problem(s, "cumle yoxlanmayib (etibarli cavab yoxdur)"))
            continue
        for p in wrong:
            same = [q for q in wrong if abs(q["correct"] - p["correct"]) <= EXACT_TOL * max(1.0, abs(p["correct"]))]
            if len(same) >= need:
                problems.append(p)
                break
    return problems


def audit_and_fix(markdown: str, extract: Extract, rewrite: Rewrite, rounds: int = ROUNDS,
                  passes: int = PASSES) -> tuple[str, list[dict]]:
    """Yoxla -> sehvli cumleleri yeniden yazdir -> butun skripti tekrar yoxla (en cox `rounds` duzelis)."""
    md = markdown
    for r in range(rounds + 1):
        sents = numeric_sentences(md)
        problems = judge(sents, [extract(sents) for _ in range(passes)]) if sents else []
        if not problems or r == rounds:
            return md, problems
        by_para: dict[str, list[dict]] = {}
        for p in problems:
            if p.get("correct") is not None:
                by_para.setdefault(p["paragraph"], []).append(p)
        for para, probs in by_para.items():
            print(f"  hesab sehvi ({len(probs)}): {probs[0]['reason']}", flush=True)
            md = _replace_sentences(md, para, probs, rewrite(para, probs))
    return md, problems


def _has_value(sentence: str, correct: float) -> bool:
    """Yeni cumlede duzgun deyer var? (roughly ile yuvarlaqlasdirma 10%-e qeder)."""
    low = sentence.lower()
    forms = [correct]
    if "percent" in low or "%" in low:
        forms.append(correct * 100)
    if re.search(r"\bcents?\b", low):
        forms.append(correct / 100)
    tol = APPROX_TOL if HEDGES.search(sentence) else EXACT_TOL
    return any(abs(v - f) <= max(tol * abs(f), 0.005) for _, _, v in find_numbers(sentence) for f in forms)


def _replace_sentences(md: str, para: str, probs: list[dict], fixed: dict) -> str:
    """Yalniz sehvli cumleler deyisir - abzasin qalani toxunulmaz qalir. Duzgun deyeri olmayan
    yeni cumle qebul edilmir (yoxlayici ozu yeni sehv gatire bilmez)."""
    new_para = para
    for p in probs:
        new = str(fixed.get(p["id"], fixed.get(str(p["id"]), ""))).strip()
        if not new or "\n" in new:
            continue
        if not _has_value(new, p["correct"]):
            print(f"  RED: yeni cumlede duzgun deyer ({p['correct']:g}) yoxdur: {new}", flush=True)
            continue
        new_para = new_para.replace(p["sentence"], new, 1)
    return md.replace(para, new_para, 1) if new_para != para else md


def _sha(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def write_report(ep_dir: str, markdown: str, problems: list[dict]) -> None:
    rows = [{k: p.get(k) for k in ("section", "sentence", "reason", "expr", "claimed", "correct")}
            for p in problems]
    with open(os.path.join(ep_dir, REPORT), "w", encoding="utf-8") as f:
        json.dump({"script_sha256": _sha(markdown), "problems": rows}, f, indent=2, ensure_ascii=False)


def report_problems(ep_dir: str) -> list[str]:
    """verify_script ucun: hesabat var, bu skripte aiddir ve sehv yoxdur."""
    path = os.path.join(ep_dir, REPORT)
    if not os.path.isfile(path):
        return ["hesablama yoxlamasi aparilmayib (math_check.json yoxdur)"]
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    with open(os.path.join(ep_dir, "script.md"), encoding="utf-8") as f:
        script = f.read()
    if rep.get("script_sha256") != _sha(script):
        return ["skript hesablama yoxlamasindan sonra deyisib - math_check yeniden isledilmelidir"]
    return [f"hesablama sehvi: {p.get('sentence')} ({p.get('reason')})" for p in rep.get("problems", [])]


# ---------------------------------------------------------------- LLM hisseleri

EXTRACT_SYSTEM = """You translate the arithmetic in a video script into formulas. You never judge
whether a number is right - a program does that. Be literal and complete."""

EXTRACT_USER = """Below are numbered sentences from one section of a script, each with the text that
precedes it in that section.

For EVERY numbered sentence return one item. A sentence is a calculation ("calc": true) when it states
a number that follows from other numbers already given: a total, difference, product, share, per-unit
amount, percentage, savings, loss, or a conversion over time (per week -> per month, per month -> per year).
Sentences that only introduce an input number (a price, a fee, a count) are "calc": false.

For calc items:
- "expr": an arithmetic formula using only digits and + - * / ( ) that computes the stated result
  from the INPUT numbers in the context. Never copy the stated result into the formula.
  Percentages: "two percent of twenty dollars" -> 20 * 2 / 100. "Seventeen of twenty is a fifteen percent
  loss" -> (20 - 17) / 20. Time: week -> month = * 4 unless the text says otherwise, month -> year = * 12,
  day -> month = * 30, week -> year = * 52.
- Money is always in DOLLARS: forty cents -> 0.40, two dollars and fifty cents -> 2.50.
- "claimed_text": the words of the sentence that state the result, copied EXACTLY (e.g. "eight hundred dollars").
- "approx": true only if the sentence itself hedges the result (roughly, about, around, nearly).

Return JSON only: {{"items": [{{"id": 1, "calc": true, "expr": "20 * 4", "claimed_text": "...", "approx": false}},
{{"id": 2, "calc": false}}]}}

{listing}"""

REWRITE_SYSTEM = """You fix arithmetic errors in narration for an ELI5 business video read aloud by a TTS
voice. Keep the voice, the example and the length. Write numbers as words, as in the original."""

REWRITE_USER = """A program found calculation errors in these sentences of the paragraph below:
{errors}

Rewrite ONLY those sentences so that the stated result is arithmetically correct. Use the correct value
shown, written as words like the rest of the text; if it is not a round number, say "roughly" and round it.
Do not change the input numbers, do not add or remove sentences, keep the wording otherwise.
Return JSON only: {{"sentences": {{"<id>": "<the corrected sentence>"}}}}

Paragraph (context):
{paragraph}"""


def _spell(v: float) -> str:
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def llm_extract(sents: list[dict], **llm_kw) -> list[dict]:
    from llm import chat_json
    items: list[dict] = []
    by_section: dict[str, list[dict]] = {}
    for s in sents:
        by_section.setdefault(s["section"], []).append(s)
    for group in by_section.values():
        listing = "\n\n".join(f"[{s['id']}] context: {s['context'][:1200]}\n    sentence: {s['sentence']}"
                              for s in group)
        data = chat_json(EXTRACT_SYSTEM, EXTRACT_USER.format(listing=listing), temperature=0.5,
                         max_tokens=4000, **llm_kw)
        items += [it for it in data.get("items") or [] if isinstance(it, dict)]
    return items


def llm_rewrite(paragraph: str, problems: list[dict], **llm_kw) -> dict:
    from llm import chat_json
    errors = "\n".join(
        f"[{p['id']}] \"{p['sentence']}\" -> {p['reason']}"
        + (f"; correct value: {_spell(p['correct'])}" if p.get("correct") is not None else "")
        for p in problems)
    data = chat_json(REWRITE_SYSTEM, REWRITE_USER.format(errors=errors, paragraph=paragraph),
                     temperature=0.0, max_tokens=1500, **llm_kw)
    got = data.get("sentences") or {}
    return got if isinstance(got, dict) else {}


def check_file(script_path: str, **llm_kw) -> list[dict]:
    """script.md-ni yoxlayir/duzeldir, yeniden yazir, hesabati yazir -> qalan problemler."""
    if llm_kw.get("provider", "openai") == "openai" and not llm_kw.get("model"):
        llm_kw = {**llm_kw, "model": MATH_MODEL}
    with open(script_path, encoding="utf-8") as f:
        md = f.read()
    print(f"[math] hesablamalar yoxlanir ({PASSES} musteqil baxis)", flush=True)
    fixed, problems = audit_and_fix(md, lambda s: llm_extract(s, **llm_kw),
                                    lambda p, pr: llm_rewrite(p, pr, **llm_kw))
    if fixed != md:
        with open(script_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(fixed.rstrip() + "\n")
    write_report(os.path.dirname(script_path), fixed, problems)
    n = len(numeric_sentences(fixed))
    print(f"  {n} reqemli cumle yoxlandi, qalan sehv: {len(problems)}", flush=True)
    for p in problems:
        print(f"  SEHV: {p['sentence']} ({p['reason']})", flush=True)
    return problems


def main() -> None:
    from llm import add_provider_arg
    ap = argparse.ArgumentParser()
    ap.add_argument("ep_dir")
    add_provider_arg(ap)
    a = ap.parse_args()
    problems = check_file(os.path.join(a.ep_dir, "script.md"), provider=a.provider, model=a.model)
    if problems:
        raise SystemExit(f"{len(problems)} hesablama sehvi duzelmedi - bax: {os.path.join(a.ep_dir, REPORT)}")


if __name__ == "__main__":
    main()
