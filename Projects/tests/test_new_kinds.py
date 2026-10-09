"""Reyestr #135 (istifadeci 2026-10-10: "gozel, maraqli ve bir-birinin eynisi olmayan animasiyalar"): 6 yeni nov -
waterfall, gauge, dotgrid, balance, funnel, versus. Her reqem danisiqda deyilmelidir (fail-closed)."""
import os

import motion
import remotion_build as rb
import visuals as v

SRC = r"C:\YouTubeAI\Remotion\src"
NEW = ("waterfall", "gauge", "dotgrid", "balance", "funnel", "versus")


def test_new_kinds_are_offered_and_have_entrance_variants():
    for k in NEW:
        assert k in v.KINDS and f"- {k}:" in v.SYSTEM
        assert len(motion.VARIANTS[k]) >= 3, k


def test_every_kind_has_a_remotion_component():
    scene = open(os.path.join(SRC, "visuals", "AnalyticsScene.tsx"), encoding="utf-8").read()
    types = open(os.path.join(SRC, "types.ts"), encoding="utf-8").read()
    for k in NEW:
        assert f"case '{k}'" in scene and f"kind: '{k}'" in types, k


WF = "Lisa brings in $10,000 a month, pays $4,000 for food and $3,000 for rent, and keeps $3,000."


def test_waterfall_checks_its_arithmetic_and_that_each_step_is_said():
    good = {"kind": "waterfall", "title": "Where the money goes", "start": {"label": "Revenue", "value": 10000},
            "steps": [{"label": "Food", "value": -4000}, {"label": "Rent", "value": -3000}],
            "end": {"label": "Profit", "value": 3000}}
    spec = v.validate_visual(good, WF)
    assert spec and [s["sign"] for s in spec["steps"]] == ["-", "-"] and spec["steps"][0]["value"] == 4000
    assert v.covers_figures(spec, WF)
    wrong = {**good, "end": {"label": "Profit", "value": 4000}}
    assert v.validate_visual(wrong, WF.replace("$3,000.", "$4,000.")) is None      # 10000-4000-3000 != 4000
    unsaid = {**good, "steps": [{"label": "Food", "value": -4500}, {"label": "Rent", "value": -2500}]}
    assert v.validate_visual(unsaid, WF) is None


def test_gauge_needs_a_said_scale_unless_it_is_a_percent():
    pct = "Lisa's tables are full 85% of the evening."
    assert v.validate_visual({"kind": "gauge", "title": "Evening seats filled", "value": 85, "unit": "%",
                              "label": "Seats filled"}, pct)
    cnt = "Lisa needs 400 extra customers and today she gets 250."
    ok = {"kind": "gauge", "title": "Toward the goal", "value": 250, "max": 400, "label": "Extra customers"}
    assert v.validate_visual(ok, cnt)
    assert v.validate_visual({**ok, "max": None}, cnt) is None
    assert v.validate_visual({**ok, "value": 500}, cnt + " 500") is None          # deyer skaladan boyuk


def test_dotgrid_shows_a_said_percentage():
    n = "About 30% of first-time guests come back."
    assert v.validate_visual({"kind": "dotgrid", "title": "Guests who return", "value": 30,
                              "label": "Come back"}, n)
    assert v.validate_visual({"kind": "dotgrid", "title": "Guests who return", "value": 35,
                              "label": "Come back"}, n) is None


def test_balance_and_versus_work_without_numbers():
    n = "Lisa weighs the comfort of a single shop against the reach of two."
    bal = {"kind": "balance", "title": "Comfort or reach", "heavier": "right",
           "left": {"label": "Single shop", "value": None, "note": "Easy to run"},
           "right": {"label": "Two shops", "value": None, "note": "More reach"}}
    assert v.validate_visual(bal, n)["heavier"] == "right"
    assert v.validate_visual({**bal, "heavier": "middle"}, n) is None
    vs = {"kind": "versus", "title": "Single shop or two", "left": {"label": "Single shop", "value": None},
          "right": {"label": "Two shops", "value": None}}
    assert v.validate_visual(vs, n)


def test_funnel_stages_shrink_and_are_said():
    n = "Of 1,000 visitors, 300 order and 90 come back."
    f = {"kind": "funnel", "title": "From visit to regular", "stages": [
        {"label": "Visitors", "value": 1000}, {"label": "Orders", "value": 300}, {"label": "Regulars", "value": 90}]}
    assert v.validate_visual(f, n)
    grow = {**f, "stages": list(reversed(f["stages"]))}
    assert v.validate_visual(grow, n) is None


def test_new_kinds_reveal_their_elements_when_spoken():
    spec = v.validate_visual({"kind": "waterfall", "title": "Where the money goes",
                              "start": {"label": "Revenue", "value": 10000},
                              "steps": [{"label": "Food", "value": -4000}, {"label": "Rent", "value": -3000}],
                              "end": {"label": "Profit", "value": 3000}}, WF)
    els = rb.visual_elements(spec)
    assert [e["value"] for e in els] == [10000, 4000, 3000, 3000]
