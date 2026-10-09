# Real Data Visuals (timeseries / usmap) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `timeseries` and `usmap` visuals are drawn only from real numbers that the pipeline downloads from an official
data API (FRED / BLS). When no fitting series is found, the visual is skipped and nothing is invented.

**Architecture:** A new `data_sources.py` module holds a fixed CATALOG of series: FRED CSV (no key) and BLS API v1 (no
key, 25 requests per day). Each entry has an id, title, unit, `cite_as`, a source URL and topic tags.
- An LLM may only pick ids from that list (closed choice), so it cannot invent a series. Python then downloads the
  data and aggregates it by year.
- The result is written to `research.json` under `"series"`.
- `script_gen` tells the writer to say these values with their years in one section. `visuals` builds the
  timeseries/usmap deterministically from the series (like `decision_visuals`). `quality_gate` checks it fail-closed.

**Tech Stack:** Python 3 (urllib, csv, json), pytest with injected `fetch`/`pick`, existing Remotion
`DataViz.tsx::Timeseries/USMap` (unchanged).

**Spec:** User decision 2026-10-10 (AskUserQuestion): "Mənbədən real data" — research.py yoxlanmış mənbədən
(BLS/Census/SBA) zaman sırası və ya ştat datası çəksin; tapılmasa vizual olmasın, uydurma yox.

## Global Constraints

- Data honesty: chart values come only from the downloaded series. No interpolation is needed: ≥ 4 annual points
  means `illustrative=False`. No API, error or bad fit means no series, and the video goes on without the visual.
- Every number on a chart must be spoken in that scene's narration. This existing rule (`visuals._said`) stays.
- Every figure is said at most 2 times (`repeated_figures`). `number_audit` counts series values as "given".
- Census API needs a key (2026-10-10 probe: "Missing Key"), so v1 does not use it. FRED (Federal Reserve Bank of
  St. Louis) republishes Census BFS and BLS data without a key.
- Tests make no network calls (`fetch` and `pick` are parameters).
- Code comments are in ASCII-transliterated Azerbaijani.
- Default ON (Faza 5): `config.REAL_DATA = True`. Only the user may turn it off.
- No new paid image calls; at most 2 extra gpt-4o calls per video.

---

### Task 1: `data_sources.py` — catalog + download + annual aggregation (#127)

**Files:**
- Create: `Projects/data_sources.py`
- Test: `Projects/tests/test_data_sources.py`

**Interfaces:**
- Produces:
  - `CATALOG: tuple[Series, ...]`, where `Series` is a frozen dataclass:
    `id, provider ("fred"|"bls"), title, unit ("$"|"%"|""), cite_as, url, tags, per_state (bool)`.
  - `fetch_series(s: Series, state: str | None = None, fetch=_http) -> list[tuple[int, float]]` returns year
    averages, the last `YEARS = 6` complete years only.
  - `state_id(s, state) -> str`: for FRED state series, e.g. `BABATOTALSA` + `TX`.

- [ ] Step 1: Write the failing tests.
  - `test_fred_csv_is_averaged_per_full_year`: fake CSV with 2 years of monthly rows plus a half year. Expect 2
    points; the incomplete year is dropped.
  - `test_bls_json_is_averaged_per_full_year`: fake BLS JSON with M01–M12; M13 is the annual average and is skipped.
  - `test_state_series_id_uses_the_postal_code`
  - `test_unknown_state_is_rejected`
  - `test_catalog_urls_are_official`: every `url` passes `research.is_official`; `stlouisfed.org` is added to
    `ALLOWED`.
- [ ] Step 2: `pytest -q Projects/tests/test_data_sources.py` → FAIL (module not found).
- [ ] Step 3: Implement.
  - Catalog v1, about 8 series:
    - business applications (`BABATOTALSA` US + state);
    - CPI food away from home (`CUUR0000SEFV`);
    - average hourly earnings, leisure/hospitality (`CES7000000003`);
    - retail sales (`RSXFS`);
    - small-business optimism (NFIB has no API, skip);
    - commercial rent: there is no official national series — do not add one;
    - quit rate (`JTSQUR`);
    - employment cost index (`ECIWAG`);
    - PPI construction (`WPUIP2300001`).
  - Every id is verified with one real curl before it enters the catalog. An id that fails does not go in.
- [ ] Step 4: Tests PASS. Then run the full suite.
- [ ] Step 5: Registry #127 + commit.

### Task 2: Selection — closed choice + relevance judge (#128)

