import io
import json

import numpy as np
from PIL import Image

import pytest

import generate
import llm
import owl


def _magenta_owl():
    im = Image.new("RGB", (60, 80), (255, 0, 255))
    im.paste((120, 80, 40), (20, 20, 40, 70))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def test_key_out_makes_magenta_transparent_and_keeps_the_owl():
    out = owl.key_out(Image.open(io.BytesIO(_magenta_owl())))
    a = np.asarray(out.getchannel("A"))
    assert a[0, 0] == 0 and a[40, 30] == 255


def test_failed_owl_stops_the_stage_and_no_sprite_is_copied(tmp_path):
    scenes = [{"n": 1, "owl": "waving"}, {"n": 2, "owl": "thinking"}]
    (tmp_path / "scenes.json").write_text(json.dumps({"title": "T", "slug": "t", "scenes": scenes}))

    def edit(prompt, ref):
        if "thinking" in prompt:
            raise RuntimeError("fail")
        return _magenta_owl()
    with pytest.raises(generate.GenerationFailed):
        owl.render_owls(str(tmp_path), edit=edit, workers=1, limiter=None, rewrite=None)
    assert (tmp_path / "owl" / "sc01.png").exists() and not (tmp_path / "owl" / "sc02.png").exists()
    assert "waving" in owl.owl_prompt("waving")


def test_safety_rejected_owl_pose_is_rewritten(tmp_path):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [{"n": 1, "owl": "holding a knife"}]}))

    def edit(prompt, ref):
        if "knife" in prompt:
            raise llm.LLMError("HTTP 400: rejected by the safety system")
        return _magenta_owl()
    owl.render_owls(str(tmp_path), edit=edit, workers=1, limiter=None, rewrite=lambda a: "holding a spoon")
    assert (tmp_path / "owl" / "sc01.png").exists()


def test_empty_openai_balance_stops_the_owl_renderer(tmp_path):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [{"n": 1, "owl": "waving"}]}))

    def broke(prompt, ref):
        raise llm.LLMError("OpenAI balansi bitib: x")
    with pytest.raises(llm.LLMError):
        owl.render_owls(str(tmp_path), edit=broke, workers=1, limiter=None)
    assert not (tmp_path / "owl" / "sc01.png").exists()
