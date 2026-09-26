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

SPRITES_JSON = r"C:\YouTubeAI\Character\ELI5_Owl\sprites\sprites.json"
WPM = 199.0   # olculmus; hər halda add. 25-de gercek audio uzunlugu ile evez olunur
# Istifadeci: "sekiller tekrardir" - 20 s bir sekil darixdirir. Sehne ~4-10 s, her sehneye oz sekli.
MIN_WORDS, MAX_WORDS = 14, 32
PLAN_CHUNK = 24                    # LLM-e bir defede verilen sehne sayi (uzun JSON pozulmasin)
RETRY_ROUNDS, RETRY_CHUNK = 3, 12   # tekrarlar kicik hisselerle yeniden istenir
REPEAT_WINDOW = 8                  # eyni esas obyekt bu qeder sehne erzinde tekrar olunmur
MIN_PROMPT_WORDS = 5               # "a smartphone" - temizlemeden sonra cilpaq qalan prompt -> yeniden
NEAR_WINDOW = 2                    # bundan yaxin tekrar olunan subyekt ehtiyat fonla evez olunur
MAX_SAME_HERO = 2                  # eyni esas isim butun epizodda en cox bu qeder (ep4: 7 sikke bankasi)
# Busт sprite-lerin bir yani kesikdir - kenara yapisdirilmali olur ve tam beden pozlarla
# olcu/yer uygunsuzlugu yaradir ("sekilsiz yerlesdirilib"). Videoda yalniz tam beden.
VIDEO_POSES = ("front", "three_q", "side", "box", "chart")
MIN_DUR, MAX_DUR = 6.0, 45.0   # klemp yalniz emniyyet ucun; gercek muddet add. 25-de TTS-den gelir
POSITIONS = ("left", "right", "center")
OWL_SIDE = "right"             # personaj butun epizodda eyni yerde (istifadeci 2026-09-27)
FALLBACK_POSE = "three_q"

SYSTEM = """You are the art director of an animated explainer video for kids and beginners.
The host is a cartoon owl rendered separately in a lower corner - you never describe the owl.
For every scene you choose one background picture and one owl pose.

Picture rules:
- ONE clear hero subject that literally shows what the narration is talking about right now
  (the object, machine, place or result in the sentence), doing its action if it has one.
  Example: "a shiny robot arm stirring a pot of tomato soup on a stove".
- At most one or two supporting props and a simple setting. Never a list of many objects.
- Everything must make physical sense: objects at normal size, in their normal place, not merged.
- Describe CONTENT ONLY - never style words (vector, illustration, flat, 3D, render, colors).
- NO people, NO hands, NO animals, NO characters. Robots and machines are fine.
- NO written words, letters, numbers, screens, signs, labels, charts, documents, books,
  calendars, receipts, money bills. Show physical objects instead.
- Every scene must look DIFFERENT from the previous scenes: a new hero subject, a new place
  or a clearly different close-up. Never reuse a subject from the recent list.
- When the narration stays on the same thing for several scenes, change the view each time:
  wide view of the place -> close-up of one detail -> the finished result -> a top-down view.
- 8-20 words, English, comma separated: hero subject first, then props, then setting.
- "subject": the hero subject in 1-3 words (used to detect repeats)."""

USER = """Return a picture and an owl pose for each numbered scene.

Available owl poses (use the name exactly): {poses}
front = talking to viewer, three_q = explaining, side = walking/looking at something,
box = showing a product/example/object, chart = numbers, growth, comparisons, results.
For each scene pick the pose that best fits what the narration says in that scene.

Subjects already used recently (do NOT repeat them): {used}

Return JSON exactly in this shape, one entry per scene, same order, no extra keys:
{{"scenes": [{{"n": 1, "subject": "...", "bg_prompt": "...", "sprite": "three_q"}}]}}

Scenes:
{note}{scenes}"""
# Yeniden istenen sehneler: evvelki sekil ya tekrar idi, ya da ekran/yazi/insan oldugu ucun silindi
RETRY_NOTE = """These scenes are asked AGAIN: the first pictures repeated an earlier subject or needed
screens, text, apps or people, which cannot be drawn. Show the idea with a PHYSICAL object or machine
metaphor instead (e.g. reminders -> a brass bell ringing on a desk; email -> paper envelopes flying
out of a small mail robot; calendar app -> a wooden desk clock beside a potted plant).

"""


