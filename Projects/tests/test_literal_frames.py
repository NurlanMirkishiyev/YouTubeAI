"""#60 (istifadeci 2026-10-05): kadrlar movzuya uygun - bos slayd olmasin, generik ve metafor kadrlar 10%-den az."""
import json

import check_bgs as cb
import scene_plan
import stages as st


def test_judge_flags_generic_or_metaphor_pictures():
    assert "generic" in cb.parse_verdict({"generic": True}).problems
    assert cb.parse_verdict({"generic": False}).ok
    low = cb.SYSTEM.lower()
    assert "metaphor" in low and "piggy bank" in low


def test_generic_share_counts_judged_generic_and_fallback_pool_pictures():
    report = {"1": {"problems": ["generic"], "prompt": "a piggy bank"},
              "2": {"problems": [], "prompt": scene_plan.FALLBACK_POOL[0]},
              "3": {"problems": [], "prompt": "a taqueria kitchen with a steel prep counter"},
              "4": {"problems": [], "prompt": "a delivery van parked at a loading dock"}}
    nums, share = cb.generic_share(report)
    assert nums == [1, 2] and share == 0.5


def test_stage_fails_when_more_than_ten_percent_of_photos_are_generic(tmp_path):
    ctx = st.Ctx(topic="T", slug="t", ep_dir=str(tmp_path), words=1, music=None, min_seconds=1, max_seconds=2,
                 provider="openai")
    (tmp_path / "bg_qa.json").write_text(json.dumps({"duplicates": [], "generic": [3, 9], "generic_share": 0.2}),
                                         encoding="utf-8")
    assert any("generik" in p for p in st.qa_problems(ctx))
    (tmp_path / "bg_qa.json").write_text(json.dumps({"duplicates": [], "generic": [3], "generic_share": 0.05}),
                                         encoding="utf-8")
    assert st.qa_problems(ctx) == []


def test_art_director_asks_for_literal_business_pictures_not_metaphors():
    low = scene_plan.SYSTEM.lower()
    assert "metaphor" in low and "literal" in low
    assert "metaphor instead" not in scene_plan.RETRY_NOTE.lower()


def test_scene_plan_tells_the_director_which_business_the_case_runs():
    note = scene_plan.case_note({"case": {"owner": "Rosa", "business": "a 30-seat taqueria", "city": "Austin",
                                          "state": "Texas"}})
    assert "taqueria" in note and "Austin" in note
    assert scene_plan.case_note({}) == ""


def test_scene_given_a_generic_pool_photo_is_animated_at_plan_time():
    """#69: scene_plan hovuz fonu (gear, stopwatch, port) verdiyi sehne foto olaraq qalmir - animasiya."""
    import scene_plan
    pool = scene_plan.FALLBACK_POOL[0]
    planned = [{"narration": "a", "bg_prompt": "a design studio desk", "visual": None},
               {"narration": "b", "bg_prompt": pool, "visual": None},
               {"narration": "c", "bg_prompt": pool, "visual": {"kind": "flow"}}]
    asked = {}

    def animate(scenes, nums):
        asked["nums"] = nums
        return {2: {"kind": "compare", "title": "T"}}
    out = scene_plan.animate_pool_scenes(planned, animate)
    assert asked["nums"] == [2]
    assert out[1]["visual"]["kind"] == "compare" and out[0]["visual"] is None
    assert planned[1]["visual"] is None          # giris deyismir


def test_plan_time_pool_animation_respects_the_cap():
    import scene_plan
    pool = scene_plan.FALLBACK_POOL[0]
    planned = [{"narration": "a", "bg_prompt": "", "visual": {"kind": "flow"}}] * 7 + \
              [{"narration": "b", "bg_prompt": pool, "visual": None}] * 3
    asked = {}
    scene_plan.animate_pool_scenes(planned, lambda sc, nums: asked.setdefault("nums", nums) and {})
    assert asked.get("nums") is None          # 7/10 = tavan - hec biri animasiyaya getmir
