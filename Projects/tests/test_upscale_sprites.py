from PIL import Image, ImageDraw

import upscale_sprites as us


def _square_alpha() -> Image.Image:
    a = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(a).rectangle((4, 4, 15, 15), fill=255)
    return a


def test_finish_alpha_erodes_edge_keeps_core():
    out = us.finish_alpha(_square_alpha(), (20, 20), 1)
    assert out.getpixel((4, 10)) < 128        # evvelki kenar (halo) yeyildi
    assert out.getpixel((10, 10)) >= 250      # merkez qalir


def test_finish_alpha_resizes():
    assert us.finish_alpha(_square_alpha(), (80, 80), 3).size == (80, 80)


def test_compose_rgba():
    rgb = Image.new("RGB", (20, 20), "white")
    out = us.compose_rgba(rgb, _square_alpha())
    assert out.mode == "RGBA" and out.getpixel((0, 0))[3] == 0 and out.getpixel((10, 10))[3] == 255


def test_is_cut_at_bottom_bust_vs_feet():
    bust = Image.new("L", (100, 100), 0)
    ImageDraw.Draw(bust).rectangle((0, 0, 99, 96), fill=255)          # genis govde, alt 3 setir bos
    feet = Image.new("L", (100, 100), 0)
    d = ImageDraw.Draw(feet)
    d.rectangle((10, 0, 89, 80), fill=255)
    d.rectangle((20, 80, 35, 96), fill=255)                           # iki ayaq
    d.rectangle((65, 80, 80, 96), fill=255)
    assert us.is_cut_at_bottom(bust)
    assert not us.is_cut_at_bottom(feet)


def test_is_cut_at_bottom_real_sprites():
    import os
    src = r"C:\YouTubeAI\Character\ELI5_Owl\sprites"
    got = {n: us.is_cut_at_bottom(Image.open(os.path.join(src, f"{n}.png")).getchannel("A"))
           for n in ("confident", "thinking", "happy", "front", "chart", "box", "side", "three_q")}
    assert {n for n, b in got.items() if b} == {"confident", "thinking", "happy"}


def test_make_shadow_soft_and_faint():
    sh = us.make_shadow(800)
    assert sh.mode == "RGBA" and sh.width == 800
    alpha = sh.getchannel("A")
    cx, cy = sh.width // 2, sh.height // 2
    assert alpha.getpixel((cx, cy)) > alpha.getpixel((cx, 2))
    assert max(alpha.getdata()) <= round(255 * us.SHADOW_OPACITY) + 1
