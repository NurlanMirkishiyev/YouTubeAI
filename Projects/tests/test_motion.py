"""Faza 3 (istifadeci 2026-10-07): deterministik muxtəliflik - seed = slug hash; her epizoda bir motion theme;
her novun >= 3 giris varianti; kecidler bolme/adi destleri, ardicil eyni kecid yox; son 3 epizodla oxsarliq <= 50%."""
import json

import motion as mo

SCENES = [{"kind": None, "section_start": True}, {"kind": "stats", "section_start": False},
          {"kind": "bars", "section_start": False}, {"kind": None, "section_start": True},
          {"kind": "table", "section_start": False}, {"kind": "threshold", "section_start": False},
          {"kind": "timeseries", "section_start": True}, {"kind": "usmap", "section_start": False},
          {"kind": None, "section_start": False}, {"kind": "compare", "section_start": True}]


def test_every_kind_has_at_least_three_entrance_variants():
    for kind in ("stats", "bars", "line", "timeseries", "compare", "equation", "table", "threshold", "usmap",
                 "ring", "counter", "flow", "timeline", "title", "kicker", "lower_third", "cold_open"):
        assert len(mo.VARIANTS[kind]) >= 3, kind
    for k in ("title", "kicker", "lower_third", "cold_open"):
        assert "typewriter" in mo.VARIANTS[k]
    assert {"rise", "scale_pop", "mask_reveal", "digit_roll"} <= set(mo.VARIANTS["stats"])


def test_same_seed_same_plan_different_seed_different_plan():
    a, b = mo.plan_motion("raise-prices", SCENES), mo.plan_motion("raise-prices", SCENES)
    c = mo.plan_motion("hire-first-employee", SCENES)
    assert a == b and mo.signature(a) != mo.signature(c)


def test_no_transition_repeats_back_to_back_and_sets_are_separate():
    for slug in ("a", "b", "c", "d", "e"):
        p = mo.plan_motion(slug, SCENES * 3)
        tr = [s["transition"] for s in p["scenes"]]
        assert all(x != y for x, y in zip(tr, tr[1:]))
        for s in p["scenes"]:
            pool = mo.SECTION_TRANSITIONS if s["section_start"] else mo.TRANSITIONS
            assert s["transition"] in pool


def test_cold_open_always_types_and_one_theme_per_episode():
    p = mo.plan_motion("x", SCENES)
    assert p["cold_open"] == "typewriter" and p["theme"] in mo.THEMES
    assert p["backdrop"] in mo.BACKDROPS and len(mo.BACKDROPS) >= 3


def test_ken_burns_has_more_moves_at_constant_speed():
    assert {"diag_tl_br", "push_in", "tilt_up"} <= set(mo.KEN_BURNS)
    p = mo.plan_motion("x", SCENES)
    photo = [s["motion"] for s in p["scenes"] if s["kind"] is None]
    assert all(m in mo.KEN_BURNS for m in photo)


def test_history_similarity_above_half_changes_the_theme(tmp_path):
    hist = tmp_path / "_motion_history.json"
    first = mo.plan_motion("same", SCENES)
    hist.write_text(json.dumps([{"slug": f"old{i}", "theme": first["theme"], "signature": mo.signature(first)}
                                for i in range(3)]), encoding="utf-8")
    p = mo.plan_with_history("same", SCENES, str(hist))
    assert p["theme"] != first["theme"]
    assert max(mo.similarity(mo.signature(p), h["signature"]) for h in json.loads(hist.read_text())) <= 0.5


def test_history_is_appended_and_kept_short(tmp_path):
    hist = tmp_path / "_motion_history.json"
    for i in range(6):
        mo.remember(str(hist), f"ep{i}", mo.plan_motion(f"ep{i}", SCENES))
    data = json.loads(hist.read_text())
    assert data[-1]["slug"] == "ep5" and len(data) == min(6, mo.HISTORY_KEEP)


# --- Faza 3.7: nitqle sinxron vurgu ---

def _props():
    return {"fps": 30, "introFrames": 60, "scenes": [
        {"frames": 900, "visual": {"kind": "stats", "cards": [{"value": 1}, {"value": 2}, {"value": 3}]},
         "reveal": [30, 36, 40]},
        {"frames": 300, "visual": {"kind": "table", "rows": [{"before": 1}, {"before": 2}]}, "reveal": [20, 200]},
        {"frames": 300, "visual": None, "overlay": {"from": 50, "frames": 75}},
        {"frames": 300, "visual": {"kind": "threshold", "threshold": {"value": 27}}, "reveal": [100]},
    ]}


def test_emphasis_pulses_are_short_and_never_flash_more_than_three_per_second():
    em = mo.emphasis(_props())
    allp = sorted((e["at"], e) for e in em)
    assert all(e["frames"] <= round(0.4 * 30) for _, e in allp)
    ats = [a for a, _ in allp]
    assert all(sum(1 for x in ats if t <= x < t + 30) <= mo.MAX_FLASH_PER_S for t in ats)


def test_big_effects_are_at_most_one_per_twenty_seconds():
    em = [e for e in mo.emphasis(_props()) if e["big"]]
    ats = sorted(e["at"] for e in em)
    assert em and all(b - a >= 20 * 30 for a, b in zip(ats, ats[1:]))


def test_signature_from_props_matches_the_plan_signature():
    import remotion_build as rb
    from test_remotion_build import DATA, POSES
    p = rb.episode_props(DATA, "T", [], POSES, slug="s1")
    plan = mo.plan_motion("s1", [{"kind": None, "section_start": bool(s.get("spoken_title"))} for s in DATA["scenes"]])
    assert mo.signature_of_props(p) == mo.signature(plan)


def test_motion_problems_are_reported():
    import remotion_build as rb
    ok = {"motion": {"cold_open": "typewriter"}, "scenes": [], "fps": 30}
    assert rb.motion_problems(ok, [0.2, 0.4]) == []
    assert any("oxsar" in p for p in rb.motion_problems(ok, [0.7]))
    assert any("typewriter" in p for p in rb.motion_problems({**ok, "motion": {"cold_open": "word_rise"}}, []))
