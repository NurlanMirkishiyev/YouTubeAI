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


def test_line_and_timeseries_draw_a_live_head_and_counter_pops():
    """#134 (istifadeci 2026-10-10, reference video_yarat_v4 Chart/counter_events): xett cekilerken ucunda parlayan
    noqte + hereket eden canli deyer; sayqac sayilarken back-overshoot ile boyuyur; VisualProbe QA kompozisiyasi."""
    common = open(os.path.join(SRC, "visuals", "common.tsx"), encoding="utf-8").read()
    charts = open(os.path.join(SRC, "visuals", "Charts.tsx"), encoding="utf-8").read()
    dataviz = open(os.path.join(SRC, "visuals", "DataViz.tsx"), encoding="utf-8").read()
    root = open(os.path.join(SRC, "Root.tsx"), encoding="utf-8").read()
    assert "export const LiveHead" in common
    assert "<LiveHead" in charts and "<LiveHead" in dataviz
    assert "EASE.back(ease(frame, d, DUR.count))" in charts
    assert 'id="VisualProbe"' in root


def test_charts_play_as_a_story_synced_with_the_narration():
    """#137 (istifadeci 2026-10-10, reference video_yarat_v4 Chart.progress): xett noqteden noqteye danisiq boyu
    ARASIKESILMEDEN gedir - seqment i oz reqemi deyilende baslayir, novbeti reqem deyilende catir (storyT);
    son noqteye catanda boyuk "landing" reqemi; xeritede say acarlar arasinda danisiq boyu artir. Bayqus deyismir."""
    common = open(os.path.join(SRC, "visuals", "common.tsx"), encoding="utf-8").read()
    charts = open(os.path.join(SRC, "visuals", "Charts.tsx"), encoding="utf-8").read()
    dataviz = open(os.path.join(SRC, "visuals", "DataViz.tsx"), encoding="utf-8").read()
    assert "export const storyT" in common and "export const Landing" in common
    for src in (charts, dataviz):
        assert "storyT(frame, reveal," in src and "<Landing" in src
        assert "at(reveal, i + 1) - DUR.draw" not in src and "at(reveal, s.to) - DUR.draw" not in src
    assert "storyT(frame, reveal, i)" in dataviz.split("export const USMap")[1]
