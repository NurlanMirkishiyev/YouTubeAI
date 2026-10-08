"""Add'im 22 - movzu -> 10-12 deqiqelik ELI5 Business skripti (~1650 soz).
Istifade:
  python Projects\\script_gen.py "Trademark vs Copyright vs Patent" [--provider openai|deepseek|ollama]
  python Projects\\script_gen.py "..." --slug trademark-copyright-patent --words 1850
Cixis: Episodes\\<slug>\\script.md  (+ meta.json)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import LLMError, add_provider_arg, chat, chat_json  # noqa: E402
from math_check import check_file as check_math  # noqa: E402

EPISODES = r"C:\YouTubeAI\Episodes"
WORDS_MIN, WORDS_MAX = 1700, 2050
WPM = 199.0          # OLCULMUS: Kokoro am_fenrir speed=1.0 -> 199 soz/deq (1550 soz = 7.8 deq danisiq)
OVERSHOOT = 1.18     # model hedefin ~85-95%-ni verir - bolme hedefleri bu qeder boyudulur
SHORT_RATIO = 0.90   # bolme hedefin bu qederinden az cixarsa yenidden yazdirilir
LENGTH_MARGIN = 1.05  # TTS bosluqlarina ve tehmin xetasina ehtiyat
# OLCULMUS: video uzunlugu (intro/basliq/outro + pauzalar daxil) skript sozune gore - 2402 soz -> 935 s,
# 2364 soz -> 967 s. Xalis 199 wpm ile hesablananda video 16 deq cixirdi (hedef 8-10 deq).
EFFECTIVE_WPM = 150.0
MIN_SECTION_WORDS = 110  # qisaldilan bolme bundan az olmur - analogiya + misal yerlesmelidir
OUTLINE_ATTEMPTS = 5      # #59: plan qaydalari pozulsa (qeyri-mueyyen cavab, ABS-dan kenar case) yeniden

SYSTEM = """You write scripts for an ELI5 Business YouTube channel.
The audience is ADULT business owners and managers in the United States (B2B): owners of small and mid-sized
companies - shops, restaurants, agencies, contractors, clinics, e-commerce brands, service firms. Every video
helps a business owner make ONE concrete business decision. The host is an owl in a suit who explains in plain,
simple words - clear for a beginner, but always respectful and grown-up, never childish or talking down.

Voice and rules:
- Second person, warm, conversational. Short sentences. Contractions are fine.
- One running case is followed from the first minute to the last: the business owner named in the plan. Each
  section moves that story forward. Every example, number and story is about that business. An analogy is ONE
  short sentence from everyday life (a thermostat, a GPS route), without numbers - never another business,
  company, owner or industry (no "a chef", "a trucking company", "a car dealer"), and each is used only once.
- Say each figure at most twice in the whole script; after that refer to it in words ("the new price").
- United States only: US cities and states, US dollars, US institutions (IRS, SBA), US spelling.
  Never examples from a child's world (toys, allowance, classmates, candy, playgrounds).
- Introduce each English business term once, then define it correctly in one short sentence.
- Never repeat an example, a story beat or an explanation that was already told.
- No filler, no "in today's video we will", no sponsor reads, no emojis, no stage directions.
- Write every figure in digits: "$4,000", "$9.99", "15%", "2,500 customers" - never spell amounts out.
- Never invent statistics, studies, company figures or laws. The ONLY research you may cite is the verified
  fact given to you, with its source name. The case numbers are an illustration, not data.
- Every calculation must be correct and easy to follow: use round numbers, say the inputs before
  the result, and do one step at a time. Name time conversions explicitly ("over four weeks",
  "over twelve months"). Check each result twice before writing it.
- State every input of a computed figure before the result, in the same paragraph: count, price,
  hours, period. Never give a total that depends on an unstated quantity (e.g. earnings of clients
  paid per hour when the hours are not said). Keep worked examples in whole numbers; do not multiply
  prices like 49.99 - compare such prices only by their difference.
- Output is narration text only - it will be read aloud word for word by a TTS voice.
  Do not write anything a narrator would not say out loud."""

OUTLINE_USER = """Topic: {topic}

Plan a ~11 minute ELI5 explainer for US business owners. If the topic sounds like consumer or personal finance,
reframe it as the decision a US small-business owner faces about it (B2B). Return JSON only:

{{"decision": "the ONE concrete decision the owner makes, as a question starting with Should, When, How or Which",
  "case": {{"owner": "first name", "business": "the kind of business, no numbers",
            "city": "a US city", "state": "its US state, full name",
            "situation": "the owner's starting numbers in one sentence - exactly the values of the model variables"}},
  "model": {{"variables": [{{"name": "snake_case_name", "value": "a round JSON number",
                             "unit": "$ for money, % for a percentage, share for a fraction between 0 and 1, or a plural noun such as customers",
                             "label": "short plain-English label"}}],
            "before": {{}}, "after": {{}},
            "threshold": {{"name": "snake_case_name", "expr": "formula", "rounding": "ceil, floor, round or none",
                           "meaning": "what the threshold means for this decision, plain words"}}}},
  "answer": "the rule the video ends with: one sentence 'Make the change if/when ...' with the threshold value
computed by the model as the condition the owner can check - never vague advice like 'find a balance'",
  "fact_need": "which official statistic would help this decision, one short phrase",
  "source_section": 2,
  "sections": [
  {{"title": "short title, max 5 words",
    "idea": "the one core idea this section teaches, one sentence",
    "term": "the key business term of this section", "definition": "its correct one-sentence definition",
    "domain": "the everyday adult world the analogy lives in, two or three words",
    "analogy": "the analogy used, one sentence",
    "case_step": "what happens to the owner's business in this section, one sentence, no numbers"}}
]}}

