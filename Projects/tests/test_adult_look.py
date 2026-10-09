"""Istifadeci (2026-09-28): videolar usaq videosu kimi gorunmesin. Secim A: realist fotoqrafiya fonlari,
yetkin auditoriya ucun ssenari, usaq musiqisi yox. Bayqus (sabit qerar) deyismir."""
import re

import check_bgs as cb
import music_gen as mg
import render_bgs as rb
import scene_plan
import script_gen

KIDDY = re.compile(r"pixar|cartoon|kids?|child|toy|playful|10-year|lemonade|school|ukulele|glockenspiel|"
                   r"carnival|candy|playground", re.I)


def test_background_style_is_realistic_photography():
    assert "photo" in rb.STYLE.lower()
    assert not KIDDY.search(rb.STYLE)
    assert "no toys" in rb.RULES.lower()


# Promptlar usaq seylerini QADAGAN edir ("never toys ...") - ona gore burada usaq cercivesi axtarilir
KID_FRAMING = re.compile(r"for kids|kids and beginners|10-year|lemonade stand|school club|pixar", re.I)


def test_scene_director_and_fallbacks_are_not_for_kids():
    assert not KID_FRAMING.search(scene_plan.SYSTEM)
    assert "adult" in scene_plan.SYSTEM.lower()
    assert [p for p in scene_plan.FALLBACK_POOL if KIDDY.search(p)] == []
    assert not KIDDY.search(scene_plan.FALLBACK_BG)


def test_fallback_pool_is_large_enough_for_unique_scenes():
    pool = scene_plan.FALLBACK_POOL
    assert len(pool) >= 40
    assert len({scene_plan.hero(p) for p in pool}) == len(pool)      # her ehtiyat fon ayri obyekt


def test_clean_bg_prompt_drops_toys_and_kid_things():
    assert scene_plan.clean_bg_prompt("a red toy rocket, a wooden desk in a bright office") == \
        "a wooden desk in a bright office"
    assert scene_plan.clean_bg_prompt("a colorful carnival ring toss game, a candy jar") == scene_plan.FALLBACK_BG


def test_judge_rejects_childish_images():
    assert ("childish", "childish") in cb.CHECKS
    assert "toy" in cb.SYSTEM.lower()
    v = cb.parse_verdict({"childish": True, "fix_prompt": "a steel espresso machine in a cafe"})
    assert not v.ok and v.problems == ("childish",)


def test_script_is_written_for_adults():
    assert not KID_FRAMING.search(script_gen.SYSTEM)
    assert "adult" in script_gen.SYSTEM.lower()


def test_music_has_no_kids_styles():
    assert [s for s in mg.STYLES if KIDDY.search(s)] == []
    assert len(mg.STYLES) >= 4


def test_fallback_prompts_survive_the_word_filters_unchanged():
    # filtr ehtiyat fonu kesib/evez edirdi ("a chess board" -> FALLBACK_BG): o zaman tekrar yaranir
    assert [p for p in scene_plan.FALLBACK_POOL if scene_plan.clean_bg_prompt(p) != p] == []
