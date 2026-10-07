"""Faza 2.2-2.4 (istifadeci 2026-10-07): timeseries (zamanla deyisen reqemler) ve usmap (yer/filial/bazar yayilmasi).
Sabit kodlanmis data yoxdur - reqemler danisiqdan; ekrandaki her reqem deyilmelidir (fail-closed)."""
import re

import layout
import visuals as vz

TS_NARR = "Sales were $40,000 in 2021, climbed to $55,000 in 2023 and fell to $38,000 in 2024 after the move."


def _ts(**over):
    v = {"kind": "timeseries", "title": "Sales by year", "unit": "$",
         "points": [{"label": "2021", "value": 40000}, {"label": "2023", "value": 55000},
                    {"label": "2024", "value": 38000}],
         "events": [{"index": 2, "label": "The move"}]}
    v.update(over)
    return v


def test_timeseries_with_spoken_points_passes():
    out = vz.validate_visual(_ts(), TS_NARR)
    assert out["kind"] == "timeseries" and [p["value"] for p in out["points"] if p["shown"]] == [40000, 55000, 38000]


def test_timeseries_number_not_said_is_rejected():
    bad = _ts(points=[{"label": "2021", "value": 40000}, {"label": "2022", "value": 47000},
                      {"label": "2024", "value": 38000}])
    assert vz.validate_visual(bad, TS_NARR) is None


def test_sparse_timeseries_is_interpolated_and_marked_illustrative():
    out = vz.validate_visual(_ts(), TS_NARR)
    assert out["illustrative"] is True
    hidden = [p for p in out["points"] if not p["shown"]]
    assert hidden and all(p["label"] == "" for p in hidden)
    assert out["events"][0]["index"] == next(i for i, p in enumerate(out["points"]) if p["label"] == "2024")


def test_downturn_segments_are_marked():
    out = vz.validate_visual(_ts(), TS_NARR)
    downs = [s["down"] for s in out["segments"]]
    assert any(downs) and not all(downs)


def test_dense_timeseries_is_not_illustrative():
    narr = "Visits went 120, 150, 140 and then 180 over four months."
    v = {"kind": "timeseries", "title": "Monthly visits", "unit": "",
         "points": [{"label": "Jan", "value": 120}, {"label": "Feb", "value": 150},
                    {"label": "Mar", "value": 140}, {"label": "Apr", "value": 180}], "events": []}
    assert vz.validate_visual(v, narr)["illustrative"] is False


MAP_NARR = "Dana grew from 3 locations to 12 in Texas and Ohio, then closed 2."


def _map():
    return {"kind": "usmap", "title": "Where Dana sells", "unit_label": "Locations",
            "keys": [{"value": 3, "label": "Start"}, {"value": 12, "label": "Expansion"},
                     {"value": 2, "label": "Closed"}]}


def test_usmap_with_spoken_values_passes():
    assert vz.validate_visual(_map(), MAP_NARR)["kind"] == "usmap"


def test_usmap_value_not_said_is_rejected():
    bad = _map()
    bad["keys"][1]["value"] = 15
    assert vz.validate_visual(bad, MAP_NARR) is None


def test_usmap_dots_are_seeded_by_the_slug():
    v = vz.validate_visual(_map(), MAP_NARR)
    a1, a2 = vz.place_map(v, "raise-prices"), vz.place_map(v, "raise-prices")
    b = vz.place_map(v, "hire-first-employee")
    assert a1["dots"] == a2["dots"] and a1["dots"] != b["dots"]
    assert len(a1["dots"]) >= 12 and len(a1["outline"]) > 20


def test_usmap_dots_are_inside_the_map_box():
    m = vz.place_map(vz.validate_visual(_map(), MAP_NARR), "s")
    x, y, w, h = layout.MAP_BOX
    assert all(x <= dx <= x + w and y <= dy <= y + h for dx, dy in m["dots"])


