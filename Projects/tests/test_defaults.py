"""Faza 5.1/5.2 (istifadeci 2026-10-07): butun yeni imkanlar BUTUN videolarda default ACIQDIR; heç biri video basina
el ile acilmir. Sondurmek yalniz istifadeci qerari ile - default False olsa ve ya kind KINDS-den cixsa bu test dusur."""
import config
import motion
import remotion_build as rb
import visuals

FLAGS = ("CASE_MODEL", "SFX", "NUMBER_OVERLAY", "TYPEWRITER", "MOTION_VARIANTS", "REAL_DATA")
DATA = {"intro_seconds": 3.5, "outro_seconds": 4.0,
        "scenes": [{"section": "Section 1: A", "duration": 8.0, "sprite": "three_q", "pos": "right",
                    "spoken_title": "A"}]}
POSES = {"three_q": (1020, 1592), "front": (1108, 1604)}


def _words():
    return [{"word": " " + w, "start": 3.6 + 0.4 * k, "end": 3.9 + 0.4 * k}
            for k, w in enumerate("Rosa now charges $55 a plate".split())]


def test_every_feature_flag_is_on_by_default():
    assert all(getattr(config, f) is True for f in FLAGS)


def test_new_visual_kinds_are_offered():
    assert {"timeseries", "usmap", "table", "threshold"} <= set(visuals.KINDS)
    assert set(config.REQUIRED_KINDS) <= set(visuals.KINDS)


def test_number_overlay_flag_drives_the_build(monkeypatch):
    assert rb.episode_props(DATA, "T", _words(), POSES)["scenes"][0]["overlay"]
    monkeypatch.setattr(config, "NUMBER_OVERLAY", False)
    assert rb.episode_props(DATA, "T", _words(), POSES)["scenes"][0]["overlay"] is None


def test_motion_variants_flag_drives_the_plan(monkeypatch, tmp_path):
    h = str(tmp_path / "h.json")
    assert "motion" in rb.episode_props(DATA, "T", _words(), POSES, slug="s", history=h)
    monkeypatch.setattr(config, "MOTION_VARIANTS", False)
    assert "motion" not in rb.episode_props(DATA, "T", _words(), POSES, slug="s", history=h)


def test_typewriter_flag_drives_the_cold_open(monkeypatch):
    scenes = [{"kind": None, "section_start": True}]
    assert motion.plan_motion("s", scenes)["cold_open"] == "typewriter"
    monkeypatch.setattr(config, "TYPEWRITER", False)
    assert motion.plan_motion("s", scenes)["cold_open"] != "typewriter"


def test_sfx_flag_drives_the_master_mix(monkeypatch):
    assert rb.sfx_enabled() is True
    monkeypatch.setattr(config, "SFX", False)
    assert rb.sfx_enabled() is False
