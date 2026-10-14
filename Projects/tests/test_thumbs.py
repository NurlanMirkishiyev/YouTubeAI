import io
import json
import os

import pytest
from PIL import Image

import generate
import thumbs

OWL = os.path.join(thumbs.ROOT, "Character", "ELI5_Owl", "sprites_hd", "front.png")


def _png(size=(1536, 1024), color="blue"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _magenta_owl(prompt, ref):
    im = Image.new("RGB", (400, 600), (255, 0, 255))
    im.paste(Image.open(OWL).convert("RGBA").resize((300, 500)), (50, 50), Image.open(OWL).convert("RGBA").resize((300, 500)))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.parametrize("style", thumbs.STYLES)
def test_every_style_composes_a_1280x720_rgb_image(style):
    bg = Image.new("RGB", (1536, 1024), "green")
    owl = Image.open(OWL).convert("RGBA")
    img = thumbs.compose(style, bg, owl, "WHY PAY MORE?")
    assert img.size == (1280, 720) and img.mode == "RGB"


def test_styles_look_different():
    bg = Image.new("RGB", (1536, 1024), "green")
    owl = Image.open(OWL).convert("RGBA")
    imgs = [thumbs.compose(s, bg, owl, "WHY PAY MORE?").tobytes() for s in thumbs.STYLES]
    assert len(set(imgs)) == len(thumbs.STYLES)


def test_chosen_style_defaults_and_persists(tmp_path):
    cfg = str(tmp_path / "thumbnail.json")
    assert thumbs.chosen_style(cfg) == thumbs.STYLES[0]
    thumbs.save_style("spotlight", cfg)
    assert thumbs.chosen_style(cfg) == "spotlight"
    assert json.load(open(cfg))["style"] == "spotlight"


def test_unknown_style_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        thumbs.save_style("nope", str(tmp_path / "t.json"))


def test_hook_text_prefers_the_script_thumbnail_words():
    data = {"title": "Why Expensive Brands Win", "thumbnail_text": "Why pay more?"}
    assert thumbs.hook_text(data, chat=lambda *a, **k: pytest.fail("GPT lazim deyil")) == "WHY PAY MORE?"


def test_hook_text_from_gpt_must_be_an_exact_title_fragment():
    data = {"title": "How Free Apps Make Billions Without Charging You"}
    answers = [{"text": "Apps Steal Your Data"}, {"text": "make billions"}]
    assert thumbs.hook_text(data, chat=lambda *a, **k: answers.pop(0)) == "MAKE BILLIONS"


def test_hook_text_falls_back_to_title_when_gpt_never_quotes_it():
    data = {"title": "Free Apps"}
    assert thumbs.hook_text(data, chat=lambda *a, **k: {"text": "Invented words"}) == "FREE APPS"


def test_background_prompt_uses_thumbnail_idea_without_owl_and_with_style_mood():
    data = {"title": "T", "thumbnail_idea": "Two handbags. The owl looks surprised.",
            "scenes": [{"type": "photo", "photo_prompt": "a phone"}]}
    p = thumbs.bg_prompt(data, "spotlight")
    assert "handbags" in p and "owl looks" not in p.lower() and thumbs.BG_MOOD["spotlight"] in p


def test_background_prompt_without_idea_uses_first_photo_prompt():
    data = {"title": "T", "scenes": [{"type": "anim"}, {"type": "photo", "photo_prompt": "a phone on a desk"}]}
    assert "a phone on a desk" in thumbs.bg_prompt(data, "bold")


def _ep(tmp_path):
    ep = tmp_path / "ep"
    (ep / "owl").mkdir(parents=True)
    data = {"title": "How Free Apps Make Billions", "slug": "s", "thumbnail_text": "WHO PAYS?",
            "scenes": [{"n": 1, "type": "photo", "photo_prompt": "a phone on a desk"}]}
    return str(ep), data


def test_make_draws_a_dedicated_thumbnail_owl_once_and_reuses_it(tmp_path):
    ep, data = _ep(tmp_path)
    calls = []

    def edit(p, r):
        calls.append(p)
        return _magenta_owl(p, r)
    thumbs.make(ep, data, gen=lambda p: _png(), edit=edit, rewrite=None, style="bold")
    thumbs.make(ep, data, gen=lambda p: _png(), edit=edit, rewrite=None, style="split")
    assert len(calls) == 1 and os.path.isfile(os.path.join(ep, "owl", "thumb.png"))


def test_make_stops_when_the_thumbnail_owl_cannot_be_drawn(tmp_path):
    ep, data = _ep(tmp_path)

    def edit(p, r):
        raise RuntimeError("down")
    with pytest.raises(generate.GenerationFailed):
        thumbs.make(ep, data, gen=lambda p: _png(), edit=edit, rewrite=None, style="bold")


def test_pipeline_thumbnail_uses_the_saved_style(tmp_path, monkeypatch):
    import publish
    ep, data = _ep(tmp_path)
    used = []
    monkeypatch.setattr(thumbs, "chosen_style", lambda *a: "bold")
    monkeypatch.setattr(thumbs, "compose", lambda style, *a: used.append(style) or Image.new("RGB", (1280, 720)))
    publish.thumbnail(ep, data, gen=lambda p: _png(), rewrite=None, edit=_magenta_owl)
    assert used == ["bold"]


def test_saved_choice_is_bold():
    assert thumbs.chosen_style() == "bold"


def test_hook_text_survives_a_gpt_error_with_the_title():
    def boom(*a, **k):
        raise RuntimeError("network")
    assert thumbs.hook_text({"title": "Free Apps"}, chat=boom) == "FREE APPS"


def test_hook_text_still_stops_on_an_empty_balance():
    import llm

    def broke(*a, **k):
        raise llm.LLMError("OpenAI balansi bitib: quota")
    with pytest.raises(llm.LLMError):
        thumbs.hook_text({"title": "Free Apps"}, chat=broke)
