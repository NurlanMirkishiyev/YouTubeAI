"""Add'im 23 - script.md -> scenes.json (fon promptu + sprite + muddet + narration).
Narration LLM-e yazdirilmir: skript deterministik olaraq sehnelere bolunur,
LLM yalniz her sehne ucun fon promptu ve sprite adini secir. Beleliklede metn 1:1 qorunur.
Istifade:
  python Projects\\scene_plan.py Episodes\\<slug> [--provider openai] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import LLMError, add_provider_arg, chat_json  # noqa: E402
from visuals import plan_visuals  # noqa: E402

SPRITES_JSON = r"C:\YouTubeAI\Character\ELI5_Owl\sprites\sprites.json"
WPM = 199.0   # olculmus; hər halda add. 25-de gercek audio uzunlugu ile evez olunur
# Istifadeci: "sekiller tekrardir" - 20 s bir sekil darixdirir. Sehne ~4-10 s, her sehneye oz sekli.
MIN_WORDS, MAX_WORDS = 14, 32
PLAN_CHUNK = 24                    # LLM-e bir defede verilen sehne sayi (uzun JSON pozulmasin)
RETRY_ROUNDS, RETRY_CHUNK = 3, 12   # tekrarlar kicik hisselerle yeniden istenir
REPEAT_WINDOW = 8                  # eyni esas obyekt bu qeder sehne erzinde tekrar olunmur
MIN_PROMPT_WORDS = 5               # "a smartphone" - temizlemeden sonra cilpaq qalan prompt -> yeniden
# Istifadeci (2026-09-28): tekrar kadrlar QETI olmasin - eyni esas obyekt epizodda yalniz 1 defe
MAX_SAME_HERO = 1
# Busт sprite-lerin bir yani kesikdir - kenara yapisdirilmali olur ve tam beden pozlarla
# olcu/yer uygunsuzlugu yaradir ("sekilsiz yerlesdirilib"). Videoda yalniz tam beden.
VIDEO_POSES = ("front", "three_q", "side", "box", "chart")
MIN_DUR, MAX_DUR = 6.0, 45.0   # klemp yalniz emniyyet ucun; gercek muddet add. 25-de TTS-den gelir
POSITIONS = ("left", "right", "center")
OWL_SIDE = "right"             # personaj butun epizodda eyni yerde (istifadeci 2026-09-27)
FALLBACK_POSE = "three_q"

SYSTEM = """You are the art director of a business explainer video for ADULT viewers (25-45: professionals,
freelancers, small business owners). It must look like a premium documentary, never like a children's video.
The host is a cartoon owl rendered separately in a lower corner - you never describe the owl.
For every scene you choose one background picture and one owl pose.

Picture rules:
- LITERAL, not symbolic: show the real business, place, product, tool or machine the narration talks about -
  above all the case business the video follows. NEVER a metaphor or generic stock object (piggy bank,
  hourglass, chess piece, light bulb, compass, lighthouse, coins on a table, empty desk).
- ONE clear hero subject that literally shows what the narration is talking about right now
  (the object, machine, place or result in the sentence), doing its action if it has one.
  Example: "an espresso machine pouring a shot in a busy modern cafe".
- Real adult world only: offices, shops, cafes, warehouses, factories, banks, streets, homes, tools,
  products and vehicles. NEVER toys, candy, cookies piles, carnival games, playgrounds, school things,
  balloons, cartoon objects or anything that belongs in a children's show.
- At most one or two supporting props and a simple setting. Never a list of many objects.
- Everything must make physical sense: objects at normal size, in their normal place, not merged.
- Describe CONTENT ONLY - never style words (vector, illustration, flat, 3D, render, colors).
- NO people, NO hands, NO animals, NO characters. Machines are fine.
- NO written words, letters, numbers, screens, signs, labels, charts, documents, books,
  calendars, receipts, money bills. Show physical objects instead.
- NO price tags, prices, currency signs or digits, even when the video is about prices: show the product
  or the place itself (e.g. "two detergent bottles side by side on a supermarket shelf").
- STRICT: every scene shows a DIFFERENT hero object than ALL other scenes of the video. The same object
  (even as a close-up, another angle, a stack or a plate of it) never appears twice. Never reuse anything
  from the "already used" list.
