"""#58 (istifadeci 2026-10-05): "Ssenariye tedqiqat elave edin - her videoda en azi 1 tedqiqat ve ya resmi menbe."
Data durustluyu: menbe UYDURULMUR. gpt-4o-mini + OpenAI web_search namizedler tapir, sonra burada deterministik:
- domen resmi (.gov, .edu) ve ya tedqiqat teskilatidir (ALLOWED);
- URL yuklenir (HTML ve ya PDF), sitatin sozleri ve reqem SEHIFEDE var;
yoxlanmayan namized atilir; hec biri kecmese None -> script_gen dayanir (fail-closed).
Cixis: Episodes\\<slug>\\research.json; skriptde menbe adi + reqem eyni abzasda deyilmelidir (citation_problems).
"""
from __future__ import annotations

import io
import json
import math
import re
import urllib.parse
import urllib.request
from typing import Callable

from llm import PROVIDERS, LLMError, _api_key, _post
from math_check import find_numbers

ALLOWED = ("fedsmallbusiness.org", "stlouisfed.org", "nber.org", "oecd.org", "worldbank.org", "imf.org", "bis.org", "pewresearch.org", "brookings.edu",
           "ssrn.com", "doi.org", "jstor.org", "aeaweb.org", "nature.com", "sciencedirect.com", "nfib.com",
           "kauffman.org", "jpmorganchase.com")
OFFICIAL_TLD = (".gov", ".edu", ".mil")
# Probe 2026-10-05: gpt-4o-mini axtarisi 12 namizedden 0 statistika tapdi (Beige Book anekdotlari) - axtaris
# aleti ucun gpt-4o; ssenari metni yene gpt-4o-mini ile yazilir (istifadeci qerari)
SEARCH_MODEL = "gpt-4o"
FETCH_TIMEOUT = 30
MAX_BYTES = 15_000_000
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/129.0 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}

SEARCH_PROMPT = """Find {n} facts for a YouTube video for US small-business owners.
Video topic: {topic}
The decision the video helps the owner make: {decision}
Statistic that would help: {fact_need}

Each fact must come from an OFFICIAL US source (a .gov agency such as SBA, BLS, Census Bureau, IRS, Federal Reserve,
FTC) or a published research study (.edu university, NBER, peer-reviewed journal). No blogs, no vendors, no news.
Prefer pages a program can download and read: SBA Office of Advocacy PDFs (advocacy.sba.gov), the Fed Small Business
Credit Survey (fedsmallbusiness.org), federalreserve.gov, irs.gov, ftc.gov, nber.org, .edu PDFs. Do NOT use bls.gov
or census.gov (they block automated checks). Copy each URL exactly from your search citations - never guess a URL.
Each fact must be a SURVEY or DATASET STATISTIC (a share of firms, a rate, an average) - never an anecdote from one
business. Good places: the Fed Small Business Credit Survey report, SBA Office of Advocacy research and FAQ PDFs,
NFIB Small Business Economic Trends, Federal Reserve FEDS notes, NBER working papers.
Prefer data published in the last 3 years and give the exact publication year of each fact.
The "claim" must contain the figure written in digits, exactly as stated on that page. Use the direct URL of the page or PDF that contains the quote.

Return ONLY JSON:
{{"sources": [{{"publisher": "full name of the organisation", "cite_as": "plain spoken name, no brackets, e.g. the U.S.
Small Business Administration", "year": 2023, "url": "...", "figure": 48.9, "claim": "one plain-English sentence a narrator can say, containing the figure"}}]}}"""


def _host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower()


def is_official(url: str) -> bool:
    host = _host(url)
    if not host or urllib.parse.urlparse(url).scheme not in ("http", "https"):
        return False
    return host.endswith(OFFICIAL_TLD) or any(host == d or host.endswith("." + d) for d in ALLOWED)


