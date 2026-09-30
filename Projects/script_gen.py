"""Add'im 22 - movzu -> 8-10 deqiqelik ELI5 Business skripti (~1350 soz).
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

SYSTEM = """You write scripts for an ELI5 Business YouTube channel.
The audience is ADULTS aged 25-45: employees, freelancers and small business owners. The host is an
owl in a suit who explains business and money topics in plain, simple words - clear for a beginner,
but always respectful and grown-up, never childish or talking down to the viewer.

Voice and rules:
- Second person, warm, conversational. Short sentences. Contractions are fine.
- Every abstract idea gets a concrete example from adult life: a coffee shop, an online store,
  a freelance project, rent, salary, a gym membership, a phone plan, a supermarket, a small restaurant.
  Never examples from a child's world (toys, allowance, classmates, candy, playgrounds).
- Introduce each English business term once, then define it in one short sentence.
- No filler, no "in today's video we will", no sponsor reads, no emojis, no stage directions.
- Numbers and examples must be plausible and generic; never invent statistics,
  studies, company figures or laws you are not certain about. Prefer "roughly" over fake precision.
- Every calculation must be correct and easy to follow: use round numbers, say the inputs before
  the result, and do one step at a time. Name time conversions explicitly ("over four weeks",
  "over twelve months"). Check each result twice before writing it.
- Output is narration text only - it will be read aloud word for word by a TTS voice.
  Do not write anything a narrator would not say out loud."""

OUTLINE_USER = """Topic: {topic}

Plan a ~10 minute ELI5 explainer. Return JSON only:

{{"sections": [
  {{"title": "short title, max 5 words",
    "idea": "the one core idea this section teaches, one sentence",
    "domain": "the everyday world the analogy lives in, two or three words",
    "analogy": "the everyday analogy used, one sentence",
    "example": "a realistic mini-example, one sentence"}}
]}}

Exactly 4 sections. They must build on each other: the first establishes the
foundation, the last is the one a viewer would act on. No overlap between sections.

CRITICAL - variety: each section must use a DIFFERENT domain, and none of the four
may share a domain. Pick four genuinely different everyday worlds, for example:
cooking, sports, school, music, gardening, board games, building a treehouse,
a road trip, a pet, a library, a toolbox, a wardrobe, a birthday party.
Never use the same object or setting in two sections. Do not use a lemonade stand
in more than one section."""

# (basliq, soz hedefi, telimat)
BLOCKS: list[tuple[str, int, str]] = [
    ("Hook", 80,
     "Open with a concrete situation or a question the viewer has felt. Then state the one "
     "thing they will be able to do by the end. No greeting, no channel name, no 'in this video'."),
    ("Common Mistakes", 170,
     "Three mistakes real people make with this topic. For each: the mistake, why it feels "
     "reasonable, and the fix. Do not repeat the earlier sections' wording."),
    ("Recap", 110,
     "The three things worth remembering, stated plainly, in the order they were taught. "
     "No new information."),
    ("Call to Action", 45,
     "Invite a comment describing their own situation, and name one related next topic. Warm, not pushy."),
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
Its analogy must live in an everyday domain different from all of these: {domains}.
Return JSON only:
{{"title": "short title, max 5 words", "idea": "the one core idea, one sentence",
  "domain": "the everyday world the analogy lives in, two or three words",
  "analogy": "the everyday analogy used, one sentence",
  "example": "a realistic mini-example, one sentence"}}"""


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())).strip("-")[:60]


def word_count(markdown: str) -> int:
    """Yalniz narration sozleri - basliq setirleri sayilmir."""
    body = "\n".join(ln for ln in markdown.splitlines() if not ln.lstrip().startswith("#"))
    return len(body.split())