Exactly 4 sections. They build on each other: the first establishes the foundation, the last answers the
decision for the owner. No overlap between sections.

CRITICAL - the case model of THIS decision: 3 to 7 input variables with round values (inputs only - never a
precomputed result). "model.before" and "model.after" are objects whose KEYS are result names you choose for this
decision (such as monthly_cost, weekly_profit, hours_saved) and whose VALUES are formulas over the variable names;
"after" (the owner makes the change) uses the same keys as "before" (today). "threshold.expr" is the break-even
formula and may use the variables and before_<key>, after_<key>, delta_<key>. The answer states exactly the
threshold value this formula gives. Formulas use ONLY variable names, numbers and + - * / ( ). Include EVERY factor the decision depends on (for example customers who leave after a price change,
or the cost of each extra unit) - a calculation that ignores one of them is wrong. Profit is always revenue minus
costs. When the change ADDS a cost (hiring, new equipment, a second location), "after" also includes what that cost
brings (for example extra customers served or extra hours sold), and the threshold is the amount of it that pays
for the cost. Every case number in the
video is a model variable or follows from the model; never add numbers outside it. The threshold is the
break-even point of the decision, computed by the model. Analogies never contain numbers.

CRITICAL - variety: each section's analogy uses a DIFFERENT everyday domain, none shared - never another business
or industry (the case is the only business in the video). Pick four genuinely different everyday adult images,
for example: a home thermostat, a car's fuel gauge, a GPS route, a household budget, a fitness tracker, a weather
forecast, a hiking trail map, a home renovation. Never the same object twice."""

# (basliq, soz hedefi, telimat) - {owner}, {business}, {city}, {state}, {decision}, {answer} plandan doldurulur
BLOCKS: list[tuple[str, int, str]] = [
    ("Hook", 80,
     "Introduce {owner}, the owner of {business} in {city}, {state}, and the decision: {decision} Ask it as "
     "a question. Then state what the viewer will be able to decide by the end. Do not repeat the opening "
     "sentence of the video. No greeting, no channel name, no 'in this video'."),
    ("Common Mistakes", 170,
     "Three mistakes US business owners make with this decision. For each: the mistake, why it feels "
     "reasonable, and the fix. Use NEW one-line situations - never {owner}'s case again, never an earlier "
     "analogy, example or number."),
    ("Recap", 60,
     "Only the conclusions: the three rules worth remembering, stated plainly as rules the viewer can apply, "
     "in the order they were taught. No examples, no stories, no names, no numbers, no new information."),
    ("Call to Action", 45,
     "Invite a comment describing their own business decision, and name one related next topic. Warm, not pushy."),
]

WRITE_USER = """Topic: {topic}

Full outline of the video (for context and continuity only):
{outline}

Now write ONLY the section "{heading}".
Target length: {words} words. This is a hard requirement - count as you write.
{guidance}

Write flowing narration paragraphs separated by blank lines.
Do not write the heading. No bullet lists, no bold, no italics, no headings, no meta commentary.
{tail}"""

EXTEND_USER = """Topic: {topic}

The video already has these teaching sections:
{existing}

