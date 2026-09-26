from PIL import Image

import render_bgs as rb
import scene_plan
from llm import LLMError


def test_prompt_has_house_style_scene_and_free_side_for_the_owl():
    p = rb.build_prompt("a robot arm stacking cubes", "right")
    assert p.startswith(rb.STYLE) and "a robot arm stacking cubes" in p
    assert "empty space on the right side" in p and "no text" in p.lower()
    assert "empty space on the left side" in rb.build_prompt("x", "left")


def test_crop_to_16x9_keeps_full_width_and_center():
    im = Image.new("RGB", (1536, 1024))
    im.paste((255, 0, 0), (0, 0, 1536, 80))          # yuxari zolaq kesilmelidir
    out = rb.crop_16x9(im)
    assert out.size == (1536, 864)
    assert out.getpixel((10, 0)) != (255, 0, 0)


def test_render_one_saves_png_and_uses_fallback_when_prompt_is_refused(tmp_path):
    seen = []

    def gen(prompt):
        seen.append(prompt)
        if len(seen) == 1:
            raise LLMError("HTTP 400: moderation_blocked")
        img = Image.new("RGB", (1536, 1024), (0, 128, 0))
        import io
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    dest = tmp_path / "sc01.png"
    rb.render_one({"bg_prompt": "a scary thing", "pos": "right"}, str(dest), gen)
    with Image.open(dest) as im:
        assert im.size == (1536, 864)
    assert "a scary thing" in seen[0] and scene_plan.FALLBACK_BG in seen[1]
