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
    images.render_photos(ep, gen=lambda p: calls.append(p) or _png(), workers=1, limiter=None)
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
