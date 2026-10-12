import io
import os
import shutil

from PIL import Image, ImageDraw, ImageFont

import pytest

import generate
import llm
import publish

DATA = {"title": "How Free Apps Make Billions", "slug": "s", "scenes": [
    {"n": 1, "section": "Hook: Who Pays?", "section_start": True, "text": "Imagine an app.", "duration": 65.0},
    {"n": 2, "section": "Hook: Who Pays?", "section_start": False, "text": "It is free.", "duration": 5.0},
    {"n": 3, "section": "Secret #1: Users", "section_start": True, "text": "Users matter.", "duration": 3.0}]}


def test_chapters_use_section_names_and_times():
    assert publish.chapters(DATA["scenes"], DATA["title"]) == ["0:00 Hook: Who Pays?", "1:10 Secret #1: Users"]


def test_chapters_start_at_zero_with_script_title_when_first_scene_is_unnamed():
    scenes = [dict(DATA["scenes"][0], section="", section_start=False)] + DATA["scenes"][1:]
    assert publish.chapters(scenes, DATA["title"]) == [
        "0:00 How Free Apps Make Billions", "1:10 Secret #1: Users"]


def test_youtube_text_comes_only_from_the_script():
    t = publish.youtube_text(DATA)
    assert t.startswith("How Free Apps Make Billions\n")
    assert "Imagine an app." in t and "1:10 Secret #1: Users" in t
    assert "Tags: how, free, apps, make, billions" in t


def _png_bytes(size=(64, 36)):
    buf = io.BytesIO()
    Image.new("RGB", size, "blue").save(buf, "PNG")
    return buf.getvalue()


def _thumb_ep(tmp_path):
    ep = tmp_path / "ep"
    (ep / "owl").mkdir(parents=True)
    shutil.copyfile(os.path.join(publish.ROOT, "Character", "ELI5_Owl", "sprites_hd", "front.png"),
                    ep / "owl" / "sc01.png")
    data = {"title": "How Free Apps Make Billions", "slug": "s", "scenes": [
        {"n": 1, "type": "photo", "photo_prompt": "a phone on a desk", "section": "Hook", "section_start": True,
         "text": "Imagine an app.", "duration": 65.0}]}
    return str(ep), data


def test_thumbnail_is_1280x720_with_generated_background(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    img = publish.thumbnail(ep, data, gen=lambda p: _png_bytes(), rewrite=None)
    assert img.size == (1280, 720)


def test_thumbnail_failure_stops_and_never_uses_a_scene_photo(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    os.makedirs(os.path.join(ep, "img"))
    with open(os.path.join(ep, "img", "sc01.png"), "wb") as f:
        f.write(_png_bytes())

    def boom(prompt):
        raise RuntimeError("network down")
    with pytest.raises(generate.GenerationFailed):
        publish.thumbnail(ep, data, gen=boom, rewrite=None)


def test_thumbnail_reraises_empty_balance(tmp_path):
    ep, data = _thumb_ep(tmp_path)

    def no_money(prompt):
        raise llm.LLMError("OpenAI balansi bitib: quota")

    with pytest.raises(llm.LLMError, match="balansi bitib"):
        publish.thumbnail(ep, data, gen=no_money, rewrite=None)


def test_thumbnail_without_the_episode_owl_stops_instead_of_using_the_sprite(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    os.remove(os.path.join(ep, "owl", "sc01.png"))
    with pytest.raises(generate.GenerationFailed, match="owl"):
        publish.thumbnail(ep, data, gen=lambda p: _png_bytes(), rewrite=None)


def test_corrupt_background_payload_is_retried(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    payloads = [b"not an image", _png_bytes()]
    img = publish.thumbnail(ep, data, gen=lambda p: payloads.pop(0), rewrite=None)
    assert img.size == (1280, 720) and img.mode == "RGB"


def test_safety_rejected_thumbnail_prompt_is_rewritten(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    seen = []

    def gen(p):
        seen.append(p)
        if "calm" not in p:
            raise llm.LLMError("HTTP 400: moderation_blocked")
        return _png_bytes()
    publish.thumbnail(ep, data, gen=gen, rewrite=lambda p: p + " calm")
    assert len(seen) == 2


def test_long_title_is_shrunk_and_capped_to_four_lines():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    title = "THE HIDDEN MATH BEHIND WHY EVERY FREE APP ON YOUR PHONE STILL MANAGES TO MAKE BILLIONS EVERY SINGLE YEAR"
    size, lines = publish.fit_title(draw, title)
    assert len(lines) <= 4
    assert 60 + len(lines) * (size + 14) <= 690
    assert all(draw.textlength(line, font=ImageFont.truetype(publish.FONT, size)) <= 760 for line in lines)
    assert size >= publish.MIN_TITLE_SIZE


def test_main_copies_outputs_to_out_root(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    with open(os.path.join(ep, "scenes.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(data, f)
    for name in ("s.mp4", "s.srt"):
        with open(os.path.join(ep, name), "wb") as f:
            f.write(b"x")
    out_root = tmp_path / "out"
    publish.main(ep, gen=lambda p: _png_bytes(), out_root=str(out_root), rewrite=None)
    dest = out_root / "s"
    assert sorted(os.listdir(dest)) == ["s.mp4", "s.srt", "thumbnail.png", "youtube.txt"]
    assert os.path.isfile(os.path.join(ep, "published"))


def test_failed_copy_writes_no_published_marker(tmp_path):
    ep, data = _thumb_ep(tmp_path)
    with open(os.path.join(ep, "scenes.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(data, f)
    with pytest.raises(FileNotFoundError):
        publish.main(ep, gen=lambda p: _png_bytes(), out_root=str(tmp_path / "out"), rewrite=None)
    assert not os.path.exists(os.path.join(ep, "published"))


def test_existing_thumbnail_is_reused_on_retry(tmp_path):
    import json
    ep, data = _thumb_ep(tmp_path)
    with open(os.path.join(ep, "scenes.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)
    Image.new("RGB", (1280, 720)).save(os.path.join(ep, "thumbnail.png"))
    for name in ("s.mp4", "s.srt"):
        with open(os.path.join(ep, name), "wb") as f:
            f.write(b"x")

    def never(p):
        raise AssertionError("should not generate")
    publish.main(ep, gen=never, out_root=str(tmp_path / "out"), rewrite=None)
    assert os.path.isfile(os.path.join(ep, "published"))