Plan ONE additional teaching section that deepens the topic without repeating any of them.
Its analogy must live in an everyday domain different from all of these: {domains} - never another business or
industry; the case business is the only example.
Return JSON only:
{{"title": "short title, max 5 words", "idea": "the one core idea, one sentence",
  "domain": "the everyday world the analogy lives in, two or three words",
  "analogy": "the everyday analogy used, one sentence"}}"""


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())).strip("-")[:60]


def word_count(markdown: str) -> int:
    """Yalniz narration sozleri - basliq setirleri sayilmir."""
    body = "\n".join(ln for ln in markdown.splitlines() if not ln.lstrip().startswith("#"))
    return len(body.split())


def check_headings(markdown: str) -> list[str]:
    required = ["## Cold Open", "## Hook", "## Section 1", "## Section 2", "## Section 3", "## Section 4",
                "## Common Mistakes", "## Recap", "## Call to Action"]
    return [h for h in required if h not in markdown]


def words_to_add(current: int, min_seconds: float, wpm: float = EFFECTIVE_WPM,
                 margin: float = LENGTH_MARGIN) -> int:
    """min_seconds video ucun catismayan soz sayi (0 = kifayetdir)."""
    return max(0, math.ceil(min_seconds / 60.0 * wpm * margin) - current)


def words_to_cut(current: int, max_seconds: float, wpm: float = EFFECTIVE_WPM, margin: float = 0.97) -> int:
    """max_seconds-i asmamaq ucun atilmali soz sayi (0 = sigir)."""
    return max(0, current - math.floor(max_seconds / 60.0 * wpm * margin))


def words_for_seconds(seconds: float, wpm: float = EFFECTIVE_WPM, margin: float = 1.10) -> int:
    return math.ceil(seconds / 60.0 * wpm * margin)


_SECTION = re.compile(r"^## (Section \d+: [^\n]+)\n(.*?)(?=^## |\Z)", re.M | re.S)


def shorten(markdown: str, cut: int, rewrite) -> str:
    """En uzun tedris bolmelerini rewrite(heading, body, target_words) ile qisaldir, cemi `cut` soz
    atilana qeder. Hook / Mistakes / Recap / CTA toxunulmur."""
    sections = sorted(((m[1], m[2].strip()) for m in _SECTION.finditer(markdown)),
                      key=lambda hb: -len(hb[1].split()))
    left = cut
    for heading, body in sections:
        if left <= 0:
            break
        n = len(body.split())
        target = max(MIN_SECTION_WORDS, n - left)
        if target >= n:
            continue
        new = rewrite(heading, body, target).strip()
        markdown = markdown.replace(body, new, 1)
        left -= n - len(new.split())
    return markdown


def teaching_headings(markdown: str) -> list[str]:
    return re.findall(r"^## (Section \d+: .+)$", markdown, flags=re.M)


def insert_before(markdown: str, anchor: str, block: str) -> str:
    idx = markdown.find("\n" + anchor)
    if idx < 0:
        raise ValueError(f"anchor tapilmadi: {anchor}")
    return markdown[:idx].rstrip() + "\n\n" + block.strip() + "\n" + markdown[idx:]


_ANSWER_PROBLEM = "cavab"     # plan_problems-in cavaba aid qeydleri ("cavabdaki reqem", "cavab ... threshold")
ANSWER_USER = """Decision: {decision}
Case: {owner}, {business}. {situation}
The case model computed this threshold: {meaning} = {value}.
Write the rule the video ends with: ONE sentence that starts with "Make the change if" or "Make the change when"
and uses exactly {value} as the condition the owner can check. No other numbers. Return only the sentence."""


def answer_from_model(plan: dict, **llm_kw) -> str:
    """Faza 1.1 (real probe 2026-10-07): cavab modelin HESABLANMIS threshold-u ile yazilir."""
    import case_model
    r = case_model.evaluate(plan["model"])
    t = r["threshold"]
    case = plan.get("case") or {}
    return " ".join(chat(SYSTEM, ANSWER_USER.format(
        decision=plan.get("decision"), owner=case.get("owner"), business=case.get("business"),
        situation=case.get("situation", ""), meaning=t["meaning"], value=case_model.fmt(t["value"], t["unit"])),
        max_tokens=120, **llm_kw).strip().strip('"').split())


MODEL_REVIEW_MODEL = "gpt-4o"      # yoxlama modeli (istifadeci: metn gpt-4o-mini, yoxlamalar gpt-4o)
MODEL_REVIEW_SYSTEM = """You check the numeric case model behind a business explainer video for US small-business
owners. A program already computed the values; you judge only whether the model is RIGHT for the decision.
Answer ONLY JSON: {"ok": bool, "problems": ["..."]}
Names before_<key>, after_<key> and delta_<key> are defined automatically for every result key, and "after" may
refer to a key's before value by its own name. The COMPUTED values are already correct arithmetic.
It is a simple teaching model: accept simplifications and modelling choices. Set ok to false ONLY for a clear,
objective ERROR:
- a formula does not compute what its result name says, or adds different units (customers + dollars);
- the change itself is missing from "after" (e.g. hiring with no wage cost, a price rise with no new price,
  a discount that changes nothing);
- "after" ignores a model VARIABLE that describes the effect of the change (e.g. a stay_share variable exists but
  "after" uses all customers);
