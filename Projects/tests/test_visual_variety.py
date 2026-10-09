"""Reyestr #133 (istifadeci 2026-10-10: "eyni animasiyalar coxdur ... bir birinin eynisi olmayan animasiyalar"):
E2E #2-de 47 animasiyanin 33-u compare idi - promptun yegane numunesi compare idi, nov limiti yox idi."""
import json

import quality_gate as qg
import visuals as v

NUMBERLESS = "Emily thinks about the cafe and her staff."


def _compare(title):
    return {"kind": "compare", "title": title,
            "left": {"label": "Fixed cost", "value": None, "note": "Same every month"},
            "right": {"label": "Variable cost", "value": None, "note": "Grows with each cup"}}


def _timeline(title):
    return {"kind": "timeline", "title": title,
            "events": [{"label": "Emily opens", "when": "Spring"}, {"label": "Lines grow", "when": "Summer"},
                       {"label": "New hire", "when": "Fall"}]}


def test_one_kind_never_exceeds_its_share():
    kinds = ["compare", None, "timeline", None, "compare", None, "equation", None, "compare", None,
             "stats", None, "compare", None, "counter", None, "bars", None, "ring", None]
    bad = v.variety_violations(kinds, protected=set())
    cap = v.kind_cap(sum(1 for k in kinds if k))
    assert sum(1 for i, k in enumerate(kinds) if k == "compare" and i not in bad) <= cap
    assert bad and all(kinds[i] == "compare" for i in bad)


def test_same_kind_is_never_back_to_back():
    kinds = ["compare", "compare", "timeline", "equation", "stats", "counter", "bars", "ring", "line", "flow"]
    assert v.variety_violations(kinds, protected=set()) == [1]
    assert v.variety_violations(kinds, protected={1}) == [0]


def test_protected_decision_visuals_are_never_moved():
    kinds = ["table", "table", "threshold"]
    assert v.variety_violations(kinds, protected={0, 1, 2}) == []


def test_over_quota_scene_is_asked_again_with_kinds_to_avoid():
    scenes = [{"section": "Section 1: A", "narration": NUMBERLESS} for _ in range(4)]
    specs = [v.validate_visual(_compare(f"Costs view {c}"), NUMBERLESS) for c in "abcd"]
    asked = []

    def chat(system, user, **kw):
        asked.append(user)
        return {"scenes": [{"n": n, "score": 7, "visual": _timeline(t)} for n, t in ((2, "Emily early days"),
                                                                                  (4, "Emily later on"))]}
    out = v.diversify(scenes, specs, protected=set(), topic="T", chat=chat, llm_kw={}, cap=2)
    assert [s["kind"] if s else None for s in out] == ["compare", "timeline", "compare", "timeline"]
    assert "compare" in asked[0] and "avoid" in asked[0].lower()


def test_numberless_scene_that_stays_monotonous_becomes_a_photo():
    scenes = [{"section": "Section 1: A", "narration": NUMBERLESS} for _ in range(3)]
    specs = [v.validate_visual(_compare(f"Costs view {c}"), NUMBERLESS) for c in "abc"]
    out = v.diversify(scenes, specs, protected=set(), topic="T", chat=lambda *a, **k: {"scenes": []},
                      llm_kw={}, cap=2)
    assert out[1] is None and out[0] and out[2]


def test_prompt_no_longer_steers_to_compare():
    assert "use compare, timeline or equation" not in v.SYSTEM
    assert "choose compare, timeline or equation" not in v.NO_KEYPOINTS
    assert "same kind" in v.SYSTEM.lower()


def test_quality_gate_fails_a_monotonous_video(tmp_path):
    kinds = ["compare"] * 6 + ["timeline", "equation", "stats", "counter"]
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [{"visual": {"kind": k}} for k in kinds]}))
    probs = qg._variety(str(tmp_path))
    assert any("compare" in p for p in probs) and any("ardicil" in p for p in probs)
    varied = ["compare", "timeline", "equation", "stats", "counter", "bars", "ring", "flow", "line", "table"]
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [{"visual": {"kind": k}} for k in varied]}))
    assert qg._variety(str(tmp_path)) == []
    assert "visual_variety" in qg.CHECKS


def test_abstract_animation_respects_the_kind_cap():
    scenes = [{"section": "Section 1: A", "narration": NUMBERLESS,
               "visual": _compare(f"Costs view {c}") if i % 2 == 0 else None} for i, c in enumerate("abcdefgh")]
    scenes[7]["visual"] = None

    def chat(system, user, **kw):
        return {"scenes": [{"n": 8, "score": 7, "visual": _compare("Costs view z")}]}
    assert v.animate_abstract(scenes, [8], "T", chat=chat) == {}
