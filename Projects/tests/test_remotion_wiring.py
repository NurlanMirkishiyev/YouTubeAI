"""Faza 3 (istifadeci 2026-10-07): Python hereket plani (motion.py) Remotion-da HEQIQETEN oynadilir.
Plan props-a yazilir, amma Remotion onu oxumasa her epizod eyni gorunur - bu testler elaqeni qoruyur:
kecid adlari, Ken Burns hereketleri, variantlar, vurgu qati, editorial film gorunusu, altyazida reqem rengi (3.9)."""
import os
import re

import motion
import remotion_build as rb

SRC = r"C:\YouTubeAI\Remotion\src"
PRES = r"C:\YouTubeAI\Remotion\node_modules\@remotion\transitions\dist\presentations"


def _read(*parts: str) -> str:
    return open(os.path.join(SRC, *parts), encoding="utf-8").read()


def _block(text: str, name: str) -> str:
    m = re.search(rf"const {name}\b[^\n]*?=\s*\{{(.*?)\n\}};", text, re.S)
    assert m, f"{name} tapilmadi"
    return m.group(1)


def test_every_planned_transition_has_a_remotion_presentation():
    table = _block(_read("Episode.tsx"), "TRANSITION_PRESETS")
    names = set(re.findall(r"^\s*(\w+):", table, re.M))
    assert set(motion.TRANSITIONS) | set(motion.SECTION_TRANSITIONS) <= names


def test_transition_imports_exist_in_the_installed_package():
    for mod in re.findall(r"from '@remotion/transitions/([\w-]+)'", _read("Episode.tsx")):
        assert os.path.isfile(os.path.join(PRES, f"{mod}.js")), mod


def test_every_ken_burns_motion_is_implemented():
    names = set(re.findall(r"^\s*(\w+):", _block(_read("Background.tsx"), "MOTIONS"), re.M))
    assert set(motion.KEN_BURNS) <= names
    union = re.search(r"export type Motion =([^;]+);", _read("types.ts")).group(1)
    assert set(motion.KEN_BURNS) <= set(re.findall(r"'(\w+)'", union))


def test_episode_plays_the_motion_plan():
    ep = _read("Episode.tsx")
    for needle in ("VariantCtx", "TitleVariantCtx", "hookVariant", "backdrop", "titleVariant",
                   "EmphasisLayer", "FilmLook"):
        assert needle in ep, needle
    assert "linearTiming" not in ep          # kecid de motion tokenleri ile (xetti yox)


def test_analytics_scene_uses_the_episode_backdrop():
    assert "backdrop" in _read("visuals", "AnalyticsScene.tsx")


def test_film_look_only_for_the_editorial_theme():
    ep = _read("Episode.tsx")
    assert re.search(r"theme\s*===\s*'editorial'", ep)


def test_caption_words_mark_spoken_figures():
    words = [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3}
             for i, w in enumerate([" Rosa", " charges", " $55", " for", " forty", " percent", " of", " 2,000"])]
    cw = rb.compact_words(words)
    marked = [w["w"] for w in cw if w.get("num")]
    assert marked == ["$55", "forty", "percent", "2,000"]
    assert not any(w.get("num") for w in cw if w["w"] in ("Rosa", "charges", "for", "of"))


def test_captions_keep_figures_in_accent_colour():
    cap = _read("Captions.tsx")
    assert re.search(r"active\s*\|\|\s*w\.num", cap)