**Files:**
- Modify: `Projects/data_sources.py`
- Modify: `Projects/research.py` (`ALLOWED` += `stlouisfed.org`)
- Test: `Projects/tests/test_data_sources.py`

**Interfaces:**
- `pick_series(topic, decision, case_state, ask=chat_json) -> dict | None`
  - Returns `{"id", "state"|None, "points": [[year, value]], "cite_as", "url", "title", "unit", "kind":
    "timeseries"|"usmap"}`.
  - gpt-4o only sees `CATALOG` ids and titles. The answer must be an id from the catalog, otherwise None.
  - usmap is allowed only when `per_state` is true and the case's state is known. Its keys are the case state value
    and the US value for the last year (2 keys).
- `research.research_data(...)` writes `research.json["series"]`. Any error → None (fail-open for the visual only).

- [ ] Tests:
  - `test_llm_cannot_invent_a_series_id`: ask returns `"FAKE123"` → None.
  - `test_no_relevant_series_means_no_data`: ask returns `{"id": null}` → None.
  - `test_download_error_means_no_data`
  - `test_usmap_only_with_a_known_case_state`
- [ ] Implement → PASS → registry #128 + commit.

### Task 3: script_gen — the series is spoken in one section (#129)

**Files:**
- Modify: `Projects/script_gen.py` (section prompt + `settle_script`)
- Modify: `Projects/number_audit.py` (given set)
- Modify: `Projects/research.py` (`citation_problems` for series)
- Test: `Projects/tests/test_research.py`, `Projects/tests/test_number_audit.py`

- [ ] Tests:
  - `test_series_values_count_as_given_numbers`
  - `test_series_must_be_cited_with_its_years_in_one_paragraph`: missing → problem
    "seriya (<cite_as>) illeri ile deyilmeyib".
  - `test_section_prompt_lists_the_series_points`
- [ ] Implement.
  - The prompt says: "In section N, say these yearly figures in order, each once, with the year, and name
    <cite_as>".
  - The section is picked as the one that is not the decision section and is the closest to the topic. The LLM plan
    already gives `fact_need`; the series goes into the section that has the most matching `tags`, or section 2 as
    a fallback.
- [ ] PASS → registry #129 + commit.

### Task 4: visuals — deterministic timeseries/usmap from the series (#130)

**Files:**
- Modify: `Projects/visuals.py` (`plan_visuals(..., series=)`)
- Modify: `Projects/data_visuals.py` (`series_visual(series, scenes) -> (scene_index, visual) | None`)
- Test: `Projects/tests/test_data_visuals.py`

- [ ] Tests:
  - `test_series_becomes_a_timeseries_on_the_scene_that_speaks_it`: scene narration says ≥ 4 values → `kind`
    timeseries, `illustrative` False.
  - `test_series_not_spoken_gives_no_visual`
  - `test_usmap_keys_are_case_state_and_us`
  - `test_forced_series_visual_counts_toward_the_animation_cap`
- [ ] Implement.
  - Labels are years. `unit` comes from the catalog.
  - `build_timeseries`/`build_usmap` are reused, so the `said` check stays.
  - Points that are not spoken are dropped. If fewer than 4 remain → the timeseries is not built
    (`illustrative=True` is not allowed for real data).
- [ ] PASS → registry #130 + commit.

### Task 5: quality_gate + publish + config (#131)

**Files:**
- Modify: `Projects/config.py` (`REAL_DATA = True`)
- Modify: `Projects/quality_gate.py` (if research has `series` → a timeseries/usmap exists in scenes)
- Modify: `Projects/publish_pack.py` (data source link in the description)
- Modify: `docs/error_classes.md` (`--write-catalog`)
- Modify: `CLAUDE.md` (root), `Projects/CLAUDE.md`
- Test: `test_quality_gate.py`, `test_publish_pack.py`, `test_defaults.py`

- [ ] Tests:
  - `test_series_in_research_needs_a_data_visual`
  - `test_description_links_the_data_series`
  - `test_real_data_flag_is_on_by_default`
- [ ] Implement → full suite → `progress.md` (current status, next step) → commit.

### Task 6: Verification (real API, cheap)

- [ ] Run `script_gen` + `scene_plan` once on a probe episode (no image stages), for example "Should You Raise Menu
  Prices?". Expected: `research.json.series` is filled (CPI food away from home), the script says the values with
  their years, and `scenes.json` has a timeseries.
- [ ] Delete the probe folder. Report back to the user.