def check_headings(markdown: str) -> list[str]:
    required = ["## Hook", "## Section 1", "## Section 2", "## Section 3", "## Section 4",
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


def outline(topic: str, **llm_kw) -> list[dict]:
    data = chat_json(SYSTEM, OUTLINE_USER.format(topic=topic), max_tokens=1200, **llm_kw)
    sections = data.get("sections") or []
    if len(sections) != 4:
        raise LLMError(f"outline 4 bolme qaytarmalidir, qaytardi: {len(sections)}")
    return sections


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


def generate(topic: str, words: int, **llm_kw) -> tuple[str, list[str]]:
    """Bolme-bolme generasiya: model uzun metnde soz hedefini tutmur, ona gore paralanir."""
    secs = outline(topic, **llm_kw)
    outline_text = "\n".join(
        f"{i + 1}. {s.get('title', '')} [{s.get('domain', '')}] - {s.get('idea', '')} "
        f"Analogy: {s.get('analogy', '')} Example: {s.get('example', '')}"
        for i, s in enumerate(secs))
    domains = [str(s.get("domain", "")).strip() for s in secs]
    print("  analogiya saheleri:", ", ".join(d for d in domains if d))
    if len({d.lower() for d in domains if d}) < len([d for d in domains if d]):
        print("  DIQQET: outline tekrarlanan analogiya sahesi qaytardi")

    body_words = words - sum(w for _, w, _ in BLOCKS)
    per_section = max(150, round(body_words / len(secs)))
    parts: list[str] = [f"# {topic}"]

    hook_h, hook_w, hook_g = BLOCKS[0]
    print(f"  [{hook_h}] {hook_w} soz")
    parts += [f"## {hook_h}",
              _write_block(topic, outline_text, hook_h, hook_w, hook_g,
                           "The teaching sections already use these analogy domains: "
                           + ", ".join(d for d in domains if d)
                           + ". Do NOT use any of them here - open with a different concrete situation.",
                           **llm_kw)]

    for i, s in enumerate(secs, 1):
        title = str(s.get("title", f"Part {i}")).strip()
        heading = f"Section {i}: {title}"
        others = [d for j, d in enumerate(domains, 1) if d and j != i]
        guidance = (f"Core idea: {s.get('idea', '')}\n"
                    f"Use ONLY this analogy domain: {s.get('domain', '')}\n"
                    f"The analogy: {s.get('analogy', '')}\n"
                    f"The mini-example: {s.get('example', '')}\n"
                    f"Stay inside that one domain for the whole section, but do not restate the "
                    f"analogy more than twice - after introducing it, keep teaching the idea.\n"
                    f"Teach the one idea, make it concrete, then hand off to the next section.")
        print(f"  [{heading}] {per_section} soz  <{s.get('domain', '')}>")
        parts += [f"## {heading}",
                  _write_block(topic, outline_text, heading, per_section, guidance,
                               "Sections before this one are already written - do not repeat them. "
                               "These domains belong to OTHER sections and are forbidden here: "
                               + ", ".join(others) + ".",
                               **llm_kw)]

    for heading, w, guidance in BLOCKS[1:]:
        print(f"  [{heading}] {w} soz")
        parts += [f"## {heading}",
                  _write_block(topic, outline_text, heading, w, guidance,
                               "All four teaching sections are already written above. Refer to their "
                               "analogies in at most a few words - never re-explain them.", **llm_kw)]

    return "\n\n".join(parts), domains


def extend(topic: str, markdown: str, words: int, domains: list[str], **llm_kw) -> tuple[str, str]:
    """Movcud skripte Common Mistakes-den evvel yeni tedris bolmesi elave edir -> (skript, domain)."""
    existing = teaching_headings(markdown)
    sec = chat_json(SYSTEM, EXTEND_USER.format(topic=topic, existing="\n".join(existing) or "(none)",
                                               domains=", ".join(domains) or "(unknown)"),
                    max_tokens=600, **llm_kw)
    heading = f"Section {len(existing) + 1}: {str(sec.get('title', 'One More Thing')).strip()}"
    guidance = (f"Core idea: {sec.get('idea', '')}\n"
                f"Use ONLY this analogy domain: {sec.get('domain', '')}\n"
                f"The analogy: {sec.get('analogy', '')}\n"
                f"The mini-example: {sec.get('example', '')}\n"
                f"Teach the one idea, make it concrete, then hand off to the next section.")
    print(f"  [{heading}] {words} soz  <{sec.get('domain', '')}>")
    body = _write_block(topic, "\n".join(existing + [heading]), heading, words, guidance,
                        "Every other section is already written. Do not repeat their ideas or analogies.",
                        **llm_kw)
    return insert_before(markdown, "## Common Mistakes", f"## {heading}\n\n{body}"), \
        str(sec.get("domain", "")).strip()


SHORTEN_USER = """Topic: {topic}

Rewrite this section of the video script ("{heading}") to about {words} words.
Keep the core idea, the same analogy and the example; cut repetition and side remarks first.
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
    verify_math(a, script_path)


def run_extend(a: argparse.Namespace, out_dir: str, script_path: str) -> None:
    if not os.path.isfile(script_path):
        raise SystemExit("uzatmaq ucun script.md yoxdur: " + script_path)
    meta_path = os.path.join(out_dir, "meta.json")
    meta = {}
    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    print(f"[22+] skript uzadilir: +{a.extend} soz")
    with open(script_path, encoding="utf-8") as f:
        current = f.read()
    try:
        script, domain = extend(a.topic, current, a.extend, meta.get("domains", []),
                                provider=a.provider, model=a.model, temperature=a.temperature)
    except (LLMError, ValueError) as e:
        raise SystemExit("uzatma xetasi: " + str(e)) from e
    n = word_count(script)
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script.rstrip() + "\n")
    meta = {**meta, "words": n, "est_minutes": round(n / EFFECTIVE_WPM, 1),
            "domains": [*meta.get("domains", []), domain]}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"  {n} soz  ~{n / EFFECTIVE_WPM:.1f} deq video -> {script_path}")
    verify_math(a, script_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--slug", help="default: movzudan yaradilir")
    ap.add_argument("--words", type=int, default=1230)   # LLM ~10% asir -> ~1350 soz ~ 9 deq video
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
        raise SystemExit(f"artiq movcuddur: {script_path}  (--force ile uzerine yaz)")

    print(f"[22] skript: {a.topic!r} -> {slug}")
    try:
        script, domains = generate(a.topic, a.words, provider=a.provider, model=a.model,
                                   temperature=a.temperature)
    except LLMError as e:
        raise SystemExit("LLM xetasi: " + str(e)) from e

    missing = check_headings(script)
    n = word_count(script)
    os.makedirs(out_dir, exist_ok=True)
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script.rstrip() + "\n")
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"topic": a.topic, "slug": slug, "words": n,
                   "est_minutes": round(n / EFFECTIVE_WPM, 1), "domains": domains,
                   "provider": a.provider, "model": a.model or "default"}, f, indent=2)

    print(f"  {n} soz  ~{n / EFFECTIVE_WPM:.1f} deq video -> {script_path}")
    if missing:
        print("  DIQQET: catismayan basliqlar:", ", ".join(missing))
    if not WORDS_MIN <= n <= WORDS_MAX:
        print(f"  DIQQET: soz sayi {WORDS_MIN}-{WORDS_MAX} araliginda deyil")
    verify_math(a, script_path)


if __name__ == "__main__":
    main()