def clean_url(url: str) -> str:
    """OpenAI axtarisi ?utm_source=openai elave edir - description-da temiz link."""
    parts = urllib.parse.urlparse(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_")]
    return urllib.parse.urlunparse(parts._replace(query=urllib.parse.urlencode(query)))


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        data = r.read(MAX_BYTES)
        ctype = r.headers.get("Content-Type", "")
    if data[:5] == b"%PDF-" or "pdf" in ctype:
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    html = data.decode("utf-8", "replace")
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    return re.sub(r"&nbsp;|&#160;", " ", re.sub(r"<[^>]+>", " ", html))


_STEM_MIN = 4
CLAIM_MATCH = 0.3          # iddianin mezmun sozlerinin en azi 30%-i reqemli sehife cumlesinde (kok, 4 herf)
MAX_QUOTE = 350            # PDF qrafik metni (500+ simvol reqem yigini) sitat sayilmir
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


def _stems(text: str) -> set[str]:
    return {w[:_STEM_MIN] for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= _STEM_MIN}


def _has(figure: float, text: str) -> bool:
    return any(math.isclose(v, figure, rel_tol=1e-9, abs_tol=1e-6) for _, _, v in find_numbers(text))


def page_quote(figure: float, claim: str, page: str) -> str | None:
    """Sehifede reqemi ve iddianin sozlerini dasiyan cumle (sitat SEHIFEDEN gelir, model parafrazi deyil -
    2026-10-05 probu: gpt-4o-mini sitatlari parafraz edir, URL-lerin bir qismi 404 idi)."""
    flat = " ".join(page.replace("-\n", "").split())
    want = _stems(claim)
    best, best_score = None, 0.0
    for sent in _SENTENCE.split(flat):
        if len(sent) > MAX_QUOTE or not _has(figure, sent):
            continue
        score = len(want & _stems(sent)) / max(1, len(want))
        if score > best_score:
            best, best_score = sent.strip(), score
    return best if best is not None and best_score >= CLAIM_MATCH else None


def verify(src: dict, fetch: Callable[[str], str] = fetch_text) -> tuple[list[str], str | None]:
    """(problemler, sehifeden sitat). Bos siyahi = menbe yoxlanib."""
    url = str(src.get("url") or "")
    figure = src.get("figure")
    if not isinstance(figure, (int, float)) or isinstance(figure, bool):
        return ["reqem (figure) yoxdur"], None
    if not is_official(url):
        return [f"resmi/tedqiqat domeni deyil: {_host(url) or url}"], None
    if not str(src.get("cite_as") or "").strip() or not _has(float(figure), str(src.get("claim") or "")):
        return ["cite_as ve ya reqemli claim yoxdur"], None
    try:
        page = fetch(url)
    except Exception as e:      # noqa: BLE001 - sebeke/PDF xetasi = yoxlanmadi (fail-closed)
        return [f"sehife yuklenmedi: {type(e).__name__}: {str(e)[:80]}"], None
    quote = page_quote(float(figure), str(src.get("claim")), page)
    return ([] if quote else [f"sehifede {figure:g} ve iddiaya uygun cumle yoxdur"]), quote


def _parse(text: str) -> list[dict]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [s for s in data.get("sources") or [] if isinstance(s, dict)]


def web_search(prompt: str) -> str:
    """OpenAI Responses API + web_search aleti (gpt-4o-mini) -> cavab metni."""
    prov = PROVIDERS["openai"]
    res = _post(f"{prov.base_url}/responses", _api_key(prov),
                {"model": SEARCH_MODEL, "tools": [{"type": "web_search"}], "input": prompt})
    for item in res.get("output") or []:
        if item.get("type") == "message":
            return "".join(c.get("text", "") for c in item.get("content") or [])
    raise LLMError("web_search cavabinda mesaj yoxdur")


JUDGE_SYSTEM = """You check one fact before it goes into a business video for US small-business owners.
Answer ONLY JSON: {"statistic": true/false, "relevant": true/false, "reason": "..."}
- "statistic": the fact is a measured figure from a survey, dataset or study (a share, rate, average, count) -
  NOT an anecdote, a single person's report, a forecast or a quote from one business.
- "relevant": the figure is about the same business question as the decision (e.g. a pricing statistic for a
  pricing decision, a cash statistic for a cash decision) so an owner can use it as context or a benchmark.
  It does NOT have to answer the decision by itself."""


def relevance_judge(src: dict, topic: str, decision: str) -> bool:
    """gpt-4o: yoxlanmis fakt statistikadir ve qerara aiddir (probe: 'ev sigortasi 20%' anekdotu kecirdi)."""
    from llm import chat_json
    user = "\n".join([f"Video topic: {topic}", f"Decision: {decision}", f"Publisher: {src.get('publisher')}",
                      f"Fact: {src.get('claim')}", f"Sentence on the page: {src.get('quote')}"])
    try:
        d = chat_json(JUDGE_SYSTEM, user, model="gpt-4o", temperature=0, max_tokens=200)
    except LLMError as e:
        print(f"  menbe hakimi xetasi: {str(e)[:120]}", flush=True)
        return False
    print(f"  menbe hakimi: statistic={d.get('statistic')} relevant={d.get('relevant')} - {d.get('reason', '')[:100]}",
          flush=True)
    return d.get("statistic") is True and d.get("relevant") is True


RETRY_HINT = "\nLook for DIFFERENT sources than usual; prefer government PDFs with survey statistics."


def research(topic: str, decision: str, search: Callable[[str], str] = web_search,
             fetch: Callable[[str], str] = fetch_text, attempts: int = 3, n: int = 4,
             judge: Callable[[dict, str, str], bool] = relevance_judge, fact_need: str = "") -> dict | None:
    """Ilk yoxlanmis (sehifede var) VE hakimden kecen (statistika, qerara aid) menbe ve ya None."""
    for k in range(attempts):
        try:
            text = search(SEARCH_PROMPT.format(n=n, topic=topic, decision=decision, fact_need=fact_need or "any")
                          + ("" if not k else RETRY_HINT))
        except LLMError as e:
            print(f"  menbe axtarisi xetasi: {str(e)[:120]}", flush=True)
            continue
        for src in by_recency(_parse(text)):
            problems, quote = verify(src, fetch)
            print(f"  menbe {_host(str(src.get('url')))}: {'OK' if not problems else '; '.join(problems)}", flush=True)
            if problems:
                continue
            found = {**src, "url": clean_url(str(src["url"])), "figure": float(src["figure"]), "quote": quote}
            if judge(found, topic, decision):
                return found
    return None


RECENT_YEARS = 3     # Faza 1.4: il >= cari il - 3 olan menbe ustundur


def _year(src: dict) -> int | None:
    try:
        return int(src.get("year"))
    except (TypeError, ValueError):
        return None


def is_old(src: dict) -> bool:
    import datetime
    y = _year(src)
    return y is None or y < datetime.date.today().year - RECENT_YEARS


def by_recency(cands: list[dict]) -> list[dict]:
    """Teze menbeler evvel (sabit sira), sonra kohneler - en tezesi birinci."""
    return sorted(cands, key=lambda s: (is_old(s), -(_year(s) or 0)))


def _paragraphs(markdown: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", markdown) if p.strip() and not p.lstrip().startswith("#")]


def _name_words(cite_as: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9.]+", cite_as.lower()) if w not in ("the", "of", "and", "u.s.", "us")]


def citation_problems(markdown: str, src: dict) -> list[str]:
    """Skriptde menbe adi ve onun reqemi EYNI abzasda deyilmelidir."""
    words = _name_words(str(src.get("cite_as") or ""))
    figure = float(src.get("figure") or math.nan)
    for p in _paragraphs(markdown):
        low = p.lower()
        named = words and all(w in low for w in words)
        has_fig = any(math.isclose(v, figure, rel_tol=1e-9, abs_tol=1e-6) for _, _, v in find_numbers(p))
        if named and has_fig:
            year = src.get("year")
            if year and is_old(src) and str(year) not in p:      # Faza 1.4: kohne menbe ili ile deyilir
                return [f"menbe kohnedir ({year}) - menbe abzasinda il deyilmelidir"]
            return []
    return [f"menbe ('{src.get('cite_as')}') ve reqemi ({figure:g}) skriptde eyni abzasda deyilmeyib"]