- a formula uses an unexplained constant that is not a unit conversion (4 weeks, 12 months, 100 for percent);
- the threshold formula does not compute what its meaning says.
Never reject for missing extra factors that have no variable, profit vs break-even, "at least" vs "more than", or
realism. Never ask to use the threshold inside before/after (the threshold is computed from them).
problems: one short concrete fix per error (empty when ok)."""


def review_model(plan: dict, **llm_kw) -> list[str]:
    """Faza 1.1: gpt-4o modelin qerara uygunlugunu yoxlayir - fail-closed (cavab yoxdursa redd)."""
    import case_model
    r = case_model.evaluate(plan["model"])
    user = (f"Decision: {plan.get('decision')}\nAnswer: {plan.get('answer')}\nCase: {plan.get('case')}\n"
            f"MODEL: {json.dumps(plan['model'], ensure_ascii=False)}\nCOMPUTED:\n{case_model.figures_text(r)}")
    kw = {k: v for k, v in llm_kw.items() if k not in ("model", "temperature")}
    if kw.get("provider", "openai") == "openai":
        kw["model"] = MODEL_REVIEW_MODEL
    try:
        got = chat_json(MODEL_REVIEW_SYSTEM, user, temperature=0, max_tokens=600, **kw)
    except LLMError as e:
        return [f"model yoxlamasi alinmadi: {str(e)[:100]}"]
    if got.get("ok") is True:
        return []
    probs = [str(p) for p in got.get("problems") or [] if str(p).strip()]
    return ["case model qerara uygun deyil (gpt-4o): " + "; ".join(probs or ["sebeb verilmedi"])]


MODEL_REPAIRS = 2
MODEL_REPAIR_SYSTEM = """You fix the numeric case model of a business explainer video. Apply the listed fixes
exactly and change nothing else. Formulas use ONLY variable names, numbers and + - * / ( ); "before"/"after" map
result names to formulas; threshold.expr may use variables and before_<key>, after_<key>, delta_<key>.
Return JSON only: {"model": {...the whole corrected model...}}"""


# #106: gpt-4o-mini xerc elave eden qerarda (isci, avadanliq) modeli 5 cehdde hakimden kecire bilmirdi - isleyen
# numune (yalniz STRUKTUR; reqemler case-in oz reqemleri olmalidir). Numune butun deterministik qaydalardan kecir.
MODEL_EXAMPLE = {
    "variables": [{"name": "monthly_jobs", "value": 40, "unit": "jobs", "label": "jobs done each month"},
                  {"name": "price_per_job", "value": 300, "unit": "$", "label": "price per job"},
                  {"name": "cost_per_job", "value": 60, "unit": "$", "label": "material cost per job"},
                  {"name": "fixed_costs", "value": 2000, "unit": "$", "label": "monthly fixed costs"},
                  {"name": "extra_jobs", "value": 30, "unit": "jobs", "label": "extra jobs the hire makes possible"},
                  {"name": "employee_cost", "value": 4800, "unit": "$", "label": "monthly cost of the employee"}],
    "before": {"monthly_profit": "monthly_jobs * (price_per_job - cost_per_job) - fixed_costs"},
    "after": {"monthly_profit": "(monthly_jobs + extra_jobs) * (price_per_job - cost_per_job) - fixed_costs "
                                "- employee_cost"},
    "threshold": {"name": "extra_jobs_needed", "expr": "employee_cost / (price_per_job - cost_per_job)",
                  "rounding": "ceil", "meaning": "extra jobs per month needed to pay for the employee"},
}


def model_example_text() -> str:
    return ("\n\nEXAMPLE of a correct case model for a decision that ADDS a cost (structure only - use this case's "
            "own variables and numbers, never these):\n" + json.dumps(MODEL_EXAMPLE, ensure_ascii=False))


def repair_model(plan: dict, why: list[str], **llm_kw) -> dict:
    """Yalniz model JSON-u duzeldilir (real probe: butun plan yeniden yazilanda mini duzelisi tetbiq etmirdi)."""
    import case_model
    user = (f"Decision: {plan.get('decision')}\nCase: {plan.get('case')}\nProblems to fix:\n- "
            + "\n- ".join(why) + f"\n{case_model.names_hint(plan.get('model'))}\n\nMODEL:\n"
            + json.dumps(plan.get("model"), ensure_ascii=False) + model_example_text())     # #106
    kw = {k: v for k, v in llm_kw.items() if k not in ("model", "temperature")}
    if kw.get("provider", "openai") == "openai":
        kw["model"] = MODEL_REVIEW_MODEL     # yoxlama qatinin duzelisi (number_audit kimi) - mini cebri duzelde bilmirdi
    got = chat_json(MODEL_REPAIR_SYSTEM, user, temperature=0, max_tokens=1500, **kw)
    return got.get("model") if isinstance(got.get("model"), dict) else plan.get("model")


def settle_plan(data: dict, **llm_kw) -> tuple[dict, list[str]]:
    """Plan yoxlamalari: deterministik (plan_problems) -> cavab hesablanmis threshold ile -> gpt-4o model
    yoxlamasi; model xetasinda en cox MODEL_REPAIRS defe yalniz model duzeldilir. -> (plan, qalan problemler)."""
    from script_qa import plan_problems
    why: list[str] = []
    for r in range(MODEL_REPAIRS + 1):
        why = plan_problems(data)
        if why and all(_ANSWER_PROBLEM in p for p in why):
            data = {**data, "answer": answer_from_model(data, **llm_kw)}   # LLM threshold-u ozu hesablaya bilmir
            why = plan_problems(data)
        if not why:
            why = review_model(data, **llm_kw)
        if not why or r == MODEL_REPAIRS or not any("model" in w for w in why):
            return data, why
        print(f"  model duzelisi: {why}", flush=True)
        data = {**data, "model": repair_model(data, why, **llm_kw)}
    return data, why


def outline(topic: str, **llm_kw) -> dict:
    """Plan (#59): biznes qerari + cavab + bir ABS case + Cold Open + 4 bolme. Sert sxem - pozulsa LLMError.
    Plan qaydalari (sual-qerar, ABS, sertli cavab) pozulsa sebebi ile yeniden istenir (OUTLINE_ATTEMPTS)."""
    from script_qa import plan_problems
    base = OUTLINE_USER.format(topic=topic) + model_example_text()       # #106: isleyen model numunesi
    user = base
    for _ in range(OUTLINE_ATTEMPTS):
        data, why = settle_plan(chat_json(SYSTEM, user, max_tokens=2000, **llm_kw), **llm_kw)
        if not why:
            break
        print(f"  plan redd: {why}")
        if any("model" in w for w in why):
            # real probe 2026-10-07: kohne plan geri oturulende mini eyni sehv modeli tekrarlayirdi - teze baslanir
            user = (base + "\n\nA previous attempt was rejected because: "
                    + "; ".join(why) + "\nBuild a NEW, simpler case model that avoids this mistake.")
        else:
            user = (base + "\n\nYour previous plan was rejected: " + "; ".join(why)
                    + "\nPrevious plan: " + json.dumps(data, ensure_ascii=False)[:2500])
    else:
        raise LLMError(f"plan qaydalara uygun gelmedi: {why}")
    sections = data.get("sections") or []
    if len(sections) != 4:
        raise LLMError(f"outline 4 bolme qaytarmalidir, qaytardi: {len(sections)}")
    case = data.get("case") if isinstance(data.get("case"), dict) else {}
    if not all(str(case.get(k) or "").strip() for k in ("owner", "business", "city", "state")):
        raise LLMError(f"outline case natamamdir: {case}")
    try:
        src_sec = min(4, max(1, int(data.get("source_section") or 2)))
    except (TypeError, ValueError):
        src_sec = 2
    import case_model
    return {**data, "case": case, "sections": sections, "source_section": src_sec,
            "model_result": case_model.evaluate(data["model"])}   # Faza 1.1: plan_problems hesabi yoxlayib


def _write_block(topic: str, outline_text: str, heading: str, words: int,
                 guidance: str, tail: str, **llm_kw) -> str:
    """Bir bolmeni yazir; qisa cixarsa bir defe genislendirmeye gonderir."""
    words = round(words * OVERSHOOT)
    user = WRITE_USER.format(topic=topic, outline=outline_text, heading=heading,
                             words=words, guidance=guidance, tail=tail)
    text = chat(SYSTEM, user, max_tokens=min(4000, words * 4), **llm_kw)
    n = len(text.split())
    if n < words * SHORT_RATIO:
        text = chat(SYSTEM, f"{user}\n\n---\nYour draft was {n} words, too short. Rewrite it at "
                            f"{words} words by deepening the analogy and the example. "
                            f"Return only the rewritten section.",
                    max_tokens=min(4000, words * 4), **llm_kw)
    return text.strip()


def _fill(template: str, plan: dict) -> str:
    case = plan["case"]
    return template.format(owner=case["owner"], business=case["business"], city=case["city"],
                           state=case["state"], decision=plan.get("decision", ""), answer=plan.get("answer", ""))


def outline_text(plan: dict) -> str:
    case = plan["case"]
    head = (f"DECISION: {plan.get('decision')}\nANSWER: {plan.get('answer')}\n"
            f"CASE: {case['owner']}, {case['business']} in {case['city']}, {case['state']}. "
            f"{case.get('situation', '')}\n")
    if isinstance(plan.get("model_result"), dict):      # Faza 1.1: case reqemleri yalniz modelden
        import case_model
        head += ("CASE MODEL - the only case figures allowed in the script:\n"
                 + case_model.figures_text(plan["model_result"]) + "\n")
    return head + "\n".join(
        f"{i + 1}. {s.get('title', '')} [{s.get('domain', '')}] - {s.get('idea', '')} "
        f"Term: {s.get('term', '')} = {s.get('definition', '')} Analogy: {s.get('analogy', '')} "
        f"Case: {s.get('case_step', '')}"
        for i, s in enumerate(plan["sections"]))


COLD_OPEN_USER = """Write the first sentence of a video for US business owners. Decision of the video: {decision}
Case: {owner}, {business} in {city}, {state}. {situation}
Rules: at most 12 words; a concrete number in digits within the first 6 words (or a paradox with a number);
plain spoken English; no question about the channel. Earlier attempt (rejected: {why}): {previous}
Return only the sentence."""


def make_cold_open(plan: dict, attempts: int = 3, **llm_kw) -> str:
    """#56: ilk 3 saniyede konkret reqem/paradoks - yoxlanir (cold_open_problems), olmasa yeniden yazdirilir."""
    from script_qa import cold_open_problems
    result = plan.get("model_result") if isinstance(plan.get("model_result"), dict) else None
    allowed = None
    if result:                                   # Faza 1.2: cold open = modelin en teeccublu neticesi
        import case_model
        allowed = case_model.allowed_numbers(result)
        line = " ".join(str(result.get("insight") or "").split())
        if not cold_open_problems(line, allowed):
            return line
    line = " ".join(str(plan.get("cold_open") or "").split())
    for _ in range(attempts):
        why = cold_open_problems(line, allowed)
        if not why:
            return line
        case = plan["case"]
        line = " ".join(chat(SYSTEM, COLD_OPEN_USER.format(
            decision=plan.get("decision"), owner=case["owner"], business=case["business"], city=case["city"],
            state=case["state"], situation=case.get("situation", ""), why="; ".join(why), previous=line or "-")
            + (f"\nUse only figures from this case model:\n{case_model.figures_text(result)}" if result else ""),
            max_tokens=80, **llm_kw).strip().strip('"').split())
    if cold_open_problems(line, allowed):
        raise LLMError(f"Cold Open qaydaya uygun yazilmadi: {line!r}")
    return line


def hook_figures(plan: dict) -> str:
    """Real probe 2026-10-07: model reqemleri her bolmede tekrarlanirdi. Baslangic deyisenleri yalniz Hook-da."""
    r = plan.get("model_result")
    if not isinstance(r, dict):
        return ""
    import case_model
    lines = [f"- {case_model._label(r, k)}: {case_model.fmt(v, r['var_units'].get(k, ''))}"
             for k, v in r["variables"].items()]
    return ("\nState the owner's starting figures here, each once, exactly as given (later sections refer to them "
            "in words):\n" + "\n".join(lines))


def _section_guidance(plan: dict, s: dict, i: int, source: dict | None) -> str:
    owner = plan["case"]["owner"]
    g = (f"Core idea: {s.get('idea', '')}\n"
         f"Key term: {s.get('term', '')} - define it exactly like this: {s.get('definition', '')}\n"
         f"Use ONLY this analogy domain, once: {s.get('domain', '')} - {s.get('analogy', '')}\n"
         f"Move the case forward: {s.get('case_step', '')} Mention {owner} by name.\n"
         f"Do not re-introduce {owner} or the business and do not restate figures already given - the viewer "
         f"knows them; only add what is new in this section.\n"
         f"Do not restate the analogy - after introducing it, keep teaching the idea and the case.")
    if source and i == plan["source_section"]:
        g += (f"\nCite this verified fact ONCE, naming the source and the figure exactly: According to "
              f"{source['cite_as']}, {source['claim']}")
    if i < len(plan["sections"]) and isinstance(plan.get("model_result"), dict):
        g += ("\nDo not state any case figure in this section: the Hook already gave the starting numbers and the "
              "final section gives the results - here refer to them in words (the current price, the regular "
              "customers). Every figure is said at most twice in the whole video.")
    if i == len(plan["sections"]):
        g += f"\nEnd by answering the decision for {owner} with this rule: {plan.get('answer', '')}"
        if isinstance(plan.get("model_result"), dict):
            import case_model
            g += ("\nUse exactly these figures for the decision - before, after, the change and the threshold - "
                  "and no other results. Say them in natural spoken sentences; never copy the labels or the words "
                  "'before'/'after' below as written (#103):\n" + case_model.figures_text(plan["model_result"]))
    return g


def generate(topic: str, words: int, plan: dict, source: dict | None, **llm_kw) -> tuple[str, list[str]]:
    """Bolme-bolme generasiya: model uzun metnde soz hedefini tutmur, ona gore paralanir."""
    secs = plan["sections"]
    text_outline = outline_text(plan)
    domains = [str(s.get("domain", "")).strip() for s in secs]
    print("  qerar:", plan.get("decision"), "| case:", plan["case"]["owner"], "-", plan["case"]["business"],
          f"({plan['case']['city']}, {plan['case']['state']})")
    print("  analogiya saheleri:", ", ".join(d for d in domains if d))

    body_words = words - sum(w for _, w, _ in BLOCKS)
    per_section = max(150, round(body_words / len(secs)))
    parts: list[str] = [f"# {topic}", "## Cold Open", make_cold_open(plan, **llm_kw)]

    hook_h, hook_w, hook_g = BLOCKS[0]
    print(f"  [{hook_h}] {hook_w} soz")
    parts += [f"## {hook_h}",
              _write_block(topic, text_outline, hook_h, hook_w, _fill(hook_g, plan) + hook_figures(plan),
                           f"The opening sentence already said: \"{parts[2]}\" - do not repeat it. The teaching "
                           "sections use these analogy domains: " + ", ".join(d for d in domains if d)
                           + ". Do NOT use any of them here.", **llm_kw)]

    for i, s in enumerate(secs, 1):
        title = str(s.get("title", f"Part {i}")).strip()
        heading = f"Section {i}: {title}"
        others = [d for j, d in enumerate(domains, 1) if d and j != i]
        print(f"  [{heading}] {per_section} soz  <{s.get('domain', '')}>")
        parts += [f"## {heading}",
                  _write_block(topic, text_outline, heading, per_section, _section_guidance(plan, s, i, source),
                               "Sections before this one are already written - do not repeat them. "
                               "These domains belong to OTHER sections and are forbidden here: "
                               + ", ".join(others) + ".",
                               **llm_kw)]

    for heading, w, guidance in BLOCKS[1:]:
        print(f"  [{heading}] {w} soz")
        parts += [f"## {heading}",
                  _write_block(topic, text_outline, heading, w, _fill(guidance, plan),
                               "All four teaching sections are already written above. Never re-explain their "
                               "analogies, examples or numbers.", **llm_kw)]

    return "\n\n".join(parts), domains


def extend(topic: str, markdown: str, words: int, domains: list[str], plan: dict | None = None,
           **llm_kw) -> tuple[str, str]:
    """Movcud skripte Common Mistakes-den evvel yeni tedris bolmesi elave edir -> (skript, domain).
    #59: yeni bolme de eyni case-i davam etdirir."""
    existing = teaching_headings(markdown)
    sec = chat_json(SYSTEM, EXTEND_USER.format(topic=topic, existing="\n".join(existing) or "(none)",
                                               domains=", ".join(domains) or "(unknown)"),
                    max_tokens=600, **llm_kw)
    heading = f"Section {len(existing) + 1}: {str(sec.get('title', 'One More Thing')).strip()}"
    owner = ((plan or {}).get("case") or {}).get("owner")
    guidance = (f"Core idea: {sec.get('idea', '')}\n"
                f"Use ONLY this analogy domain, once: {sec.get('domain', '')} - {sec.get('analogy', '')}\n"
                + (f"Continue the case of {owner}: what happens to {owner}'s business now. Mention {owner} by name.\n"
                   if owner else "")
                + "This section comes BEFORE the final decision section: do not make or announce the final "
                  "decision, and keep every fact consistent with the sections already written.\n"
                + "Teach the one idea, make it concrete, then hand off to the next section.")
    print(f"  [{heading}] {words} soz  <{sec.get('domain', '')}>")
    body = _write_block(topic, (outline_text(plan) + "\n\nSCRIPT SO FAR:\n" + markdown) if plan
                        else "\n".join(existing + [heading]), heading, words,
                        guidance, "Every other section is already written. Do not repeat their ideas, examples, "
                        "analogies or numbers.", **llm_kw)
    # E2E 2026-10-05: qerardan SONRA elave olunan bolme ziddiyyet yaratdi - son (qerar) bolmesinden evvele
    anchor = f"## {existing[-1]}" if existing else "## Common Mistakes"
    return renumber_sections(insert_before(markdown, anchor, f"## {heading}\n\n{body}")), \
        str(sec.get("domain", "")).strip()


def renumber_sections(markdown: str) -> str:
    """'## Section N: ...' basliqlari sira ile 1..n."""
    counter = iter(range(1, 1000))
    return re.sub(r"^## Section \d+:", lambda m: f"## Section {next(counter)}:", markdown, flags=re.M)


SHORTEN_USER = """Topic: {topic}

Rewrite this section of the video script ("{heading}") to about {words} words.
Keep the core idea, the same analogy, the case person and every sourced fact with its source name; cut
repetition and side remarks first. Write figures in digits.
Write flowing narration paragraphs separated by blank lines. No heading, no lists, no meta commentary.

Current text:
{body}"""


def verify_math(a: argparse.Namespace, script_path: str) -> None:
    """Skript her yazilandan sonra hesablamalar yoxlanir/duzelir; qalan sehv merheleni dayandirir."""
    try:
        problems = check_math(script_path, provider=a.provider, model=a.model)
    except LLMError as e:
        raise SystemExit("hesablama yoxlamasi xetasi: " + str(e)) from e
    if problems:
        raise SystemExit(f"{len(problems)} hesablama sehvi duzelmedi - bax: math_check.json")


def _load_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def quality_gate(a: argparse.Namespace, out_dir: str, script_path: str) -> None:
    """#59: deterministik hekaye/menbe/hook duzelisleri -> gpt-4o redaktor -> reqem auditi -> son yoxlama.
    script_qa.json (sha) yazilir; problem qalsa merhele dayanir."""
    import script_qa as qa
    plan = _load_json(os.path.join(out_dir, "meta.json")).get("plan") or {}
    source = _load_json(os.path.join(out_dir, "research.json")) or None
    if not plan:
        raise SystemExit("meta.json-da plan yoxdur - skript --force ile yeniden yazilmalidir")
    kw = {"provider": a.provider, "model": a.model, "temperature": a.temperature}
    with open(script_path, encoding="utf-8") as f:
        script = f.read()
    src_head = next((h for h in teaching_headings(script) if h.startswith(f"Section {plan.get('source_section', 2)}:")),
                    (teaching_headings(script) or ["Section 2"])[0])
    try:
        for _ in range(qa.REVIEW_ROUNDS):
            fixes = qa.story_fixes(script, plan, source, src_head)
            if not fixes:
                break
            script = qa.apply_fixes(script, plan, fixes, chat, **kw)
        script, review = qa.review_loop(script, plan, source, a.topic, review=chat_json, rewrite=chat,
                                        provider=a.provider)
        for _ in range(qa.REVIEW_ROUNDS):            # redaktor hekaye xettini/menbeni poza biler
            fixes = qa.story_fixes(script, plan, source, src_head)
            if not fixes:
                break
            script = qa.apply_fixes(script, plan, fixes, chat, **kw)
        script = qa.settle_script(script, plan, source)   # #105/#107: deterministik
    except LLMError as e:
        raise SystemExit("ssenari keyfiyyet yoxlamasi xetasi: " + str(e)) from e
    for _ in range(2):                               # #107: audit cutu parcalasa elave olunur, audit tekrar (sha)
        with open(script_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(script.rstrip() + "\n")
        verify_math(a, script_path)                  # reqem auditi abzaslari yeniden yaza biler -> sonra son yoxlama
        with open(script_path, encoding="utf-8") as f:
            script = f.read()
        settled = qa.settle_script(script, plan, source)
        if settled == script:
            break
        script = settled
    with open(script_path, encoding="utf-8") as f:
        script = f.read()                            # son hokm yalniz audit olunmus fayla
    problems = check_headings_problems(script) + qa.story_problems(script, plan, source) + review
    qa.write_report(out_dir, script, problems, decision=plan.get("decision"), case=plan.get("case"),
                    source=(source or {}).get("url"))
    print(f"  ssenari keyfiyyeti: {'OK' if not problems else problems}")
    if problems:
        raise SystemExit(f"{len(problems)} ssenari keyfiyyet problemi qaldi - bax: script_qa.json")


def check_headings_problems(markdown: str) -> list[str]:
    missing = check_headings(markdown)
    return [f"catismayan basliqlar: {', '.join(missing)}"] if missing else []


def run_shorten(a: argparse.Namespace, out_dir: str, script_path: str) -> None:
    if not os.path.isfile(script_path):
        raise SystemExit("qisaltmaq ucun script.md yoxdur: " + script_path)
    with open(script_path, encoding="utf-8") as f:
        current = f.read()
    print(f"[22-] skript qisaldilir: -{a.shorten} soz")

    def rewrite(heading: str, body: str, target: int) -> str:
        print(f"  [{heading}] {len(body.split())} -> {target} soz")
        return chat(SYSTEM, SHORTEN_USER.format(topic=a.topic, heading=heading, words=target, body=body),
                    max_tokens=min(4000, target * 4), provider=a.provider, model=a.model,
                    temperature=a.temperature)

    try:
        script = shorten(current, a.shorten, rewrite)
    except LLMError as e:
        raise SystemExit("qisaltma xetasi: " + str(e)) from e
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script.rstrip() + "\n")
    n = word_count(script)
    print(f"  {n} soz  ~{n / EFFECTIVE_WPM:.1f} deq video -> {script_path}")
    quality_gate(a, out_dir, script_path)


def run_extend(a: argparse.Namespace, out_dir: str, script_path: str) -> None:
    if not os.path.isfile(script_path):
        raise SystemExit("uzatmaq ucun script.md yoxdur: " + script_path)
    meta_path = os.path.join(out_dir, "meta.json")
    meta = _load_json(meta_path)
    print(f"[22+] skript uzadilir: +{a.extend} soz")
    with open(script_path, encoding="utf-8") as f:
        current = f.read()
    try:
        script, domain = extend(a.topic, current, a.extend, meta.get("domains", []), meta.get("plan"),
                                provider=a.provider, model=a.model, temperature=a.temperature)
    except (LLMError, ValueError) as e:
        raise SystemExit("uzatma xetasi: " + str(e)) from e
    n = word_count(script)
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script.rstrip() + "\n")
    meta = {**meta, "words": n, "est_minutes": round(n / EFFECTIVE_WPM, 1),
            "domains": [*meta.get("domains", []), domain]}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  {n} soz  ~{n / EFFECTIVE_WPM:.1f} deq video -> {script_path}")
    quality_gate(a, out_dir, script_path)