# SDXL yazi cekende anlamsiz herfler cixir (FAZA F E2E, sehne 16: "game interface"). LLM
# qadagaya tam emel etmir, ona gore yazi dasiyan hisseler deterministik atilir.
TEXT_BEARING = re.compile(
    r"['\"‘’“”]|\b(signs?|signage|label(?:ed|led)?|screens?|dashboards?|"
    r"interfaces?|scoreboards?|charts?|graphs?|statements?|receipts?|checklists?|lists?|"
    r"notes?|notepad|sheets?|written|writing|handwriting|report cards?|chalkboards?|blackboards?|whiteboards?|boards?|posters?|banners?|"
    r"menus?|icons?|planners?|apps?|display of|homework|assignments?|grades|"
    # obyektin ozu cap dasiyir - SDXL uzerinde mutleq psevdo-yazi cekir (E2E sc12/20/24/28)
    r"calendars?|calculators?|bills?|banknotes?|books?|notebooks?|newspapers?|magazines?|"
    r"documents?|papers?|invoices?|tickets?|coupons?|price tags?|plans?|"
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
    r"parents?|visitors?|patients?|doctors?|nurses?)\b", re.I)
PIZZA_BOX = re.compile(r"\bpizza box(es)?\b", re.I)
# "and" ile bolunende "limits", "no extra fees" kimi qirintilar qalir - yalniz isim birlesmesi saxlanir
NOUN_START = re.compile(r"^(with|and)\s+", re.I)
NOUN_PHRASE = re.compile(r"^(a|an|the|some|several|piles?|stacks?|rows?)\s", re.I)
MAX_PARTS = 3      # SDXL cox obyekti bir-birine qarisdirir ("esyalar qarisib")
FALLBACK_BG = "a cozy tidy desk with a potted plant, a coffee mug and a warm lamp"
# Temizlenmis prompt bos qalanda - her biri bir defe istifade olunur (8 eyni fon olmusdu)
FALLBACK_POOL = (    # biznes/avtomatlasdirma metaforalari - movzudan kenar tesadufi sekil olmasin
    "a shiny brass gear mechanism turning, soft workshop light",
    "a small conveyor belt carrying wooden toy blocks on a workbench",
    "a friendly robot arm stacking colorful cubes on a workbench",
    "a glowing light bulb on a wooden desk beside a potted plant",
    "a row of dominoes falling in a neat line on a wooden table",
    "a small wind-up robot walking across a tidy wooden desk",
    "a glass jar slowly filling with golden coins on a wooden table",
    "a silver stopwatch lying on a wooden desk next to a coffee cup",
    "a tidy workbench with neatly arranged tools hanging on a wall",
    "a toy factory with tiny gears and a little conveyor belt",
    "a brass pulley lifting a small wooden crate in a workshop",
    "a red toy rocket lifting off from a wooden desk, soft smoke",
    "a mechanical music box with turning golden gears",
    "a potted sprout growing on a sunny windowsill, a watering can beside it",
    "a golden key turning in a padlock on a wooden chest",
    "a paper airplane gliding over a tidy wooden desk",
    "a stack of wooden building blocks forming a tall tower",
    "a small delivery drone carrying a wooden crate over a green park",
    "a toy train crossing a little bridge on a tabletop",
    "a compass lying on a wooden table, warm light",
)


def clean_bg_prompt(prompt: str) -> str:
    """Vergul / 'and' ile bolunen hisselerden yazi teleb edenleri atir; hec ne qalmasa FALLBACK_BG."""
    parts = [p.strip() for p in re.split(r",|\band\b", prompt) if p.strip()]
    parts = [NOUN_START.sub("", p) for p in parts]
    parts = [ABSTRACT_TAIL.sub("", p) for p in parts]
    parts = [PAYMENT_CARD.sub(lambda m: BLANK_CARD.replace("card", "card" + m.group(1), 1), p)
             for p in parts]
    parts = [PIZZA_BOX.sub(lambda m: "pizza tray" + ("s" if m.group(1) else ""), p) for p in parts]
    kept = [p for p in parts
            if NOUN_PHRASE.match(p) and not TEXT_BEARING.search(p) and not HUMAN.search(p)]
    return ", ".join(kept[:MAX_PARTS]) or FALLBACK_BG


def fallback_bg(k: int) -> str:
    return FALLBACK_POOL[k % len(FALLBACK_POOL)]


def pick_fallbacks(n: int, used_heroes: set[str]) -> list[str]:
    """n ehtiyat fon: evvelce epizodda olmayan esas isimliler, catmasa qalanlar (tekrarsiz)."""
    fresh = [p for p in FALLBACK_POOL if hero(p) not in used_heroes]
    rest = [p for p in FALLBACK_POOL if p not in fresh]
    pool = fresh + rest
    return [pool[k % len(pool)] for k in range(n)]


def _norm(subject: str) -> str:
    return " ".join(w.rstrip("s") for w in re.findall(r"[a-z]+", subject.lower()) if w not in ("a", "an", "the"))


