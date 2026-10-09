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


# --- ssenari (#129) -----------------------------------------------------------------------------

import script_qa as qa   # noqa: E402

SERIES = {"id": "BABATOTALSAUS", "points": [[2022, 5100000.0], [2023, 5500000.0], [2024, 5200000.0],
                                            [2025, 5600000.0]],
          "sentence": "According to the U.S. Census Bureau, owners across the US filed 5.1 million new business "
                      "applications in 2022, 5.5 million in 2023, 5.2 million in 2024 and 5.6 million in 2025.",
          "state": {"name": "Texas", "value": 540000.0, "us_value": 5600000.0,
                    "sentence": "In Texas, owners filed 540,000 of them in 2025, out of 5.6 million nationwide."}}
SCRIPT = ("# T\n\n## Hook\n\nEmily runs a cafe.\n\n## Section 1: Costs\n\nEmily pays rent.\n\nShe also pays staff.\n\n"
          "## Section 2: Source\n\nAccording to the SBA, 48.9% of firms grow.\n\n## Section 3: Decide\n\nEmily decides.\n")


def test_series_paragraphs_go_into_their_section_once():
    plan = {"source_section": 2, "series": SERIES}
    out = qa.ensure_series(SCRIPT, plan)
    body = qa.sections(out)["Section 1: Costs"]
    assert body.split("\n\n")[0] == "Emily pays rent."
    assert SERIES["sentence"] in body and SERIES["state"]["sentence"] in body
    assert qa.ensure_series(out, plan) == out                 # idempotent
    assert qa.series_problems(out, plan) == [] and qa.series_problems(SCRIPT, plan)


def test_series_moves_to_section_2_when_section_1_holds_the_source():
    out = qa.ensure_series(SCRIPT, {"source_section": 1, "series": SERIES})
    assert SERIES["sentence"] in qa.sections(out)["Section 2: Source"]


def test_no_series_changes_nothing():
    assert qa.ensure_series(SCRIPT, {"source_section": 2}) == SCRIPT
    assert qa.series_problems(SCRIPT, {"source_section": 2}) == []


def test_series_values_are_allowed_figures():
    assert qa.series_figures({"series": SERIES}) == [5100000.0, 5500000.0, 5200000.0, 5600000.0, 540000.0]


def test_series_values_count_as_trusted_numbers_in_the_audit(tmp_path):
    import number_audit
    (tmp_path / "meta.json").write_text(json.dumps({"plan": {"model": {"variables": []}}}))
    (tmp_path / "series.json").write_text(json.dumps(SERIES))
    assert 540000.0 in number_audit.trusted_numbers(str(tmp_path))


# --- vizual (#130) ------------------------------------------------------------------------------

import data_visuals as dv   # noqa: E402
import visuals             # noqa: E402

TS_SERIES = {**SERIES, "title": "New business applications", "unit": "", "unit_label": "Applications"}


def _scenes(*narrations):
    return [{"section": "Section 1: Costs", "narration": n} for n in narrations]


def test_series_becomes_a_timeseries_on_the_scene_that_speaks_it():
    scenes = _scenes("Emily pays rent.", SERIES["sentence"], SERIES["state"]["sentence"])
    got = dv.series_visuals(scenes, TS_SERIES, visuals.validate_visual)
    ts = got[1]
    assert ts["kind"] == "timeseries" and ts["illustrative"] is False
    assert [p["value"] for p in ts["points"]] == [5100000.0, 5500000.0, 5200000.0, 5600000.0]
    assert [p["label"] for p in ts["points"]] == ["2022", "2023", "2024", "2025"]
    m = got[2]
    assert m["kind"] == "usmap" and [k["value"] for k in m["keys"]] == [540000.0, 5600000.0]


def test_series_not_spoken_gives_no_visual():
    assert dv.series_visuals(_scenes("Emily pays rent."), TS_SERIES, visuals.validate_visual) == {}


def test_split_series_sentence_with_too_few_points_is_not_drawn():
    half = "Owners filed 5.1 million applications in 2022 and 5.5 million in 2023."
    assert dv.series_visuals(_scenes(half), TS_SERIES, visuals.validate_visual) == {}


def test_plan_visuals_forces_the_series_visual(monkeypatch):
    scenes = _scenes("Emily pays rent.", SERIES["sentence"], "Emily decides.")
    out = visuals.plan_visuals(scenes, "T", chat=lambda *a, **k: {"scenes": []}, plan={"series": TS_SERIES})
    assert out[1] and out[1]["kind"] == "timeseries"


def test_episode_plan_carries_the_series(tmp_path):
    import scene_plan
    (tmp_path / "meta.json").write_text(json.dumps({"plan": {"decision": "Should?"}}))
    (tmp_path / "series.json").write_text(json.dumps(TS_SERIES))
    assert scene_plan.episode_plan(str(tmp_path))["series"]["id"] == "BABATOTALSAUS"
    (tmp_path / "series.json").write_text(json.dumps({"id": None}))
    assert "series" not in scene_plan.episode_plan(str(tmp_path))
