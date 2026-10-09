"""#127/#128 (istifadeci 2026-10-10: "Menbeden real data"): timeseries/usmap ucun REAL zaman sirasi.
- CATALOG sabitdir: yalniz FRED-de (Federal Reserve Bank of St. Louis, acarsiz CSV) yoxlanmis seriyalar; asil
  nesriyyatci (Census Bureau, BLS) cite_as-dadir. Census API acar isteyir (2026-10-10 probu) - istifade olunmur.
- LLM yalniz katalogdan id SECIR (qapali secim) - seriya uydura bilmez; reqemleri Python yukleyir ve illik edir.
- Uygun seriya yoxdur / yuklenmedi / az il -> None: video vizualsiz davam edir, hec ne uydurulmur.
Cixis: Episodes\\<slug>\\series.json (script_gen yazir)."""
from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable

YEARS = 4                    # deyilen noqte sayi (data_visuals.DENSE - interpolasiya yox)
FETCH_TIMEOUT = 30
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}"
FRED_PAGE = "https://fred.stlouisfed.org/series/{id}"
PICK_MODEL = "gpt-4o"


@dataclass(frozen=True)
class Series:
    id: str
    title: str               # chart basligi (reqemsiz)
    unit: str                # "$" | "%" | ""
    transform: str           # "level" | "yoy" (illik faiz deyisimi)
    agg: str                 # "sum" | "mean" (ayliq -> illik)
    cite_as: str
    lead: str                # cumle: "According to <cite_as>, <lead> <v1> <noun> in <y1>, <v2> in <y2> ..."
    noun: str
    tags: str
    state_prefix: str = ""   # FRED stat seriyasi: prefix + poct kodu (BABATOTALSA + TX)
    unit_label: str = ""     # usmap sayqac etiketi (visuals.LABEL_MAX-a sigir)

    @property
    def url(self) -> str:
        return FRED_PAGE.format(id=self.id)


CATALOG: tuple[Series, ...] = (
    Series("BABATOTALSAUS", "New business applications", "", "level", "sum", "the U.S. Census Bureau",
           "owners across the US filed", "new business applications",
           "competition, new competitors, opening, expansion, second location, starting a business, market",
           state_prefix="BABATOTALSA", unit_label="Applications"),
    Series("CUSR0000SEFV", "Restaurant prices, yearly rise", "%", "yoy", "mean", "the Bureau of Labor Statistics",
           "prices at US restaurants and cafes rose", "",
           "restaurant, cafe, coffee shop, bakery, food service, menu prices, raising prices, pricing"),
    Series("CES7000000003", "Hourly pay in hospitality", "$", "level", "mean", "the Bureau of Labor Statistics",
           "average hourly pay in US restaurants, hotels and leisure businesses was", "",
           "hiring, staff, wages, employees, restaurant, cafe, hotel, hospitality, payroll"),
    Series("CES4200000003", "Hourly pay in retail", "$", "level", "mean", "the Bureau of Labor Statistics",
           "average hourly pay in US retail stores was", "",
           "hiring, staff, wages, employees, retail store, shop, boutique, payroll"),
    Series("JTSQUR", "Monthly quit rate", "%", "level", "mean", "the Bureau of Labor Statistics",
           "the share of US workers who quit their job each month averaged", "",
           "employee turnover, retention, hiring, quitting, staff, training"),
    Series("ECIWAG", "Private wages, yearly rise", "%", "yoy", "mean", "the Bureau of Labor Statistics",
           "wages and salaries of US private-sector workers rose", "",
           "raises, wages, salary, payroll, hiring, labor costs, employees"),
)

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY"}


def by_id(series_id: str) -> Series | None:
    return next((s for s in CATALOG if s.id == series_id), None)


def state_id(s: Series, state: str) -> str | None:
    code = STATES.get(" ".join(str(state or "").split()).title())
    return s.state_prefix + code if s.state_prefix and code else None


def _http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def parse_fred(text: str) -> dict[int, list[float]]:
    """FRED CSV -> {il: ayliq deyerler}; yalniz 12 (ayliq) ve ya 4 (rubluk) deyeri tam olan iller."""
    years: dict[int, list[float]] = {}
    for row in list(csv.reader(io.StringIO(text)))[1:]:
        if len(row) < 2 or len(row[0]) < 4:
            continue
        try:
            years.setdefault(int(row[0][:4]), []).append(float(row[1]))
        except ValueError:
            continue                         # "." = deyer yoxdur
    return {y: v for y, v in years.items() if len(v) in (4, 12)}


def _round(x: float, digits: int) -> float:
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def speakable(v: float, unit: str) -> float:
    """Deyilecek deqiqlik: milyonlar 0.1 milyon, minler 1,000, pul sent, faiz 0.1."""
    if unit == "$":
        return _round(v, 2)
    if unit == "%":
        return _round(v, 1)
    if abs(v) >= 1e6:
        return _round(v / 1e6, 1) * 1e6
    if abs(v) >= 1e4:
        return _round(v / 1e3, 0) * 1e3
    return _round(v, 0)


