from PIL import Image

import cards


def _bg(tmp_path):
    p = tmp_path / "bg.png"
    Image.new("RGB", (1344, 768), (40, 90, 160)).save(p)
    return str(p)


def _sprite(tmp_path):
    p = tmp_path / "owl.png"
    Image.new("RGBA", (400, 600), (200, 150, 90, 255)).save(p)
    return str(p)


def test_wrap_splits_long_text():
    font = cards.load_font("ExtraBold", 96)
    lines = cards.wrap("Trademark vs Copyright vs Patent explained simply", font, 900)
    assert len(lines) >= 2 and all(font.getlength(ln) <= 900 for ln in lines if " " in ln)


def test_intro_card(tmp_path):
    out = cards.intro_card("Trademark vs Copyright", _bg(tmp_path), _sprite(tmp_path), str(tmp_path / "i.png"))
    assert Image.open(out).size == (1920, 1080)


def test_outro_card(tmp_path):
    out = cards.outro_card(_bg(tmp_path), _sprite(tmp_path), str(tmp_path / "o.png"))
    assert Image.open(out).size == (1920, 1080)


def test_lower_third_is_transparent_except_panel(tmp_path):
    img = Image.open(cards.lower_third("Why Brands Matter", str(tmp_path / "lt.png")))
    assert img.mode == "RGBA" and img.size == (1920, 1080)
    assert img.getpixel((960, 540))[3] == 0
    assert img.getpixel((90, 100))[3] > 0


def test_thumbnail_size(tmp_path):
    out = cards.thumbnail(_bg(tmp_path), _sprite(tmp_path), "Protect Your Idea", str(tmp_path / "t.png"))
    assert Image.open(out).size == (1280, 720)


def test_load_font_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "FONTS_DIR", str(tmp_path))
    assert cards.load_font("SemiBold", 30).size == 30


def _bust_sprite(tmp_path, cut: str) -> str:
    """Duz kesik tereli (cut) bust: ellips + kesik terefde duz dolu sutun."""
    from PIL import ImageDraw
    im = Image.new("RGBA", (200, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 180, 300), fill=(200, 100, 50, 255))
    if cut == "left":
        d.rectangle((0, 60, 99, 299), fill=(200, 100, 50, 255))
    else:
        d.rectangle((100, 60, 199, 299), fill=(200, 100, 50, 255))
    p = tmp_path / "happy.png"          # _shadow.png yoxdur -> bust
    im.save(p)
    return str(p)


def test_paste_sprite_bust_is_flush_right_with_cut_side_outward(tmp_path):
    from imaging import cut_side
    canvas = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    cards.paste_sprite(canvas, _bust_sprite(tmp_path, "left"), 300, 40, 30)
    box = canvas.getchannel("A").getbbox()
    assert box[2] == 800 and box[3] == 600          # sag ve alt kenara yapisib
    assert cut_side(canvas) == "right"              # kesik taraf ekran kenarina baxir
