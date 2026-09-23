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
