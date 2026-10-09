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


def test_clip_threshold_is_a_candidate_filter_below_real_repeats():
    # CLIP yalniz namized secir, son qerar hakimdedir (#31). pricing E2E-2: iki qol saati 0.878 idi
    # ve 0.88 hedde tutulmamisdi; eyni sikke 0.884 - namized hedd her ikisinden asagi olmalidir
    assert bg_dedupe.DUP_SIM <= 0.85


def test_clip_candidate_threshold_is_wide_enough_for_same_kind_objects():
    # Reyestr #48 (2026-10-03): istifadeci yene "eyni/tekrar sekiller" gordu. Ehtiyat tedbiri: CLIP namized
    # penceresi genislenir ki, ferqli gorunuslu eyni nov obyekt hakime catsin (deqiq oxsarliq olculmeyib).
    assert bg_dedupe.DUP_SIM <= 0.80


def test_check_bgs_stage_fails_while_duplicates_remain(tmp_path):
    ctx = st.Ctx(topic="T", slug="t", ep_dir=str(tmp_path), words=1230, music=None,
                 min_seconds=480.0, max_seconds=600.0, provider="openai")
    (tmp_path / "bg_qa.json").write_text(json.dumps({"passed": True, "scenes": {}, "duplicates": [[2, 5]]}))
    assert any("tekrar" in p for p in st.qa_problems(ctx))
    (tmp_path / "bg_qa.json").write_text(json.dumps({"passed": True, "scenes": {}, "duplicates": []}))
    assert st.qa_problems(ctx) == []


# --- CLIP namized cutlerini vision hakimi tesdiqleyir (reyestr #31) ------------------------------
# pricing E2E-2: saniyeolcen/kompas/qum saati (hamisi taxta ustunde "vaxt" esyasi) CLIP-de 0.897-0.918
# cixdi, eyni sikke ise 0.884 idi - tek hedd ile ayrilmir, ona gore iki sekli gpt-4o muqayise edir.

def test_clip_pairs_that_the_judge_calls_different_are_not_duplicates():
    same = {(5, 49): False, (5, 51): False, (3, 7): True}
    out = cb.confirm_duplicates([[5, 49], [5, 51], [3, 7]], lambda a, b: same[(a, b)])
    assert out == {"pairs": [[3, 7]], "redo": [7]}


def test_confirmed_duplicates_keep_the_first_scene_of_each_group():
    out = cb.confirm_duplicates([[2, 5], [2, 9], [5, 9]], lambda a, b: True)
    assert out == {"pairs": [[2, 5], [2, 9], [5, 9]], "redo": [5, 9]}


def test_judge_error_on_a_pair_counts_as_duplicate():
    # hakim elcatmazdirsa ehtiyatli ol: tekrar sayilir (qeti qayda), sonraki sehne yeniden cekilir
    out = cb.confirm_duplicates([[1, 4]], lambda a, b: None)
    assert out == {"pairs": [[1, 4]], "redo": [4]}


def test_parse_same_verdict_only_true_is_same():
    assert cb.parse_same({"same": True}) is True
    assert cb.parse_same({"same": False}) is False
    assert cb.parse_same({"same": "yes"}) is None and cb.parse_same({}) is None


# Reyestr #46 (2026-10-03): giris karti 1-ci, cixis karti son sehnenin fotosunu tekrar gosterirdi
def test_cards_do_not_reuse_scene_photos():
    import remotion_build as rb
    data = {"intro_seconds": 3.0, "outro_seconds": 5.0, "scenes": [
        {"duration": 6.0, "sprite": "front", "pos": "right", "spoken_title": None},
        {"duration": 6.0, "sprite": "front", "pos": "right", "spoken_title": None}]}
    p = rb.episode_props(data, "T", [], {"front": (100, 200), "three_q": (100, 200)})
    scene_bgs = {s["bg"] for s in p["scenes"]}
    assert p["introBg"] is None and p["outroBg"] is None
    assert not scene_bgs & {p["introBg"], p["outroBg"]}


# --- E2E hire-first-employee (2026-10-09): tek case biznesinde "yer" kadrlari tekrar olurdu ----------
# "A photo of a bakery kitchen with ovens" (hero "photo") ve "a well-equipped bakery kitchen" (hero "kitchen")
# hero-ya gore ferqli idi, CLIP + hakim ise eyni yer dedi; check_bgs 13 tekrar cutle dayandi.

def test_place_shots_of_the_case_business_share_one_hero():
    places = ["A photo of a bakery kitchen with ovens", "a well-equipped bakery kitchen with ovens",
              "a cozy bakery with display cases", "an Interior of a bakery with pastries on display shelves",
              "a simple training area in the bakery with tools"]
    assert {scene_plan.hero(p) for p in places} == {"place"}


def test_photo_of_prefix_is_not_the_hero():
    assert scene_plan.hero("A photo of a wooden bread basket in the bakery") == "basket"
    assert scene_plan.hero("an image of a stainless steel mixer") == "mixer"


def test_ing_compound_noun_keeps_its_head():
    # E2E hire-first-employee: "rolling pin" -> hero "wooden" idi, 17/56 eyni oklov kadri tutulmadi
    assert scene_plan.hero("A wooden rolling pin on a floured surface in a bakery kitchen") == "pin"
    assert scene_plan.hero("a stainless baking sheet with cookies") == "sheet"
    assert scene_plan.hero("a glass jar filling with coins") == "jar"


def test_duplicate_redraw_asks_for_a_new_case_object_not_the_generic_pool():
    used = {"a cozy bakery with display cases", "a bakery counter with fresh bread"}
    asked = []

    def suggest(feedback):
        asked.append(feedback)
        return ("a stainless steel dough sheeter on a bakery workbench",)

    got = cb.duplicate_prompt("a bakery counter with fresh bread", used, suggest)
    assert got == "a stainless steel dough sheeter on a bakery workbench"
    assert got not in scene_plan.FALLBACK_POOL and "counter" in asked[0]


def test_duplicate_redraw_falls_back_to_the_pool_only_without_a_fresh_suggestion():
    used = {"a cozy bakery with display cases", "a bakery counter with fresh bread"}
    got = cb.duplicate_prompt("a bakery counter with fresh bread", used, lambda fb: ("a bakery counter at dawn",))
    assert got in scene_plan.FALLBACK_POOL
