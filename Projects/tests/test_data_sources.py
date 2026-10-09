"""Reyestr #127-#131 (istifadeci 2026-10-10: "Menbeden real data"): timeseries/usmap yalniz resmi API-den
yuklenmis real reqemlerle; uygun seriya yoxdursa vizual yox, uydurma yox."""
import json

import data_sources as ds
import research


def _fred(rows):
    return "observation_date,X\n" + "\n".join(f"{d},{v}" for d, v in rows)


def _monthly(year, value):
    return [(f"{year}-{m:02d}-01", value) for m in range(1, 13)]


APPS = ds.by_id("BABATOTALSAUS")
CPI = ds.by_id("CUSR0000SEFV")


def test_fred_csv_keeps_only_full_years():
    csv = _fred(_monthly(2023, 400000) + _monthly(2024, 450000) + [("2025-01-01", 1), ("2025-02-01", ".")])
    assert ds.parse_fred(csv) == {2023: [400000.0] * 12, 2024: [450000.0] * 12}


def test_sum_series_is_scaled_to_a_speakable_figure():
    years = {y: [v] * 12 for y, v in ((2021, 450000), (2022, 420000), (2023, 460000), (2024, 430000))}
    pts = ds.points(APPS, years)
    assert pts == [(2021, 5400000.0), (2022, 5000000.0), (2023, 5500000.0), (2024, 5200000.0)]


def test_yoy_series_gives_yearly_percent_change():
    years = {y: [v] * 12 for y, v in ((2020, 100), (2021, 104), (2022, 112), (2023, 119), (2024, 124))}
    assert ds.points(CPI, years) == [(2021, 4.0), (2022, 7.7), (2023, 6.3), (2024, 4.2)]


def test_too_few_years_means_no_series():
    assert ds.points(CPI, {2023: [1.0] * 12, 2024: [2.0] * 12}) is None


def test_falling_yoy_is_not_forced_into_a_rose_sentence():
    years = {y: [v] * 12 for y, v in ((2020, 100), (2021, 98), (2022, 99), (2023, 100), (2024, 101))}
    assert ds.points(CPI, years) is None


def test_state_series_uses_the_postal_code():
    assert ds.state_id(APPS, "Texas") == "BABATOTALSATX"
    assert ds.state_id(APPS, "Atlantis") is None
    assert ds.state_id(CPI, "Texas") is None


def test_catalog_urls_are_official_sources():
    assert ds.CATALOG and all(research.is_official(s.url) for s in ds.CATALOG)


def test_sentence_says_every_point_with_its_year_and_the_source():
    s = ds.sentence(APPS, [(2021, 5400000.0), (2022, 5000000.0), (2023, 5500000.0), (2024, 5200000.0)])
    assert s.startswith("According to the U.S. Census Bureau,")
    for part in ("5.4 million", "in 2021", "5 million", "5.5 million", "5.2 million in 2024"):
        assert part in s


# --- secim (#128) -------------------------------------------------------------------------------

def _fetch_ok(url):
    return _fred(sum((_monthly(y, 100 + 5 * (y - 2019)) for y in range(2019, 2026)), []))


def test_llm_cannot_invent_a_series_id():
    got = ds.pick_series("T", "Should?", {"state": "Texas"}, ask=lambda *a, **k: {"id": "FAKE123"}, fetch=_fetch_ok)
    assert got is None


def test_no_relevant_series_means_no_data():
    assert ds.pick_series("T", "Should?", {}, ask=lambda *a, **k: {"id": None}, fetch=_fetch_ok) is None


def test_download_error_means_no_data():
    def boom(url):
        raise OSError("down")
    assert ds.pick_series("T", "Should?", {}, ask=lambda *a, **k: {"id": "CUSR0000SEFV"}, fetch=boom) is None


def test_picked_series_carries_points_sentence_and_link():
    got = ds.pick_series("T", "Should?", {"state": "Texas"}, ask=lambda *a, **k: {"id": "CUSR0000SEFV"},
                         fetch=_fetch_ok)
    assert got["id"] == "CUSR0000SEFV" and len(got["points"]) == ds.YEARS
    assert got["url"].startswith("https://fred.stlouisfed.org/series/") and got["sentence"]
    assert "state" not in got                         # CPI stat seriyasi deyil -> usmap yox
    json.dumps(got)                                    # series.json-a yazilir


def test_state_value_only_for_a_known_case_state():
    got = ds.pick_series("T", "Should?", {"state": "Texas"}, ask=lambda *a, **k: {"id": "BABATOTALSAUS"},
                         fetch=_fetch_ok)
    assert got["state"]["name"] == "Texas" and got["state"]["sentence"].startswith("In Texas")
    none = ds.pick_series("T", "Should?", {"state": "Nowhere"}, ask=lambda *a, **k: {"id": "BABATOTALSAUS"},
                          fetch=_fetch_ok)
    assert "state" not in none