def find_source(a: argparse.Namespace, plan: dict, out_dir: str) -> dict:
    """#58: yoxlanmis resmi/tedqiqat menbe - olmasa merhele dayanir (data uydurulmur)."""
    from research import research
    path = os.path.join(out_dir, "research.json")
    cached = _load_json(path)
    if cached:
        return cached
    print(f"  menbe axtarilir: {plan.get('fact_need', '')}")
    # hakim QERARA gore baxir; dar fact_need yalniz axtaris ipucudur (E2E: 48% qiymet artimi redd olunmusdu)
    src = research(a.topic, str(plan.get("decision", "")), fact_need=str(plan.get("fact_need", "")))
    if not src:
        raise SystemExit("yoxlanmis resmi/tedqiqat menbe tapilmadi (#58) - run.py --resume ile yeniden cehd et")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(src, f, indent=2, ensure_ascii=False)
    print(f"  menbe: {src['cite_as']} - {src['claim']} ({src['url']})")
    return src


def needs_regeneration(out_dir: str) -> bool:
    """Movcud script.md keyfiyyet/hesab qapisindan kecmeyibse (merhele retry-i --force-suz gelir) yeniden yazilir."""
    import script_qa
    from math_check import report_problems
    return bool(script_qa.report_problems(out_dir) or report_problems(out_dir))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--slug", help="default: movzudan yaradilir")
    ap.add_argument("--words", type=int, default=1530)   # ~11 deq video (pipeline.DEFAULT_WORDS)
    ap.add_argument("--extend", type=int, metavar="SOZ",
                    help="movcud script.md-ye bu qeder sozluk yeni tedris bolmesi elave et")
    ap.add_argument("--shorten", type=int, metavar="SOZ",
                    help="movcud script.md-nin en uzun tedris bolmelerini bu qeder soz qisalt")
    ap.add_argument("--force", action="store_true", help="movcud script.md uzerine yaz")
    add_provider_arg(ap)
    a = ap.parse_args()

    slug = a.slug or slugify(a.topic)
    if not slug:
        raise SystemExit("slug bos alindi - --slug ile ver")
    out_dir = os.path.join(EPISODES, slug)
    script_path = os.path.join(out_dir, "script.md")
    if a.extend:
        run_extend(a, out_dir, script_path)
        return
    if a.shorten:
        run_shorten(a, out_dir, script_path)
        return
    if os.path.isfile(script_path) and not a.force:
        if not needs_regeneration(out_dir):
            raise SystemExit(f"artiq movcuddur: {script_path}  (--force ile uzerine yaz)")
        print("  evvelki skript yoxlamalardan kecmeyib - yeniden yazilir")

    print(f"[22] skript: {a.topic!r} -> {slug}")
    os.makedirs(out_dir, exist_ok=True)
    kw = {"provider": a.provider, "model": a.model, "temperature": a.temperature}
    try:
        plan = outline(a.topic, **kw)
        source = find_source(a, plan, out_dir)
        script, domains = generate(a.topic, a.words, plan, source, **kw)
    except LLMError as e:
        raise SystemExit("LLM xetasi: " + str(e)) from e

    n = word_count(script)
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script.rstrip() + "\n")
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"topic": a.topic, "slug": slug, "words": n,
                   "est_minutes": round(n / EFFECTIVE_WPM, 1), "domains": domains, "plan": plan,
                   "provider": a.provider, "model": a.model or "default"}, f, indent=2, ensure_ascii=False)

    print(f"  {n} soz  ~{n / EFFECTIVE_WPM:.1f} deq video -> {script_path}")
    if not WORDS_MIN <= n <= WORDS_MAX:
        print(f"  DIQQET: soz sayi {WORDS_MIN}-{WORDS_MAX} araliginda deyil")
    quality_gate(a, out_dir, script_path)


if __name__ == "__main__":
    main()