- When the narration stays on the same idea for several scenes, show a different related real object or
  place each time (its cause, its setting, its result, the tool behind it) - never the same object again.
- 8-20 words, English, comma separated: hero subject first, then props, then setting.
- "subject": the hero subject in 1-3 words (used to detect repeats)."""

USER = """Return a picture and an owl pose for each numbered scene.

Available owl poses (use the name exactly): {poses}
front = talking to viewer, three_q = explaining, side = walking/looking at something,
box = showing a product/example/object, chart = numbers, growth, comparisons, results.
For each scene pick the pose that best fits what the narration says in that scene.

"owl_action": what the owl host itself does in this scene, 6-14 words, English: ONE pose or gesture
plus its emotion and at most ONE simple prop that matches the narration (e.g. "shaking hands with a
small friendly robot, smiling", "holding a big stopwatch, surprised", "pointing up with one wing,
excited"). No people, no text, no papers, books, screens or signs. Never the same action as the
previous scene.

Subjects already used recently (do NOT repeat them): {used}

Return JSON exactly in this shape, one entry per scene, same order, no extra keys:
{{"scenes": [{{"n": 1, "subject": "...", "bg_prompt": "...", "sprite": "three_q", "owl_action": "..."}}]}}

Scenes:
{note}{scenes}"""
# Yeniden istenen sehneler: evvelki sekil ya tekrar idi, ya da ekran/yazi/insan oldugu ucun silindi
RETRY_NOTE = """These scenes are asked AGAIN: the first pictures repeated an earlier subject or needed
screens, text, apps, people, price tags, prices or digits, which cannot be drawn. Show the idea LITERALLY with
a real place, product, tool or machine of the business in the narration that carries no writing (e.g. pricing
at a taqueria -> a steaming tray of tacos on the pass of a restaurant kitchen; shipping costs -> a delivery van
at a loading dock). No symbolic metaphors.

"""


TOPIC_POOL_SPARE = 15              # filtrden kecmeyenler ucun artiq istenir
TOPIC_POOL = """The video is titled "{topic}". List {n} background pictures for it: each one a DIFFERENT
real physical object, machine or place from the world of this topic (shops, products, tools, rooms, streets),
following all picture rules above. No price tags, prices, digits, labels or screens.
Each picture is ONE full phrase of 8-20 words that starts with "a" or "an", e.g.
"a clothing rack with folded shirts in a quiet boutique in morning light".
Never use these objects again: {used}

Return JSON exactly: {{"pictures": ["...", "..."]}}"""


# SDXL yazi cekende anlamsiz herfler cixir (FAZA F E2E, sehne 16: "game interface"). LLM
# qadagaya tam emel etmir, ona gore yazi dasiyan hisseler deterministik atilir.
TEXT_BEARING = re.compile(
    # Reyestr #38: "$9.99", "the other $10" - reqem/valyuta sekilde yazi olur
    r"['\"‘’“”$]|\d|\b(signs?|signage|label(?:s|ed|led)?|screens?|dashboards?|"
    # #38: cap olunmus sey - "quality seal sticker", "feedback form", "brand logo", "comment section"
    r"stickers?|seals?|forms?|logos?|brands?|comments?|online|websites?|(?<!plastic )cards?|"
    r"numbers?|digits?|pages?|summar(?:y|ies)|reviews?|reports?|badges?|pric(?:e|es|ed|ing)|visible|"
    r"interfaces?|scoreboards?|charts?|graphs?|statements?|receipts?|checklists?|lists?|"
    r"notes?|notepad|sheets?|written|writing|handwriting|report cards?|chalkboards?|blackboards?|whiteboards?|boards?|posters?|banners?|"
    r"menus?|icons?|planners?|apps?|display of|homework|assignments?|grades|"
    # obyektin ozu cap dasiyir - SDXL uzerinde mutleq psevdo-yazi cekir (E2E sc12/20/24/28)
    r"calendars?|calculators?|bills?|banknotes?|books?|notebooks?|newspapers?|magazines?|"
    r"documents?|papers?|invoices?|tickets?|coupons?|tags?|plans?|"
    r"card readers?|terminals?|"
    # ekranli cihazlar reqem/yazi cekir (ep3 sc23 "smart kitchen scale" 3 raund); "smart robot" qalir
    r"digital \w+|smart (?:kitchen )?(?:scales?|ovens?|devices?|watch(?:es)?|thermostats?|speakers?|"
    r"meters?|displays?|fridges?|refrigerators?|blenders?|appliances?)|"
    # ekranli cihaz - SDXL ekranini psevdo-yazi ile doldurur
    r"smartphones?|phones?|computers?|laptops?|tablets?|monitors?)\b", re.I)
# "showing balance", "indicating savings" - abstrakt melumat teleb edir, SDXL onu yazi kimi cekir
ABSTRACT_TAIL = re.compile(
    r"\s+(?:showing|indicating|representing|displaying|counting|beside it|next to it|on the side)\b.*$",
    re.I)
# Eyni seed ile olculdu: negativ prompt kartdaki yazini aradan qaldirmir, bu ad ise qaldirir
BLANK_CARD = "blank glossy plastic card with a small gold chip"
PAYMENT_CARD = re.compile(r"\b(?:credit|debit|bank|payment|gift)\s+card(s?)\b(?!\s+readers?)", re.I)
# Insan ismi negativ promptdaki "person"-u ustelayir (E2E sc35 "basketball player" -> cizgi oglan).
# Qabagindaki "robot " varsa (robot chef) - movzu analogiyasidir, saxlanir.
HUMAN = re.compile(
    r"\b(?<!robot )(?:people|persons?|man|men|woman|women|boys?|girls?|kids?|child(?:ren)?|"
    r"players?|chefs?|cooks?|customers?|clients?|workers?|employees?|staff|owners?|"
    r"shoppers?|cashiers?|teachers?|students?|farmers?|gardeners?|drivers?|family|friends?|"
    r"crowds?|team|someone|somebody|everyone|names?|athletes?|hands?|humans?|users?|learners?|"
    r"parents?|visitors?|patients?|doctors?|nurses?|consumers?|buyers?|freelancers?)\b", re.I)
PIZZA_BOX = re.compile(r"\bpizza box(es)?\b", re.I)
# "and" ile bolunende "limits", "no extra fees" kimi qirintilar qalir - yalniz isim birlesmesi saxlanir
NOUN_START = re.compile(r"^(with|and)\s+", re.I)
NOUN_PHRASE = re.compile(r"^(a|an|the|some|several|piles?|stacks?|rows?|two|three|four|five)\s", re.I)
MAX_PARTS = 3      # SDXL cox obyekti bir-birine qarisdirir ("esyalar qarisib")
FALLBACK_BG = "a tidy modern office desk by a large window, soft daylight"
# Istifadeci (2026-09-28): usaq videosu kimi gorunmesin (oyuncaq/karusel/konfet yox) ve tekrar kadr olmasin:
# her ehtiyat fon real dunyadan AYRI obyektdir (hero tekrarsiz), epizodda bir defe istifade olunur
FALLBACK_POOL = (
    "a brass gear mechanism turning in a softly lit workshop",
    "an espresso machine pouring a shot in a modern cafe",
    "a glass jar filling with coins on a kitchen counter",
    "a silver stopwatch on a dark wooden desk",
    "a leather briefcase standing beside an office chair",
    "a row of shipping containers stacked at a port at sunset",
    "a delivery van parked on a quiet city street",
    "an empty modern conference room with a long wooden table",
    "a warehouse aisle with tall shelves of cardboard boxes",
    "a conveyor belt moving parcels in a bright factory",
    "a golden key in a brass padlock on a wooden door",
    "a compass on a dark leather surface in warm light",
    "a potted sprout on a sunny office windowsill",
    "a steel bank vault door slightly open",
    "a stack of gold bars in a dim vault",
    "a wooden chess king piece on a dark table",
    "a single light bulb glowing in a dark loft office",
    "a row of dominoes falling on a dark table",
    "an hourglass with sand running on a desk",
    "a ceramic coffee mug steaming on an office desk",
    "a fountain pen resting on a leather desk pad",
    "a modern glass skyscraper reflecting the sky",
    "a city skyline at dusk seen from a high window",
    "a cargo ship leaving a harbor at sunrise",
    "a freight train crossing a steel bridge at dusk",
    "a small bakery shop window with fresh bread loaves",
    "a market stall with crates of fresh vegetables",
    "a wooden crate lifted by a warehouse forklift",
    "an empty grocery cart in a supermarket aisle",
    "a set of brass balance scales with small weights",
    "a steel safe with a round dial in an office corner",
    "a mountain road winding up to a summit at sunrise",
    "a lighthouse shining over a dark sea",
    "a sailboat on calm water at golden hour",
    "a tall stack of cardboard boxes by a loading dock",
    "a gold wristwatch on a marble table",
    "a bonsai tree on a minimalist desk",
    "a steel cable bridge over a river at dusk",
    "a black umbrella in the rain on a city street",
    "an open metal toolbox on a workshop bench",
    "a greenhouse full of young plants in morning light",
    "a pair of running shoes on a gym floor",
    "rows of solar panels on a rooftop in bright sun",
)
# Usaq movzulari fonu usaq videosuna cevirir (pricing E2E: karusel, oyuncaq fabrik, peceniye yigini)
CHILDISH = re.compile(
    r"(?<![a-z])(?:toys?|kids?|child(?:ren)?|cand(?:y|ies)|lollipops?|carnival|ring toss|playground|"
    r"cartoons?|teddy|crayons?|lemonade stand|balloons?|wind-up|building blocks?)(?![a-z])", re.I)


# Reyestr #32: hakim "a burger with a price label" yazirdi - butun hisse atilirdi, obyektin ozu yazisizdir
TEXT_CLAUSE = re.compile(r"\s+(?:with|showing|displaying|featuring|bearing)\b", re.I)
# Yalniz obyekte yapisdirilmis yazi kesilir; ekran / kart oxuyucu / oyun magazasi kimi yazili yer ve cihaz
# elavesinde hisse evvelki kimi butov atilir (bas hisse "a counter", "a game store" menasiz qalir)
ATTACHED_TEXT = re.compile(r"\b(?:price[sd]?|labels?|labell?ed|tag(?:s|ged)?|stickers?|marked)\b|[$\d]", re.I)


def cut_text_clause(part: str) -> str:
    """Yazi dasiyan soz obyektden sonraki elavededirse ("X with a price label ...") elave kesilir."""
    m = TEXT_BEARING.search(part)
    if not m or not ATTACHED_TEXT.search(part[m.start():]):
        return part
    cuts = [c.start() for c in TEXT_CLAUSE.finditer(part) if c.start() < m.start()]
    return part[:cuts[0]] if cuts else part


# Reyestr #38: gpt-4o artikl yazmir ("shirt on a rack") - ilk hisse (esas obyekt) artikl alir;
# "no extra fees" kimi qirinti ise yox
NOT_A_NOUN = {"no", "not", "without", "only", "extra", "more", "less", "various", "very", "just", "each"}


def with_article(part: str) -> str:
    first = part.split(" ", 1)[0].lower()
    if NOUN_PHRASE.match(part) or not first.isalpha() or first in NOT_A_NOUN:
        return part
    return ("an " if first[0] in "aeiou" else "a ") + part


def clean_bg_prompt(prompt: str) -> str:
    """Vergul / 'and' ile bolunen hisselerden yazi teleb edenleri atir; hec ne qalmasa FALLBACK_BG."""
    parts = [p.strip() for p in re.split(r",|\band\b", prompt) if p.strip()]
    parts = [NOUN_START.sub("", p) for p in parts]
    parts = [ABSTRACT_TAIL.sub("", p) for p in parts]
    parts = [PAYMENT_CARD.sub(lambda m: BLANK_CARD.replace("card", "card" + m.group(1), 1), p)
             for p in parts]
    parts = [PIZZA_BOX.sub(lambda m: "pizza tray" + ("s" if m.group(1) else ""), p) for p in parts]
    parts = [cut_text_clause(p) for p in parts]
    if parts:
        parts[0] = with_article(parts[0])
    kept = [p for p in parts
            if NOUN_PHRASE.match(p) and not TEXT_BEARING.search(p) and not HUMAN.search(p)
            and not CHILDISH.search(p)]
    return ", ".join(kept[:MAX_PARTS]) or FALLBACK_BG


def fallback_bg(k: int) -> str:
    return FALLBACK_POOL[k % len(FALLBACK_POOL)]


def pick_fallbacks(n: int, used_heroes: set[str]) -> list[str]:
    """n ehtiyat fon - yalniz epizodda olmayan obyektler; catmasa xeta (tekrar kadr QETI olmaz)."""
    fresh = [p for p in FALLBACK_POOL if hero(p) not in used_heroes]
    if n > len(fresh):
        raise ValueError(f"ehtiyat fon catmir: {n} lazim, {len(fresh)} tekrarsiz var")
    return fresh[:n]


def _norm(subject: str) -> str:
    return " ".join(w.rstrip("s") for w in re.findall(r"[a-z]+", subject.lower()) if w not in ("a", "an", "the"))


_ARTICLES = {"a", "an", "the", "some", "several"}
_HERO_STOP = {"with", "of", "on", "in", "at", "next", "beside", "near", "under", "over", "from", "to", "for",
              "filled", "full", "and", "that", "which", "while", "into", "onto", "by", "against", "behind"}


_QUANTITY = {"stack", "pile", "row", "pair", "set", "bunch", "handful", "heap", "couple", "group", "collection"}


def hero(prompt: str) -> str:
    """Promptun esas ismi: ilk isim birlesmesinin son sozu ("a glass jar slowly filling ..." -> "jar").
    LLM subyekti mucerred adlandirir ("positive cash flow"), sekil ise eyni sikke bankasi olur."""
    chunk: list[str] = []
    for w in re.findall(r"[a-z]+", prompt.split(",")[0].lower().replace("side by side", "")):
        if not chunk and w in _ARTICLES:
            continue
        if w == "of" and chunk and (chunk[-1].rstrip("s") in _QUANTITY or chunk[-2:] == ["close", "up"]):
            chunk = []                      # "a stack of cookies" -> cookie (6 peceniye tutulmurdu)
            continue
        if w in _HERO_STOP or (chunk and (w.endswith("ing") or w.endswith("ly") or
                                          (w.endswith("ed") and len(w) > 4))):
            break
        chunk.append(w)
    return chunk[-1].rstrip("s") if chunk else ""


def avoid_list(prompts: list[str], subjects: list[str], skip: set[int] = frozenset()) -> list[str]:
    """LLM-e "bunlari tekrarlama" siyahisi: subyektler + sekildeki esas isimler ("jar")."""
    keep = [i for i in range(len(prompts)) if i not in skip]
    return sorted({subjects[i] for i in keep if subjects[i]} | {hero(prompts[i]) for i in keep if hero(prompts[i])})


def repeats(prompts: list[str], subjects: list[str], window: int = REPEAT_WINDOW) -> list[int]:
    """Yeniden planlanmali sehneler: fallback-e dusenler, son `window` sehnede subyekti ve ya esas ismi
    tekrar olanlar, butun epizodda esas ismi MAX_SAME_HERO defe artiq islenenler."""
    bad = []
    heroes = [hero(p) for p in prompts]
    for i, (p, sub) in enumerate(zip(prompts, subjects)):
        lo = max(0, i - window)
        recent = {_norm(x) for x in subjects[lo:i]}
        h = heroes[i]
        if (p == FALLBACK_BG or len(p.split()) < MIN_PROMPT_WORDS or (_norm(sub) and _norm(sub) in recent)
                or (h and (h in heroes[lo:i] or heroes[:i].count(h) >= MAX_SAME_HERO))):
            bad.append(i)
    return bad


def fit_poses(suggested: list[str]) -> list[str]:
    """LLM sehnenin mezmununa uygun pozu secir - secim oldugu kimi saxlanir (tekrar olsa da).
    Bust ve ya namelum poz -> FALLBACK_POSE."""
    return [p if p in VIDEO_POSES else FALLBACK_POSE for p in suggested]


def load_poses() -> list[str]:
    if not os.path.isfile(SPRITES_JSON):
        raise SystemExit("sprites.json tapilmadi - evvelce make_sprites.py isledin: " + SPRITES_JSON)
    with open(SPRITES_JSON, encoding="utf-8") as f:
        return sorted(json.load(f))


def split_scenes(markdown: str) -> list[dict]:
    """Basliqlari atir, paraqraflari MIN_WORDS..MAX_WORDS araliginda sehnelere yigir."""
    scenes: list[dict] = []
    section = ""
    buf: list[str] = []

    def flush() -> None:
        if buf:
            text = " ".join(buf).strip()
            if text:
                scenes.append({"section": section, "narration": text})
            buf.clear()

    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            flush()
            section = line.lstrip("#").strip()
            continue
        if not line or section == "Cold Open":     # #56: Cold Open giris kartinda seslenir, sehne deyil
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if not sentence:
                continue
            if buf and len(" ".join(buf).split()) + len(sentence.split()) > MAX_WORDS:
                flush()
            buf.append(sentence)
        flush()
    flush()

    # cox qisa sehneleri qonsusuna birlesdir (eyni bolme daxilinde)
    merged: list[dict] = []
    for sc in scenes:
        if merged and merged[-1]["section"] == sc["section"] \
                and len(merged[-1]["narration"].split()) < MIN_WORDS:
            merged[-1]["narration"] += " " + sc["narration"]
        else:
            merged.append(sc)
    return merged


def assign_positions(scenes: list[dict]) -> list[str]:
    """Bayqus butun epizodda eyni terefde sabit durur (istifadeci 2026-09-27: "tərpənməsin").
    Evvel bolmeler novbe ile sag/sol idi - bolme deyisende personaj ekranda tullanirdi.
    'center' istifade olunmur - subtitr asagi-merkezdedir."""
    return [OWL_SIDE for _ in scenes]


def raw_duration(narration: str) -> float:
    """Klempsiz tehmin: soz sayi / WPM + qisa nefes."""
    return round(len(narration.split()) / WPM * 60.0 + 0.6, 1)


def duration_for(narration: str) -> float:
    return round(min(MAX_DUR, max(MIN_DUR, raw_duration(narration))), 1)


def align(items: list[dict], numbers: list[int]) -> list[dict]:
    """LLM cavabi sehne nomresine gore duzulur; catismayan sehne bos qalir (sonra yeniden istenir).
    Uzun siyahida LLM bezen yarisini qaytarir - butun planlama buna gore dayanmamalidir."""
    by_n = {}
    for it in items:
        try:
            by_n[int(it.get("n"))] = it
        except (TypeError, ValueError):
            pass
    if not set(by_n) & set(numbers):
        # nomre yoxdur ve ya LLM 1-den yeniden nomreleyib (97, 98 -> 1, 2) - sira ile
        return [(items[k] if k < len(items) else {}) for k in range(len(numbers))]
    return [by_n.get(n, {}) for n in numbers]


def case_note(plan: dict) -> str:
    """#60: videonun izlediyi case biznesi - fonlar onun real yerlerini/mehsullarini gostersin."""
    case = (plan or {}).get("case") or {}
    if not case.get("business"):
        return ""
    return (f"The video follows {case.get('owner', 'an owner')}'s business: {case['business']} in "
            f"{case.get('city', '')}, {case.get('state', '')}. Prefer literal pictures of this business's real "
            "places, products, tools and machines.\n\n")


CASE_NOTE = ""      # main() plandan doldurur; testlerde bos


def _ask(scenes: list[dict], numbers: list[int], used: list[str], retry: bool = False,
         **llm_kw) -> list[dict]:
    listing = "\n".join(f"{n}. [{scenes[n - 1]['section']}] {scenes[n - 1]['narration']}" for n in numbers)
    data = chat_json(SYSTEM, USER.format(poses=", ".join(VIDEO_POSES), used=", ".join(used) or "none",
                                         note=CASE_NOTE + (RETRY_NOTE if retry else ""),
                                         scenes=listing), max_tokens=4000, **llm_kw)
    items = align(data.get("scenes") or [], numbers)
    lost = sum(1 for it in items if not it)
    if lost:
        print(f"  DIQQET: LLM {lost}/{len(numbers)} sehneni qaytarmadi - yeniden istenecek")
    return items


def clean_owl_action(action: str) -> str:
    """Bayqusun sehnedeki hereketi: insan ve yazi dasiyan hisseler atilir (fon filtrleri ile eyni sebeb -
    gpt-image adi cekilen seyi cekir). Bos qalsa "" - o sehnede kohne poz sprite-i istifade olunur."""
    parts = [x.strip() for chunk in action.split(",") for x in re.split(r"\s+and\s+", chunk)]
    return ", ".join(x for x in parts if x and not TEXT_BEARING.search(x) and not _has_person(x))


def _has_person(text: str) -> bool:
    # bayqusun oz "elleri" var ("shaking hands with a robot") - yalniz insan isimleri sayilir
    return any(m.group(0).lower() not in ("hand", "hands") for m in HUMAN.finditer(text))


def _fields(it: dict) -> tuple[str, str, str, str]:
    bg = " ".join(str(it.get("bg_prompt", "")).split())
    return (clean_bg_prompt(bg) if bg else FALLBACK_BG,
            " ".join(str(it.get("subject", "")).split()) or bg[:30], str(it.get("sprite", "")).strip(),
            clean_owl_action(" ".join(str(it.get("owl_action", "")).split())))


def topic_pool(topic: str, used_heroes: set[str], n: int, **llm_kw) -> list[str]:
    """Sehne metni verilmeden movzuya aid tekrarsiz fonlar (metnde "$9.99" olanda LLM her defe yene
    qiymet etiketi cekirdi). Eyni filtrlerden kecir; esas ismi artiq islenenler atilir."""
    data = chat_json(SYSTEM, CASE_NOTE + TOPIC_POOL.format(n=n, topic=topic, used=", ".join(sorted(used_heroes)) or "none"),
                     max_tokens=4000, **llm_kw)
    out: list[str] = []
    seen = set(used_heroes)
    for raw in data.get("pictures") or []:
        p = clean_bg_prompt(" ".join(str(raw).split()))
        h = hero(p)
        if p == FALLBACK_BG or len(p.split()) < MIN_PROMPT_WORDS or not h or h in seen:
            continue
        seen.add(h)
        out.append(p)
    return out


def photo_repeats(prompts: list[str], subjects: list[str], photo: list[int]) -> list[int]:
    """repeats() yalniz foto sehnelerinde (#45: animasiya sehnesinin fonu yoxdur) - indeksler umumi siradadir."""
    return [photo[k] for k in repeats([prompts[i] for i in photo], [subjects[i] for i in photo])]


def plan(scenes: list[dict], poses: list[str], topic: str = "", visuals: list[dict | None] | None = None,
         **llm_kw) -> list[dict]:
    """Hisse-hisse planlanir (son movzular LLM-e verilir), sonra tekrarlar bir defe yeniden istenir,
    qalanlar evvelce movzu hovuzundan, sonra tekrarsiz FALLBACK_POOL-dan alir. Pozlar tam beden.
    visuals[i] (spec) olan sehne analitik animasiyadir: fon promptu bos, yalniz bayqus plani qalir."""
    visuals = visuals or [None] * len(scenes)
    photo = [i for i, v in enumerate(visuals) if not v]
    missing = [p for p in VIDEO_POSES if p not in poses]
    if missing:
        raise LLMError(f"sprites.json-da poz yoxdur: {missing}")
    prompts: list[str] = []
    subjects: list[str] = []
    sprites: list[str] = []
    actions: list[str] = []
    for start in range(0, len(scenes), PLAN_CHUNK):
        numbers = list(range(start + 1, min(len(scenes), start + PLAN_CHUNK) + 1))
        recent = avoid_list(prompts[-REPEAT_WINDOW * 2:], subjects[-REPEAT_WINDOW * 2:])
        heroes = [hero(p) for p in prompts]
        overused = {h for h in heroes if h and heroes.count(h) >= MAX_SAME_HERO}
        for it in _ask(scenes, numbers, sorted(set(recent) | set(overused)), **llm_kw):
            bg, sub, spr, act = _fields(it)
            prompts.append(bg)
            subjects.append(sub)
            sprites.append(spr)
            actions.append(act)
    for i, v in enumerate(visuals):
        if v:
            prompts[i], subjects[i] = "", ""
    for _ in range(RETRY_ROUNDS):
        bad = photo_repeats(prompts, subjects, photo)
        if not bad:
            break
        print(f"  tekrar/bos fon: {len(bad)} sehne yeniden istenir")
        for c in range(0, len(bad), RETRY_CHUNK):
            part = bad[c:c + RETRY_CHUNK]
            used = avoid_list(prompts, subjects, skip=set(part))
            for i, it in zip(part, _ask(scenes, [i + 1 for i in part], used, retry=True, **llm_kw)):
                if it:
                    prompts[i], subjects[i], _, act = _fields(it)
                    actions[i] = act or actions[i]
    # Istifadeci (2026-09-28): tekrar kadr QETI olmasin - qalan butun tekrarlar ehtiyat fonla evez olunur
    final = photo_repeats(prompts, subjects, photo)
    print(f"  ehtiyat fon: {len(final)} (bos: {sum(prompts[i] == FALLBACK_BG for i in final)})")
    kept = {hero(p) for j, p in enumerate(prompts) if j not in final and p}
    # Reyestr #38: evvelce movzuya aid tekrarsiz obyektler, generik hovuz (mayak, yelkenli) yalniz sonda
    pool = topic_pool(topic, kept, len(final) + TOPIC_POOL_SPARE, **llm_kw)[:len(final)] if topic and final else []
    kept |= {hero(p) for p in pool}
    print(f"  movzu hovuzu: {len(pool)}, generik hovuz: {len(final) - len(pool)}")
    for k, (i, fb) in enumerate(zip(final, pool + pick_fallbacks(len(final) - len(pool), kept))):
        prompts[i], subjects[i] = fb, f"fallback {k}"
    out = []
    for sc, bg, sub, spr, pos, act, vis in zip(scenes, prompts, subjects, fit_poses(sprites),
                                               assign_positions(scenes), actions, visuals):
        out.append({**sc, "bg_prompt": bg, "subject": sub, "sprite": spr, "pos": pos, "owl_action": act,
                    "visual": vis,
                    "sprite_token": f"{spr}@{pos}", "duration": duration_for(sc["narration"])})
    return out


def episode_topic(episode_dir: str) -> str:
    try:
        with open(os.path.join(episode_dir, "meta.json"), encoding="utf-8") as f:
            return str(json.load(f).get("topic", ""))
    except (OSError, ValueError):
        return ""


def episode_plan(episode_dir: str) -> dict:
    try:
        with open(os.path.join(episode_dir, "meta.json"), encoding="utf-8") as f:
            return json.load(f).get("plan") or {}
    except (OSError, ValueError):
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir", help=r"mes. Episodes\trademark-copyright-patent")
    ap.add_argument("--force", action="store_true")
    add_provider_arg(ap)
    a = ap.parse_args()

    script_path = os.path.join(a.episode_dir, "script.md")
    out_path = os.path.join(a.episode_dir, "scenes.json")
    if not os.path.isfile(script_path):
        raise SystemExit("script.md tapilmadi: " + script_path)
    if os.path.isfile(out_path) and not a.force:
        raise SystemExit(f"artiq movcuddur: {out_path}  (--force ile uzerine yaz)")

    poses = load_poses()
    scenes = split_scenes(open(script_path, encoding="utf-8").read())
    if not scenes:
        raise SystemExit("script.md-den sehne cixmadi")
    print(f"[23] {len(scenes)} sehne bolundu -> fon promptu + sprite secilir")

    topic = episode_topic(a.episode_dir)
    global CASE_NOTE
    CASE_NOTE = case_note(episode_plan(a.episode_dir))
    llm_kw = {"provider": a.provider, "model": a.model, "temperature": a.temperature}
    try:
        # #45: evvelce hansi sehnelerin animasiya olacagi - fon yalniz qalan foto sehnelerine planlanir
        visuals = plan_visuals(scenes, topic, **llm_kw)
        planned = plan(scenes, poses, topic=topic, visuals=visuals, **llm_kw)
    except LLMError as e:
        raise SystemExit("LLM xetasi: " + str(e)) from e

    clamped = [i + 1 for i, s in enumerate(planned)
               if abs(s["duration"] - raw_duration(s["narration"])) > 0.05]
    if clamped:
        print("  DIQQET: muddeti klemplenmis sehneler:", clamped)
    total = sum(s["duration"] for s in planned)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"scenes": planned, "total_seconds": round(total, 1)}, f, indent=2, ensure_ascii=False)

    print(f"  {len(planned)} sehne  ~{total / 60:.1f} deq  -> {out_path}")
    print("  sprite istifadesi:", ", ".join(
        f"{p}x{sum(1 for s in planned if s['sprite'] == p)}" for p in poses))


if __name__ == "__main__":
    main()
