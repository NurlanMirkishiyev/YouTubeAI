"""Bayqus gpt-image-2 ile qalir (istifadeci 2026-09-30). Model seffaf fon vermir -> bircins magenta fonda
cekilir, fon lokal silinir (chroma key). Magenta: movzu esyalari (pul, kitab) tez-tez yasil olur."""
import io

import pytest
from PIL import Image

import render_owls as ro

K = (251, 5, 247)
NAVY = (30, 50, 100)


def _canvas(size=(60, 80)) -> Image.Image:
    im = Image.new("RGB", size, K)
    im.paste(NAVY, (20, 20, 40, 60))
    return im


def test_background_becomes_transparent_and_owl_stays_opaque():
    out = ro.key_out(_canvas())
    assert out.mode == "RGBA"
    assert out.getpixel((2, 2))[3] == 0
    assert out.getpixel((30, 40)) == (*NAVY, 255)


def test_edge_pixels_are_unmixed_without_magenta_fringe():
    im = _canvas()
    half = tuple((a + b) // 2 for a, b in zip(K, NAVY))
    im.putpixel((19, 40), half)                      # antialias kenari: 50% fon + 50% bayqus
    r, g, b, a = ro.key_out(im).getpixel((19, 40))
    assert 90 <= a <= 165
    assert abs(r - NAVY[0]) < 25 and abs(g - NAVY[1]) < 25 and abs(b - NAVY[2]) < 25


def test_magenta_seen_through_glass_inside_the_owl_is_removed_too():
    im = _canvas()
    im.paste(K, (27, 30, 33, 36))                    # sekil daxilinde, kenara toxunmayan fon
    assert ro.key_out(im).getpixel((30, 33))[3] == 0


def test_non_uniform_background_is_rejected():
    im = _canvas()
    for x in range(im.width):
        for y in range(10):
            im.putpixel((x, y), (200, 200, 200) if x % 2 else K)
    with pytest.raises(ValueError):
        ro.key_out(im)


def test_drawn_owl_is_keyed_before_saving(tmp_path):
    buf = io.BytesIO()
    _canvas().save(buf, "PNG")
    (tmp_path / "owl").mkdir()
    assert ro._draw(str(tmp_path), 1, "waving", lambda p: buf.getvalue())
    with Image.open(tmp_path / "owl" / "sc01.png") as im:
        assert im.mode == "RGBA" and im.getpixel((0, 0))[3] == 0


def test_unkeyable_drawing_counts_as_not_drawn(tmp_path):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (120, 120, 120)).save(buf, "PNG")
    (tmp_path / "owl").mkdir()
    assert ro._draw(str(tmp_path), 1, "waving", lambda p: buf.getvalue()) is False


def test_owl_uses_gpt_image_2_on_a_solid_magenta_background():
    assert ro.MODEL == "gpt-image-2"
    assert ro.BACKGROUND == "opaque"
    assert "magenta" in ro.build_owl_prompt("x").lower()
    assert "transparent" not in ro.build_owl_prompt("x").lower()