def test_map_counter_and_box_avoid_owl_and_captions():
    for box in (layout.MAP_BOX, layout.MAP_COUNTER, layout.AREA):
        assert not layout.overlaps(box, layout.OWL_ZONE) and not layout.overlaps(box, layout.CAPTION_ZONE), box


def test_python_layout_matches_the_remotion_area():
    src = open(r"C:\YouTubeAI\Remotion\src\visuals\common.tsx", encoding="utf-8").read()
    m = re.search(r"AREA = \{left: (\d+), top: (\d+), width: (\d+), height: (\d+)\}", src)
    assert tuple(int(g) for g in m.groups()) == layout.AREA


def test_llm_prompt_offers_timeseries_and_usmap():
    low = vz.SYSTEM.lower()
    assert "timeseries" in low and "usmap" in low
    assert "time" in low and ("location" in low or "branch" in low)
    assert {"timeseries", "usmap"} <= set(vz.KINDS)


def test_maps_are_placed_with_the_episode_slug_before_saving():
    import inspect
    import scene_plan
    v = vz.validate_visual(_map(), MAP_NARR)
    out = vz.finalize_maps([{"visual": v}, {"visual": None}], "slug-a")
    assert out[0]["visual"]["dots"] and out[1]["visual"] is None
    assert "finalize_maps(" in inspect.getsource(scene_plan.main)


# --- Faza 2.6: generik kart qadagasi ---

CTX_PLAN = {"case": {"owner": "Rosa Diaz", "business": "a catering firm"},
            "model": {"variables": [{"name": "customers", "value": 40, "unit": "customers", "label": "weekly customers"},
                                    {"name": "price", "value": 50, "unit": "$", "label": "event price"}]}}
FLOW_NARR = "Rosa looks at what changed, plans her next move and weighs her choices before the busy season."


def test_generic_flow_steps_are_rejected():
    v = {"kind": "flow", "title": "How Rosa decides", "steps": ["Analyze Changes", "Forecast Actions", "Evaluate Options"]}
    assert vz.validate_visual(v, FLOW_NARR) is not None             # kontekstsiz kohne davranis
    assert vz.validate_visual(v, FLOW_NARR, ctx=vz.case_context(CTX_PLAN)) is None


def test_flow_steps_with_case_owner_object_or_variable_pass():
    v = {"kind": "flow", "title": "How Rosa decides",
         "steps": ["Rosa checks costs", "Catering menu review", "Weekly customers count"]}
    assert vz.validate_visual(v, FLOW_NARR, ctx=vz.case_context(CTX_PLAN)) is not None


def test_generic_timeline_events_are_rejected():
    v = {"kind": "timeline", "title": "Rosa's plan", "events": [
        {"label": "Identify issues", "when": ""}, {"label": "Review results", "when": ""},
        {"label": "Monitor progress", "when": ""}]}
    assert vz.validate_visual(v, FLOW_NARR, ctx=vz.case_context(CTX_PLAN)) is None


def test_at_most_one_flow_per_video():
    scores = [5, 9, 9, 9, 9]
    kinds = ["", "flow", "flow", "compare", "timeline"]
    picked = vz.choose_animated(scores, share=1.0, kinds=kinds, titles=["a", "b", "c", "d", "e"])
    assert sum(1 for i in picked if kinds[i] == "flow") == 1


def test_animate_abstract_obeys_the_card_rules():
    scenes = [{"section": "S", "narration": FLOW_NARR, "visual": {"kind": "flow", "title": "Old flow", "steps": []}},
              {"section": "S", "narration": FLOW_NARR}]

    def fake(system, user, **kw):
        return {"scenes": [{"n": 2, "score": 8, "visual": {"kind": "flow", "title": "Rosa's next steps",
                                                            "steps": ["Rosa checks costs", "Catering menu review",
                                                                      "Weekly customers count"]}}]}
    assert vz.animate_abstract(scenes, [2], "T", chat=fake, plan=CTX_PLAN) == {}      # ikinci flow yox