_ARTICLES = {"a", "an", "the", "some", "several"}
_HERO_STOP = {"with", "of", "on", "in", "at", "next", "beside", "near", "under", "over", "from", "to", "for",
              "filled", "full", "and", "that", "which", "while", "into", "onto", "by", "against", "behind"}


def hero(prompt: str) -> str:
    """Promptun esas ismi: ilk isim birlesmesinin son sozu ("a glass jar slowly filling ..." -> "jar").
    LLM subyekti mucerred adlandirir ("positive cash flow"), sekil ise eyni sikke bankasi olur."""
    chunk: list[str] = []
    for w in re.findall(r"[a-z]+", prompt.split(",")[0].lower()):
        if not chunk and w in _ARTICLES:
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
        if not line:
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


def _ask(scenes: list[dict], numbers: list[int], used: list[str], retry: bool = False,
         **llm_kw) -> list[dict]:
    listing = "\n".join(f"{n}. [{scenes[n - 1]['section']}] {scenes[n - 1]['narration']}" for n in numbers)
    data = chat_json(SYSTEM, USER.format(poses=", ".join(VIDEO_POSES), used=", ".join(used) or "none",
                                         note=RETRY_NOTE if retry else "",
                                         scenes=listing), max_tokens=4000, **llm_kw)
    items = align(data.get("scenes") or [], numbers)
    lost = sum(1 for it in items if not it)
    if lost:
        print(f"  DIQQET: LLM {lost}/{len(numbers)} sehneni qaytarmadi - yeniden istenecek")
    return items


def _fields(it: dict) -> tuple[str, str, str]:
    bg = " ".join(str(it.get("bg_prompt", "")).split())
    return (clean_bg_prompt(bg) if bg else FALLBACK_BG,
            " ".join(str(it.get("subject", "")).split()) or bg[:30], str(it.get("sprite", "")).strip())


def plan(scenes: list[dict], poses: list[str], **llm_kw) -> list[dict]:
    """Hisse-hisse planlanir (son movzular LLM-e verilir), sonra tekrarlar bir defe yeniden istenir,
    qalanlar tekrarsiz FALLBACK_POOL-dan alir. Pozlar tam beden, sehneye uygun."""
    missing = [p for p in VIDEO_POSES if p not in poses]
    if missing:
        raise LLMError(f"sprites.json-da poz yoxdur: {missing}")
    prompts: list[str] = []
    subjects: list[str] = []
    sprites: list[str] = []
    for start in range(0, len(scenes), PLAN_CHUNK):
        numbers = list(range(start + 1, min(len(scenes), start + PLAN_CHUNK) + 1))
        recent = avoid_list(prompts[-REPEAT_WINDOW * 2:], subjects[-REPEAT_WINDOW * 2:])
        heroes = [hero(p) for p in prompts]
        overused = {h for h in heroes if h and heroes.count(h) >= MAX_SAME_HERO}
        for it in _ask(scenes, numbers, sorted(set(recent) | set(overused)), **llm_kw):
            bg, sub, spr = _fields(it)
            prompts.append(bg)
            subjects.append(sub)
            sprites.append(spr)
    for _ in range(RETRY_ROUNDS):
        bad = repeats(prompts, subjects)
        if not bad:
            break
        print(f"  tekrar/bos fon: {len(bad)} sehne yeniden istenir")
        for c in range(0, len(bad), RETRY_CHUNK):
            part = bad[c:c + RETRY_CHUNK]
            used = avoid_list(prompts, subjects, skip=set(part))
            for i, it in zip(part, _ask(scenes, [i + 1 for i in part], used, retry=True, **llm_kw)):
                if it:
                    prompts[i], subjects[i], _ = _fields(it)
    # Movzuya aid, amma bir az evvel olmus subyekt tesadufi fondan yaxsidir: son addimda yalniz bos
    # promptlar ve yan-yana (NEAR_WINDOW) tekrarlar evez olunur
    final = repeats(prompts, subjects, NEAR_WINDOW)
    print(f"  ehtiyat fon: {len(final)} (bos: {sum(prompts[i] == FALLBACK_BG for i in final)})")
    kept = {hero(p) for j, p in enumerate(prompts) if j not in final}
    for k, (i, fb) in enumerate(zip(final, pick_fallbacks(len(final), kept))):
        prompts[i], subjects[i] = fb, f"fallback {k}"
    out = []
    for sc, bg, sub, spr, pos in zip(scenes, prompts, subjects, fit_poses(sprites), assign_positions(scenes)):
        out.append({**sc, "bg_prompt": bg, "subject": sub, "sprite": spr, "pos": pos,
                    "sprite_token": f"{spr}@{pos}", "duration": duration_for(sc["narration"])})
    return out


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

    try:
        planned = plan(scenes, poses, provider=a.provider, model=a.model, temperature=a.temperature)
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
