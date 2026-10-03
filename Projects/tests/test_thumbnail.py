"""Reyestr #47 (istifadeci 2026-10-03): thumbnail daha keyfiyyetli olsun. Evvel fon sehne fotolarinin
"en kontrastlisi" idi (why-9-99: qiymet movzusunda qehve qovurma masini), yazi tek rengli, bayqus umumi sprite."""
from PIL import Image

import cards
import thumbnail as th


def _bg(tmp_path, color=(40, 90, 160)):
    p = tmp_path / "bg.png"
    Image.new("RGB", (1536, 864), color).save(p)
    return str(p)


def _owl(tmp_path):
    p = tmp_path / "owl.png"
    Image.new("RGBA", (400, 600), (200, 150, 90, 255)).save(p)
    return str(p)


def _accent_pixels(img, box):
    reg = img.crop(box).convert("RGB")
    b = reg.tobytes()
    return sum(1 for i in range(0, len(b), 3) if b[i] > 230 and 170 < b[i + 1] < 220 and b[i + 2] < 60)


def test_highlight_word_is_drawn_in_accent_colour(tmp_path):
    out = cards.thumbnail(_bg(tmp_path), _owl(tmp_path), "Why Prices Trick Us", str(tmp_path / "t.png"),
                          highlight="Trick")
    img = Image.open(out)
    assert img.size == (1280, 720)
    assert _accent_pixels(img, (0, 0, 760, 720)) > 2000
    plain = Image.open(cards.thumbnail(_bg(tmp_path), _owl(tmp_path), "Why Prices Trick Us",
                                       str(tmp_path / "p.png"), highlight=""))
    assert _accent_pixels(plain, (60, 150, 760, 600)) < _accent_pixels(img, (60, 150, 760, 600))


def test_text_side_is_darkened_for_contrast(tmp_path):
    img = Image.open(cards.thumbnail(_bg(tmp_path, (200, 200, 200)), _owl(tmp_path), "Hi",
                                     str(tmp_path / "t.png"))).convert("RGB")
    assert sum(img.getpixel((20, 700))) < sum(img.getpixel((900, 100)))


def test_fit_title_shrinks_long_text_to_three_lines():
    size, lines = cards.fit_title("The Hidden Psychology Behind Every Price You See", 700, max_lines=3)
    font = cards.load_font("ExtraBold", size)
    assert len(lines) <= 3 and all(font.getlength(ln) <= 700 for ln in lines)
    assert cards.fit_title("Cash Flow", 700)[0] > size


def test_prompt_is_clean_and_leaves_space_for_text():
    p = th.thumb_prompt("a price tag of $9.99 on a shirt, a shopper's hand, a glowing supermarket aisle")
    assert "$" not in p and "hand" not in p.lower() and "9.99" not in p
    assert "left third" in p and "no text" in p.lower()


def test_pick_best_prefers_clean_highest_score():
    verdicts = {"a.png": {"writing": False, "people": False, "score": 6},
                "b.png": {"writing": True, "people": False, "score": 9},
                "c.png": {"writing": False, "people": False, "score": 8}}
    assert th.pick_best(verdicts) == "c.png"
    assert th.pick_best({"b.png": {"writing": True, "score": 9}}) is None
    assert th.pick_best({"x.png": None}) is None


def test_make_background_falls_back_when_generation_fails(tmp_path):
    from llm import LLMError

    def broken(prompt):
        raise LLMError("quota")

    assert th.make_background("a concept", str(tmp_path), generate=broken, judge=lambda p: {}) is None


def test_make_background_returns_judged_best(tmp_path):
    import io
    calls = []

    def gen(prompt):
        calls.append(prompt)
        buf = io.BytesIO()
        Image.new("RGB", (1536, 1024), (len(calls) * 40, 0, 0)).save(buf, "PNG")
        return buf.getvalue()

    def judge(path):
        return {"writing": False, "people": False, "score": 5 if path.endswith("1.png") else 9}

    best = th.make_background("an espresso machine", str(tmp_path), generate=gen, judge=judge)
    assert best.endswith("thumb_bg_2.png") and len(calls) == th.VARIANTS
    assert Image.open(best).size == (1536, 864)


# --- publish_pack inteqrasiyasi ------------------------------------------------------------------

def _episode(tmp_path, with_owl=True):
    ep = tmp_path / "ep"
    (ep / "bg").mkdir(parents=True)
    Image.new("RGB", (1536, 864), (10, 10, 10)).save(ep / "bg" / "sc01.png")
    if with_owl:
        (ep / "owl").mkdir()
        Image.new("RGBA", (300, 500), (255, 0, 0, 255)).save(ep / "owl" / "intro.png")
    return ep


DATA = {"titles": ["Why $9.99 works"], "summary": "s", "tags": ["a"], "hashtags": ["#a"],
        "thumb_text": "Why Prices Trick Us", "thumb_highlight": "Trick", "thumb_scene": "an espresso machine"}


def test_write_pack_uses_generated_background_and_topic_owl(tmp_path, monkeypatch):
    import publish_pack as pp
    ep = _episode(tmp_path)
    seen = {}
    gen_bg = str(tmp_path / "gen.png")
    Image.new("RGB", (1536, 864), (0, 120, 0)).save(gen_bg)
    monkeypatch.setattr(pp.cards, "thumbnail", lambda bg, owl, text, out, highlight="": seen.update(
        bg=bg, owl=owl, text=text, highlight=highlight) or out)
    pp.write_pack(str(ep), "T", DATA, [], make_bg=lambda concept, out_dir: seen.update(concept=concept) or gen_bg)
    assert seen["bg"] == gen_bg and seen["concept"] == "an espresso machine"
    assert seen["owl"].endswith("intro.png") and seen["highlight"] == "Trick"


def test_write_pack_falls_back_to_scene_photo_and_sprite(tmp_path, monkeypatch):
    import publish_pack as pp
    ep = _episode(tmp_path, with_owl=False)
    seen = {}
    monkeypatch.setattr(pp.cards, "thumbnail", lambda bg, owl, text, out, highlight="": seen.update(
        bg=bg, owl=owl) or out)
    pp.write_pack(str(ep), "T", DATA, [], make_bg=lambda concept, out_dir: None)
    assert seen["bg"].endswith("sc01.png") and seen["owl"].endswith("confident.png")
