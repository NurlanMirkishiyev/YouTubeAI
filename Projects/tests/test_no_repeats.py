"""Istifadeci (2026-09-28): tekrar kadrlar QETI olmasin - bir epizodda eyni fon/obyekt iki defe yox.
E2E pricing: 55 sehneden 10-u eyni ehtiyat fon, 6 peceniye, 3 donuz qumbarasi, 2 eyni sikke idi."""
import json

import pytest

import bg_dedupe
import check_bgs as cb
import scene_plan
import stages as st


# --- scene_plan: eyni esas obyekt butun epizodda yalniz 1 defe --------------------------------

def test_same_hero_anywhere_in_the_episode_is_a_repeat():
    prompts = [f"a shiny {n} on a wooden table" for n in
               "kettle lamp vase clock globe drum kite boat bell tent sled cup".split()]
    prompts[0] = prompts[9] = "a glass jar filled with coins"
    prompts[9] += ", close-up"
    subjects = [f"s{k}" for k in range(len(prompts))]
    assert scene_plan.repeats(prompts, subjects, window=3) == [9]


def test_hero_of_a_stack_or_pile_is_the_object_inside():
    assert scene_plan.hero("A stack of cookies on a simple wooden table.") == "cookie"
    assert scene_plan.hero("a pile of gold coins on a desk") == "coin"
    assert scene_plan.hero("a tray of freshly baked cookies cooling on a rack") == "tray"


def test_plan_output_never_repeats_a_prompt_or_hero(monkeypatch):
    monkeypatch.setattr(scene_plan, "chat_json", lambda system, user, **kw: {"scenes": [
        {"n": int(n), "subject": "cookie", "bg_prompt": "a single cookie on a wooden table next to a plate",
         "sprite": "front", "owl_action": "pointing, curious"}
        for n in __import__("re").findall(r"(?m)^(\d+)\. \[", user)]})
    scenes = [{"narration": f"line {k} about prices", "section": "S"} for k in range(6)]
    out = scene_plan.plan(scenes, list(scene_plan.VIDEO_POSES))
    prompts = [s["bg_prompt"] for s in out]
    heroes = [scene_plan.hero(p) for p in prompts]
    assert len(set(prompts)) == len(prompts) and len(set(heroes)) == len(heroes)


def test_pick_fallbacks_refuses_to_reuse_when_the_pool_runs_out():
    with pytest.raises(ValueError):
        scene_plan.pick_fallbacks(len(scene_plan.FALLBACK_POOL) + 1, set())


# --- check_bgs: yeni prompt epizodda olan obyekti tekrarlamir ---------------------------------

def test_next_prompt_skips_pool_items_whose_object_is_already_in_the_episode():
    pool = scene_plan.FALLBACK_POOL
    used = {pool[0], f"another {scene_plan.hero(pool[1])} somewhere"}
    got = cb.next_prompt("", attempt=cb.MAX_ATTEMPTS, used=used)
    assert got in pool and scene_plan.hero(got) not in {scene_plan.hero(u) for u in used}


def test_next_prompt_rejects_a_judge_fix_that_repeats_an_episode_object():
    used = {"a glass jar filled with coins on a desk"}
    got = cb.next_prompt("a glass jar with coins on a shelf", attempt=1, used=used)
    assert scene_plan.hero(got) != "jar"


def test_next_prompt_never_returns_the_same_fallback_twice():
    used: set[str] = set()
    for _ in range(len(scene_plan.FALLBACK_POOL)):
        used.add(cb.next_prompt("", attempt=cb.MAX_ATTEMPTS, used=used))
    assert len(used) == len(scene_plan.FALLBACK_POOL)


# --- bg_dedupe: sekil oxsarligi (CLIP) - eyni gorunen kadrlarin sonrakilari yeniden cekilir -----

def test_duplicates_keep_the_first_scene_and_redo_the_later_ones():
    sim = [[1.0, 0.95, 0.50, 0.93],
           [0.95, 1.0, 0.40, 0.60],
           [0.50, 0.40, 1.0, 0.30],
           [0.93, 0.60, 0.30, 1.0]]
    pairs, redo = bg_dedupe.find_duplicates(sim, threshold=0.88)
    assert pairs == [(1, 2), (1, 4)] and redo == [2, 4]


def test_threshold_matches_the_calibration():
    # pricing E2E: eyni sikke 0.884, ferqli obyektler (kompas/terezi) 0.873
    assert bg_dedupe.DUP_SIM == 0.88


def test_check_bgs_stage_fails_while_duplicates_remain(tmp_path):
    ctx = st.Ctx(topic="T", slug="t", ep_dir=str(tmp_path), words=1230, music=None,
                 min_seconds=480.0, max_seconds=600.0, provider="openai")
    (tmp_path / "bg_qa.json").write_text(json.dumps({"passed": True, "scenes": {}, "duplicates": [[2, 5]]}))
    assert any("tekrar" in p for p in st.qa_problems(ctx))
    (tmp_path / "bg_qa.json").write_text(json.dumps({"passed": True, "scenes": {}, "duplicates": []}))
    assert st.qa_problems(ctx) == []
