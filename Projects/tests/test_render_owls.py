import io
import os

from PIL import Image

import render_owls as ro


def _png(w=40, h=60, box=(10, 5, 30, 55)) -> bytes:
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.paste((120, 80, 40, 255), box)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def test_trim_alpha_cuts_transparent_margins():
    with Image.open(io.BytesIO(_png(100, 100, (30, 20, 50, 70)))) as im:
        out = ro.trim_alpha(im)
    assert out.size == (20 + 2 * ro.PAD, 50 + 2 * ro.PAD)


def test_prompt_keeps_the_character_and_adds_the_scene_action():
    p = ro.build_owl_prompt("holding a big stopwatch, surprised")
    assert "holding a big stopwatch, surprised" in p
    assert "same" in p.lower() and "magenta" in p.lower()


def test_verdict_needs_explicit_problems():
    assert ro.parse_owl_verdict({"different_character": False, "cropped": False}).ok
    v = ro.parse_owl_verdict({"different_character": True, "writing": True})
    assert not v.ok and v.problems == ("identity", "text")


def _scenes():
    return [{"owl_action": "waving hello, happy"}, {"owl_action": ""}, {"owl_action": "reading a map, curious"}]


def test_bad_owls_are_redrawn_and_hopeless_ones_fall_back_to_the_pose(tmp_path):
    calls = []

    def gen(prompt: str) -> bytes:
        calls.append(prompt)
        return _png()

    seen = {}

    def judge(path: str, n: int) -> ro.Verdict:
        seen[n] = seen.get(n, 0) + 1
        if n == 1:          # 2-ci cehdde duzelir
            return ro.Verdict(seen[n] >= 2, () if seen[n] >= 2 else ("identity",))
        return ro.Verdict(False, ("cropped",))     # sc03 hec vaxt duzelmir

    report = ro.run(str(tmp_path), _scenes(), gen, judge)
    owl = tmp_path / "owl"
    assert (owl / "sc01.png").is_file()
    assert not (owl / "sc02.png").exists()          # hereket yoxdur -> kohne poz, sekil cekilmir
    assert not (owl / "sc03.png").exists()          # 3 cehdden sonra da pis -> kohne poz
    assert report["1"] == {"ok": True, "problems": [], "attempts": 2, "action": "waving hello, happy"}
    assert report["3"]["ok"] is False and report["3"]["attempts"] == ro.MAX_ATTEMPTS
    assert "2" not in report
    assert len(calls) == 2 + ro.MAX_ATTEMPTS


def test_failed_generation_does_not_stop_the_episode(tmp_path):
    def gen(prompt: str) -> bytes:
        raise ro.LLMError("moderation")

    report = ro.run(str(tmp_path), _scenes()[:1], gen, lambda p, n: ro.Verdict(True, ()))
    assert report["1"]["ok"] is False and not os.path.exists(tmp_path / "owl" / "sc01.png")