def points(s: Series, years: dict[int, list[float]]) -> list[tuple[int, float]] | None:
    """Son YEARS tam il -> [(il, deyer)]; yoy-da musbet artim olmalidir (cumle "rose" deyir)."""
    yearly = {y: (sum(v) if s.agg == "sum" else sum(v) / len(v)) for y, v in sorted(years.items())}
    ys = sorted(yearly)
    if s.transform == "yoy":
        pts = [(y, (yearly[y] / yearly[y - 1] - 1) * 100) for y in ys if y - 1 in yearly and yearly[y - 1]]
    else:
        pts = [(y, yearly[y]) for y in ys]
    pts = [(y, speakable(v, s.unit)) for y, v in pts[-YEARS:]]
    if len(pts) < YEARS or (s.transform == "yoy" and any(v <= 0 for _, v in pts)):
        return None
    return pts


def say(v: float, unit: str) -> str:
    if unit == "$":
        return f"${v:,.2f}"
    if unit == "%":
        return f"{v:g}%"
    if abs(v) >= 1e6:
        return f"{v / 1e6:g} million"
    return f"{v:,.0f}"


def sentence(s: Series, pts: list[tuple[int, float]]) -> str:
    said = [f"{say(v, s.unit)} in {y}" for y, v in pts]
    first = said[0] if not s.noun else said[0].replace(" in ", f" {s.noun} in ", 1)
    return f"According to {s.cite_as}, {s.lead} {first}, " + ", ".join(said[1:-1]) + f" and {said[-1]}."


PICK_SYSTEM = """You choose ONE official US data series that gives real context for a business video's decision,
or none. Pick only an id from the list. Choose a series only if a US small-business owner facing this decision
would clearly use it as a benchmark (prices of their industry, wages they pay, competition in their market).
If none fits well, answer null. Answer ONLY JSON: {"id": "<id from the list>" or null, "reason": "..."}"""


def _ask_pick(topic: str, decision: str, case: dict, ask: Callable) -> Series | None:
    from llm import LLMError
    listing = "\n".join(f"- {s.id}: {s.title} ({s.tags})" for s in CATALOG)
    user = (f"Video topic: {topic}\nDecision: {decision}\nCase business: {case.get('business', '')}\n\n"
            f"Series:\n{listing}")
    try:
        got = ask(PICK_SYSTEM, user, model=PICK_MODEL, temperature=0, max_tokens=200)
    except LLMError as e:
        print(f"  data seriyasi secimi xetasi: {str(e)[:120]}", flush=True)
        return None
    return by_id(str((got or {}).get("id") or ""))


def _state_part(s: Series, case: dict, us_last: tuple[int, float], fetch: Callable) -> dict | None:
    name = " ".join(str(case.get("state") or "").split()).title()
    sid = state_id(s, name)
    if not sid:
        return None
    years = parse_fred(fetch(FRED_CSV.format(id=sid)))
    year, us_value = us_last
    if year not in years:
        return None
    raw = years[year]
    value = speakable(sum(raw) if s.agg == "sum" else sum(raw) / len(raw), s.unit)
    text = (f"In {name}, owners filed {say(value, s.unit)} of them in {year}, out of "
            f"{say(us_value, s.unit)} nationwide.")
    return {"name": name, "id": sid, "year": year, "value": value, "us_value": us_value, "sentence": text,
            "url": FRED_PAGE.format(id=sid)}


def pick_series(topic: str, decision: str, case: dict, ask: Callable | None = None,
                fetch: Callable[[str], str] = _http) -> dict | None:
    """Katalogdan secilmis + yuklenmis seriya (series.json) ve ya None (vizual olmayacaq)."""
    if ask is None:
        from llm import chat_json as ask
    s = _ask_pick(topic, decision, case or {}, ask)
    if s is None:
        print("  data seriyasi: uygun seriya yoxdur - timeseries/usmap olmayacaq", flush=True)
        return None
    try:
        pts = points(s, parse_fred(fetch(FRED_CSV.format(id=s.id))))
        state = _state_part(s, case or {}, pts[-1], fetch) if pts and s.state_prefix else None
    except Exception as e:      # noqa: BLE001 - sebeke/format xetasi = data yoxdur (uydurma yox)
        print(f"  data seriyasi yuklenmedi ({s.id}): {type(e).__name__}: {str(e)[:80]}", flush=True)
        return None
    if not pts:
        print(f"  data seriyasi {s.id}: kifayet qeder tam il yoxdur", flush=True)
        return None
    out = {"id": s.id, "title": s.title, "unit": s.unit, "cite_as": s.cite_as, "url": s.url, "unit_label": s.unit_label,
           "points": [[y, v] for y, v in pts], "sentence": sentence(s, pts)}
    if state:
        out["state"] = state
    print(f"  data seriyasi: {s.id} - {out['sentence']}", flush=True)
    return out
