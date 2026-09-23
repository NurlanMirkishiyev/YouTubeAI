import pytest
from PIL import Image

import build_episode as be

SCENES = [
    {"section": "Hook", "duration": 10, "sprite_token": "three_q@right"},
    {"section": "Section 1: A", "duration": 20, "sprite_token": "front@left"},
    {"section": "Section 1: A", "duration": 30, "sprite_token": "box@left"},
]
CARDS = {"intro": "i.png", "outro": "o.png", "lower_thirds": ["-", "lt2.png", "-"]}


def test_lower_third_titles_skip_hook():
    assert be.lower_third_titles(SCENES) == [None, "A", None]


def test_assemble_with_cards():
    p = be.assemble(SCENES, ["1.png", "2.png", "3.png"], CARDS, 0.5)
    assert p["images"] == ["i.png", "1.png", "2.png", "3.png", "o.png"]
    assert p["durations"] == ["4.500", "10.500", "20.500", "30.500", "6.000"]
    assert p["sprites"] == ["-", "three_q@right", "front@left", "box@left", "-"]
    assert p["lower_thirds"] == ["-", "-", "lt2.png", "-", "-"]
    assert len(p["transitions"]) == 4 and p["transitions"][0] == "fade"
    assert p["delay"] == 4.0


def test_assemble_without_cards():
    p = be.assemble(SCENES, ["1.png", "2.png", "3.png"], None, 0.5)
    assert p["durations"] == ["10.500", "20.500", "30.000"]
    assert p["delay"] == 0.0 and len(p["transitions"]) == 2


def test_scene_image_prefers_hd(tmp_path):
    (tmp_path / "bg_hd").mkdir()
    Image.new("RGB", (3840, 2160)).save(tmp_path / "bg_hd" / "sc01.png")
    assert be.scene_image(str(tmp_path), 1, {}, True).endswith("sc01.png")


def test_scene_image_rejects_small_hd(tmp_path):
    (tmp_path / "bg_hd").mkdir()
    Image.new("RGB", (1344, 768)).save(tmp_path / "bg_hd" / "sc01.png")
    with pytest.raises(SystemExit):
        be.scene_image(str(tmp_path), 1, {}, False)


def test_scene_image_require_hd_missing(tmp_path):
    with pytest.raises(SystemExit):
        be.scene_image(str(tmp_path), 1, {}, True)
