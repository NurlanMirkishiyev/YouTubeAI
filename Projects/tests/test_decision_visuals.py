"""Faza 2.1 (istifadeci 2026-10-07): qerar bolmesinde deterministik (LLM-siz) vizuallar model_result-dan -
"table" (evvel/sonra/ferq) ve "threshold" (break-even). Ekrandaki her reqem sehne danisiginda deyilmelidir."""
import case_model as cm
import visuals as vz
from test_case_model import MODEL

RESULT = cm.evaluate(MODEL)
PLAN = {"model": MODEL, "model_result": RESULT, "case": {"owner": "Rosa", "business": "a catering firm"}}
DEC = "Section 4: The Decision"


def _scenes(*narrs, section=DEC):
    return [{"section": "Section 1: Margin", "narration": "Rosa charges $50 and each order costs her $40."}] + \
        [{"section": section, "narration": n} for n in narrs]


def test_table_shows_before_after_and_change_that_are_said():
    narr = "Revenue drops from $2,000 to $1,870, but profit climbs from $400 to $510, a $110 gain."
    t = vz.decision_table(RESULT, narr)
    rows = {r["label"]: r for r in t["rows"]}
    assert t["kind"] == "table"
    assert rows["Profit"]["before"] == 400 and rows["Profit"]["after"] == 510 and rows["Profit"]["delta"] == 110
    assert rows["Revenue"]["delta"] is None          # -$130 deyilmeyib -> gosterilmir
    assert vz.validate_visual(t, narr) == t


def test_table_needs_a_spoken_before_after_pair():
    assert vz.decision_table(RESULT, "Profit climbs to $510.") is None


def test_threshold_gauge_marks_the_threshold_and_the_current_value_when_said():
    narr = "Rosa has 40 customers today and needs at least 27 to keep her profit."
    t = vz.decision_threshold(PLAN, narr)
    assert t["kind"] == "threshold" and t["threshold"]["value"] == 27 and t["current"]["value"] == 40
    assert vz.validate_visual(t, narr) == t


def test_threshold_requires_the_threshold_value_to_be_said():
    assert vz.decision_threshold(PLAN, "Rosa needs enough customers to keep her profit.") is None


def test_threshold_curve_when_a_variable_crosses_the_baseline():
    m = {**MODEL, "threshold": {"name": "stay_needed", "expr": "before_profit / (customers * (price_new - unit_cost))",
                                "rounding": "none", "meaning": "share of customers that must stay"}}
    plan = {"model": m, "model_result": cm.evaluate(m)}
    narr = "Profit holds at $400 as long as 67% of her customers stay."
    t = vz.decision_threshold(plan, narr)
    assert t["curve"] and t["curve"]["var"] == "retention" and t["curve"]["result"] == "profit"
    assert abs(t["curve"]["cross"] - 0.6667) < 1e-3
    assert t["threshold"]["value"] == 67 and t["threshold"]["unit"] == "%"     # ekranda deyilen kimi
    assert vz.validate_visual(t, narr) == t


def test_decision_visuals_are_forced_into_the_decision_section():
    scenes = _scenes("Revenue drops from $2,000 to $1,870, but profit climbs from $400 to $510.",
                     "So Rosa needs at least 27 customers at the new price; she has 40.")
    got = vz.decision_visuals(scenes, PLAN)
    assert got[1]["kind"] == "table" and got[2]["kind"] == "threshold"
    assert 0 not in got                               # qerar bolmesinden kenarda deyil


def test_planned_visuals_keep_the_decision_visuals():
    scenes = _scenes("Revenue drops from $2,000 to $1,870, but profit climbs from $400 to $510.",
                     "So Rosa needs at least 27 customers at the new price; she has 40.")

    def fake(system, user, **kw):
        return {"scenes": [{"n": n, "score": 9, "visual": {"kind": "stats", "title": "Numbers", "cards": []}}
                           for n in (1, 2, 3)], "ok": [True], "labels": [], "title": "x"}
    specs = vz.plan_visuals(scenes, "T", chat=fake, plan=PLAN)
    assert specs[1]["kind"] == "table" and specs[2]["kind"] == "threshold"


def test_script_decision_section_must_state_a_before_after_pair_and_the_threshold():
    from test_case_model import _script
    plan = {**PLAN, "decision": "Should Rosa raise her price?"}
    bad = _script("Rosa raises her price and keeps most clients.")
    probs = cm.case_problems(bad, plan)
    assert any("evvel/sonra" in p for p in probs) and any("threshold" in p for p in probs)
    good = _script("Revenue drops from $2,000 to $1,870, but profit climbs from $400 to $510. "
                   "She needs at least 27 customers.")
    assert not any("evvel/sonra" in p or "threshold" in p for p in cm.case_problems(good, plan))


def test_missing_decision_figures_get_a_section_fix():
    import script_qa as qa
    from test_case_model import _script
    from test_script_story import SOURCE
    plan = {**PLAN, "decision": "Should Rosa raise her price?", "answer": "Raise it if at least 27 customers stay.",
            "case": {"owner": "Rosa", "business": "a catering firm", "city": "Austin", "state": "Texas"}}
    md = _script("Rosa raises her price and keeps most clients.")
    fixes = qa.story_fixes(md, plan, SOURCE, "Section 1: Margin")
    dec = [f for f in fixes if f["section"] == "Section 2: Decision"]
    assert dec and "from $2,000 to $1,870" in dec[0]["instruction"] and "27" in dec[0]["instruction"]


def test_scene_plan_passes_the_case_plan_to_the_visual_planner():
    import inspect
    import scene_plan
    assert "plan=" in inspect.getsource(scene_plan.main).split("plan_visuals(")[1].split(")")[0]
