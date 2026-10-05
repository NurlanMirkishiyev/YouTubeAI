"""#58 (istifadeci 2026-10-05): her videoda en azi 1 tedqiqat ve ya resmi menbe. Menbe uydurulmamalidir:
URL yuklenir, sitat ve reqem sehifede olmalidir, domen resmi/tedqiqat olmalidir (fail-closed)."""
import json

import pytest

import research as rs

PAGE = ("Frequently Asked Questions. From 1994-2020, an average of 67.7% of new employer establishments survived "
        "at least two years. During the same period, the five-year survival rate was 48.9%, and the ten-year "
        "survival rate was 33.7%.")
GOOD = {"publisher": "U.S. Small Business Administration, Office of Advocacy", "cite_as": "the U.S. Small Business "
        "Administration", "year": 2023, "url": "https://advocacy.sba.gov/faq.pdf?utm_source=openai",
        "quote": "the five-year survival rate was 48.9%", "figure": 48.9,
        "claim": "About 48.9% of new employer businesses survive five years."}


@pytest.mark.parametrize("url, ok", [
    ("https://advocacy.sba.gov/x.pdf", True),
    ("https://www.bls.gov/bdm/", True),
    ("https://www.federalreserve.gov/publications/x.htm", True),
    ("https://hbs.harvard.edu/paper", True),
    ("https://www.nber.org/papers/w123", True),
    ("https://www.fedsmallbusiness.org/reports/x", True),
    ("https://randomblog.com/stats", False),
    ("https://sba.gov.evil.com/x", False),
])
def test_only_official_or_research_domains(url, ok):
    assert rs.is_official(url) is ok


def test_verified_source_passes_and_quote_comes_from_the_page():
    problems, quote = rs.verify({**GOOD, "quote": "paraphrased by the model"}, fetch=lambda url: PAGE)
    assert problems == [] and quote == "During the same period, the five-year survival rate was 48.9%, and the "         "ten-year survival rate was 33.7%."


def test_claim_unrelated_to_the_page_sentence_fails():
    bad = {**GOOD, "claim": "Most restaurants fail within their first 12 months of trading."}
    assert rs.verify(bad, fetch=lambda url: PAGE)[0]


def test_figure_not_on_page_fails():
    assert rs.verify({**GOOD, "figure": 52.0, "claim": "The five-year survival rate was 52%."},
                     fetch=lambda url: PAGE)[0]


def test_unofficial_domain_fails_even_with_matching_text():
    assert rs.verify({**GOOD, "url": "https://randomblog.com/x"}, fetch=lambda url: PAGE)[0]


def test_fetch_error_fails_closed():
    def boom(url):
        raise OSError("timeout")
    assert rs.verify(GOOD, fetch=boom)[0]


def test_research_returns_first_verified_candidate():
    fake = json.dumps({"sources": [{**GOOD, "url": "https://randomblog.com/x"}, GOOD]})
    got = rs.research("What Is Cash Flow?", "Should I keep 3 months of cash?",
                      search=lambda prompt: fake, fetch=lambda url: PAGE, judge=lambda *a: True)
    assert got["url"] == "https://advocacy.sba.gov/faq.pdf" and got["figure"] == 48.9


def test_research_returns_none_when_nothing_verifies():
    fake = json.dumps({"sources": [{**GOOD, "figure": 61.0, "claim": "61% of firms raised prices."}]})
    assert rs.research("T", "D?", search=lambda prompt: fake, fetch=lambda url: PAGE, attempts=2,
                       judge=lambda *a: True) is None


def test_script_must_cite_the_source_with_its_figure():
    script = ("## Section 2: Survival\n\nAccording to the U.S. Small Business Administration, about 48.9% of new "
              "employer businesses are still open after five years.\n")
    assert rs.citation_problems(script, GOOD) == []
    assert rs.citation_problems(script.replace("48.9%", "half"), GOOD)
    assert rs.citation_problems(script.replace("U.S. Small Business Administration", "experts"), GOOD)


def test_verified_but_irrelevant_source_is_skipped():
    """Probe 2026-10-05: qiymet qerari ucun 'ev sigortasi 20%' anekdotu kecirdi - hakim statistika + aidiyyet yoxlayir."""
    other = {**GOOD, "url": "https://www.federalreserve.gov/beige.htm", "figure": 33.7,
             "claim": "33.7% of new employer establishments survived ten years."}
    fake = json.dumps({"sources": [GOOD, other]})
    got = rs.research("T", "D?", search=lambda prompt: fake, fetch=lambda url: PAGE,
                      judge=lambda src, topic, decision: src["figure"] == 33.7)
    assert got["figure"] == 33.7
    assert rs.research("T", "D?", search=lambda prompt: fake, fetch=lambda url: PAGE,
                       judge=lambda src, topic, decision: False, attempts=1) is None


def test_chart_text_blob_is_not_a_quote():
    """Probe 2026-10-05: PDF qrafikinin 500 simvolluq reqem yigini 'sitat' secildi."""
    blob = "Survey N=7,837 " + " ".join(f"{k}%" for k in range(40, 90)) + " raised prices 48% employer firms " * 8
    assert rs.page_quote(48, "48% of employer firms raised prices", blob) is None


def test_judge_sees_the_decision_not_the_narrow_search_hint():
    """E2E 2026-10-05: hakim 'digital services rates' ipucu ile 48% qiymet artimi statistikasini redd etdi."""
    seen = {}

    def judge(src, topic, decision):
        seen["decision"] = decision
        return True

    prompts = []
    rs.research("T", "Should I raise prices?", search=lambda p: prompts.append(p) or json.dumps({"sources": [GOOD]}),
                fetch=lambda url: PAGE, judge=judge, fact_need="market rates for digital services")
    assert seen["decision"] == "Should I raise prices?"
    assert "market rates for digital services" in prompts[0]
