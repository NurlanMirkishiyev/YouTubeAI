"""Giris/cixis kartinda bayqus (istifadeci 2026-09-30): "yene titreyir - sabit dayansin; her movzuya uygun
yaradilmis, acilis ve qapanis oldugunu gosteren bayqus sekilleri ile evez et"."""
import os
import re

import remotion_build as rb
import render_owls as ro
from tests.test_remotion_build import DATA, POSES
from tests.test_render_owls import _png

CARDS_TSX = os.path.join(os.path.dirname(rb.__file__), "..", "Remotion", "src", "Cards.tsx")


def _card_owl_source() -> str:
    with open(CARDS_TSX, encoding="utf-8") as f:
        src = f.read()
    return src[src.index("const CardOwl"):src.index("const Words")]


def test_card_owl_does_not_move():
    """Kok sebeb: CardOwl-da 7 px sinus 'bob' + spring ile asagidan ucub gelme."""
    src = _card_owl_source()
    assert "Math.sin" not in src
    assert "spring(" not in src
    assert not re.search(r"translate[XY]?\(", src)


def test_card_actions_are_topic_specific_opening_and_closing():
    a = ro.card_actions("What Is Cash Flow?", "a leather wallet with a few banknotes")
    assert set(a) == {"intro", "outro"}
    assert all("What Is Cash Flow?" in v and "a leather wallet with a few banknotes" in v for v in a.values())
    assert "welcom" in a["intro"].lower() or "hello" in a["intro"].lower()
    assert "goodbye" in a["outro"].lower() or "farewell" in a["outro"].lower()
    assert a["intro"] != a["outro"]


def test_card_owls_are_drawn_judged_and_fall_back_when_hopeless(tmp_path):
    prompts = []

    def gen(prompt):
        prompts.append(prompt)
        return _png()

    def judge(path, name):
        return ro.Verdict(name == "intro", () if name == "intro" else ("identity",))

    report = ro.run_cards(str(tmp_path), "Break-Even Point", gen, judge, prop="a balance scale")
    assert (tmp_path / "owl" / "intro.png").is_file()
    assert not (tmp_path / "owl" / "outro.png").exists()          # pis -> kohne sprite
    assert report["intro"]["ok"] is True and report["outro"]["ok"] is False
    assert report["outro"]["attempts"] == ro.MAX_ATTEMPTS
    assert all("Break-Even Point" in p and "same" in p.lower() for p in prompts)


def test_props_use_topic_card_owls_when_present():
    p = rb.episode_props(DATA, "T", [], POSES, card_owls={"intro": (800, 1200), "outro": (900, 1300)})
    assert p["introOwl"] == "intro" and p["outroOwl"] == "outro"
    assert p["poses"]["intro"] == {"name": "intro", "w": 800, "h": 1200, "height": rb.DEFAULT_HEIGHT,
                                   "flippable": False}


def test_props_fall_back_to_sprites_without_card_owls():
    p = rb.episode_props(DATA, "T", [], POSES)
    assert p["introOwl"] == "front" and p["outroOwl"] == "three_q"


def test_card_owl_sizes_read_from_episode(tmp_path):
    (tmp_path / "owl").mkdir()
    (tmp_path / "owl" / "intro.png").write_bytes(_png(40, 60))
    assert rb.card_owl_sizes(str(tmp_path)) == {"intro": (40, 60)}


def test_episode_passes_card_owl_names_to_cards():
    with open(os.path.join(os.path.dirname(CARDS_TSX), "Episode.tsx"), encoding="utf-8") as f:
        src = f.read()
    assert "p.introOwl" in src and "p.outroOwl" in src


def test_model_rejecting_transparency_stops_the_stage_instead_of_silent_sprites(tmp_path):
    """Real hal 2026-09-30: gpt-image-2 'Transparent background is not supported for this model' -
    butun bayquslar sessizce kohne sprite-a dusurdu."""
    import pytest

    def gen(prompt):
        raise ro.LLMError('HTTP 400: {"message": "Transparent background is not supported for this model."}')

    with pytest.raises(ro.LLMError):
        ro.run_cards(str(tmp_path), "T", gen, lambda p, n: ro.Verdict(True, ()), prop="a wallet")


def test_owl_model_supports_transparent_background():
    assert ro.MODEL != "gpt-image-2"


def _ctx(tmp_path):
    import stages
    return stages.Ctx(topic="t", slug="s", ep_dir=str(tmp_path), words=1230, music=None,
                      min_seconds=480, max_seconds=600, provider="openai")


def test_owl_stage_fails_when_most_scene_owls_fell_back_or_cards_missing(tmp_path):
    import json

    import stages
    ok = {"ok": True}
    bad = {"ok": False}
    (tmp_path / "owl_qa.json").write_text(json.dumps({"scenes": {"1": ok, "2": ok, "3": ok, "4": ok, "5": ok},
                                                      "cards": {"intro": ok, "outro": ok}}))
    assert stages.verify_owls(_ctx(tmp_path)) == []
    (tmp_path / "owl_qa.json").write_text(json.dumps({"scenes": {"1": ok, "2": bad, "3": bad},
                                                      "cards": {"intro": ok, "outro": ok}}))
    assert stages.verify_owls(_ctx(tmp_path))
    (tmp_path / "owl_qa.json").write_text(json.dumps({"scenes": {"1": ok}}))
    assert any("kart" in p for p in stages.verify_owls(_ctx(tmp_path)))


def test_topic_prop_is_one_concrete_object_without_screens_or_writing():
    """Real hal: 'represents the topic' -> planset uzerinde sari cizgi fiquru (cash flow)."""
    asked = []

    def chat(system, user, **kw):
        asked.append(system + user)
        return {"prop": "a leather wallet with a few banknotes"}

    assert ro.choose_prop("What Is Cash Flow?", chat) == "a leather wallet with a few banknotes"
    rules = asked[0].lower()
    assert "no screens" in rules and "no writing" in rules


def test_topic_prop_falls_back_when_llm_fails():
    def chat(system, user, **kw):
        raise ro.LLMError("down")

    assert ro.choose_prop("T", chat) == ro.DEFAULT_PROP


def test_judge_rejects_other_characters_on_clothes_or_props():
    assert "printed" in ro.SYSTEM.lower()


def test_wide_card_owl_is_scaled_down_so_it_never_covers_the_title():
    """Qolunu acan giris bayqusu enli olur; basliq (maxWidth 1080, sol 170) ~1300 px-e qeder gedir."""
    src = _card_owl_source()
    m = re.search(r"MAX_OWL_W = (\d+)", open(CARDS_TSX, encoding="utf-8").read())
    assert m and 1920 - 150 - int(m.group(1)) >= 1300
    assert "MAX_OWL_W" in src
