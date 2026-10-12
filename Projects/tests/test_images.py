import io
import json

from PIL import Image

import pytest

import generate
import images
import llm


def _ep(tmp_path, types):
    scenes = [{"n": i + 1, "type": t, "photo_prompt": f"p{i}", "text": "Only 2% of users pay.",
               "keep": "me", "anim": None if t == "photo" else {"kind": "quote", "text": "x", "variant": 0}}
              for i, t in enumerate(types)]
    (tmp_path / "scenes.json").write_text(json.dumps({"title": "T", "slug": "t", "scenes": scenes}))
    return str(tmp_path)


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buf, "PNG")
    return buf.getvalue()


def test_photos_are_rendered_only_for_photo_scenes(tmp_path):
    ep = _ep(tmp_path, ["photo", "anim", "photo"])
    calls = []
    images.render_photos(ep, gen=lambda p: calls.append(p) or _noise(len(calls)), workers=1, limiter=None)
    assert sorted(c[:2] for c in calls) == ["p0", "p2"]
    assert (tmp_path / "img" / "sc01.png").exists() and not (tmp_path / "img" / "sc02.png").exists()


def test_failed_photo_stops_the_stage_and_is_never_replaced(tmp_path):
    ep = _ep(tmp_path, ["photo", "photo"])

    def gen(p):
        if p.startswith("p1"):
            raise RuntimeError("network")
        return _png()
    with pytest.raises(generate.GenerationFailed):
        images.render_photos(ep, gen=gen, workers=1, limiter=None, rewrite=None)
    scenes = json.loads((tmp_path / "scenes.json").read_text())["scenes"]
    assert [s["type"] for s in scenes] == ["photo", "photo"] and scenes[1]["anim"] is None
    assert (tmp_path / "img" / "sc01.png").exists() and not (tmp_path / "img" / "sc02.png").exists()


def test_safety_rejected_photo_is_redrawn_with_a_rewritten_prompt(tmp_path):
    ep = _ep(tmp_path, ["photo"])
    seen = []

    def gen(p):
        seen.append(p)
        if "calm" not in p:
            raise llm.LLMError("HTTP 400: moderation_blocked")
        return _png()
    images.render_photos(ep, gen=gen, workers=1, limiter=None, rewrite=lambda p: p + " calm")
    assert (tmp_path / "img" / "sc01.png").exists() and seen[1].startswith("p0 calm")


def test_empty_openai_balance_is_not_swallowed(tmp_path):
    ep = _ep(tmp_path, ["photo"])

    def broke(p):
        raise llm.LLMError("OpenAI balansi bitib: x")
    with pytest.raises(llm.LLMError):
        images.render_photos(ep, gen=broke, workers=1, limiter=None)
    assert json.loads((tmp_path / "scenes.json").read_text())["scenes"][0]["type"] == "photo"


def test_photo_style_forbids_the_mascot():
    assert "owl" in images.STYLE.lower() and "cartoon" in images.STYLE.lower()


def _noise(seed):
    import numpy as np
    a = (np.random.default_rng(seed).random((48, 64, 3)) * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, "PNG")
    return buf.getvalue()


def test_dhash_separates_different_photos_and_matches_the_same_one():
    a, b = images.dhash(_noise(1)), images.dhash(_noise(2))
    assert bin(a ^ images.dhash(_noise(1))).count("1") == 0
    assert bin(a ^ b).count("1") > images.DUP_BITS


def test_near_duplicate_photo_is_redrawn_with_a_different_composition(tmp_path):
    ep = _ep(tmp_path, ["photo", "photo"])
    seen = []

    def gen(p):
        seen.append(p)
        return _noise(len(seen)) if images.VARY.strip() in p else _noise(0)
    images.render_photos(ep, gen=gen, workers=1, limiter=None, rewrite=None)
    assert any(images.VARY.strip() in p for p in seen)
    h1 = images.dhash((tmp_path / "img" / "sc01.png").read_bytes())
    h2 = images.dhash((tmp_path / "img" / "sc02.png").read_bytes())
    assert bin(h1 ^ h2).count("1") > images.DUP_BITS


def test_duplicate_of_an_existing_episode_photo_is_detected(tmp_path):
    ep = _ep(tmp_path, ["photo", "photo"])
    (tmp_path / "img").mkdir()
    (tmp_path / "img" / "sc01.png").write_bytes(_noise(0))
    seen = []

    def gen(p):
        seen.append(p)
        return _noise(5) if images.VARY.strip() in p else _noise(0)
    images.render_photos(ep, gen=gen, workers=1, limiter=None, rewrite=None)
    assert len(seen) == 2


def test_intro_and_outro_backgrounds_are_drawn(tmp_path):
    ep = _ep(tmp_path, ["intro", "photo", "outro"])
    n = iter(range(100))
    images.render_photos(ep, gen=lambda p: _noise(next(n)), workers=1, limiter=None, rewrite=None)
    assert all((tmp_path / "img" / f"sc{i:02d}.png").exists() for i in (1, 2, 3))
