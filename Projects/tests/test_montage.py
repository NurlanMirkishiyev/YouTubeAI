import pytest
from PIL import Image

import montage as mt


def _sprite(**kw):
    base = dict(path="s.png", shadow="sh.png", pos="right", height=0.42,
                src_w=800, src_h=1200, shadow_w=800, shadow_h=150)
    base.update(kw)
    return mt.Sprite(**base)


def test_sprite_geometry_right():
    s = _sprite()
    assert s.size() == (303, 454)
    assert s.x() == 1920 - 303 - mt.SPRITE_MARGIN_X
    assert s.y() == 1080 - 454 - mt.SPRITE_MARGIN_Y
    assert s.shadow_size() == (303, 57)
    assert s.shadow_y() == s.y() + 454 - round(454 * mt.SHADOW_INSET) - 57 // 2


def test_bust_sprite_sits_on_frame_edges():
    s = _sprite(shadow=None, shadow_w=0, shadow_h=0)
    assert s.y() == 1080 - 454 + mt.BOB_PX      # bob yuxari qalxanda alt kenar gorunmesin
    assert s.x() == 1920 - 303                  # sag kenara yapisir
    assert _sprite(shadow=None, pos="left").x() == 0
    assert s.shadow_size() is None


def test_bust_flipped_so_cut_side_faces_screen_edge(tmp_path):
    im = Image.new("RGBA", (100, 150), (0, 0, 0, 0))
    im.paste((200, 150, 90, 255), (0, 20, 60, 150))      # sol kenar duz kesik
    im.save(tmp_path / "confident.png")
    assert mt.Sprite.parse("confident@left:0.1", str(tmp_path)).flip is False
    assert mt.Sprite.parse("confident@right:0.1", str(tmp_path)).flip is True
    clip = mt.Clip("a.png", 6.0, mt.Sprite.parse("confident@right:0.1", str(tmp_path)), None)
    assert ",hflip," in ";".join(mt.clip_chain(0, clip, {"bg": 0, "sprite": 1}))


def test_sprite_never_upscaled():
    with pytest.raises(SystemExit):
        _sprite(src_h=300, src_w=200).size()


def test_sprite_parse_reads_dims(tmp_path):
    Image.new("RGBA", (800, 1200)).save(tmp_path / "front.png")
    Image.new("RGBA", (800, 150)).save(tmp_path / "front_shadow.png")
    s = mt.Sprite.parse("front@left:0.4", str(tmp_path))
    assert (s.pos, s.height, s.src_w, s.src_h, s.shadow_h) == ("left", 0.4, 800, 1200, 150)
    assert mt.Sprite.parse("-", str(tmp_path)) is None


def test_input_args_table():
    clips = [mt.Clip("a.png", 6.0, _sprite(), "lt.png"), mt.Clip("b.png", 6.0, None, None)]
    args, table = mt.input_args(clips)
    assert table == [{"bg": 0, "shadow": 1, "sprite": 2, "lt": 3}, {"bg": 4}]
    assert args.count("-i") == 5 and "-loop" not in args     # tek kadr, tekrar loop filtri ile


def test_clip_chain_labels():
    clip = mt.Clip("a.png", 6.0, _sprite(), "lt.png")
    chain = ";".join(mt.clip_chain(0, clip, {"bg": 0, "shadow": 1, "sprite": 2, "lt": 3}))
    assert "[1:v]scale=303:-1" in chain and "[2:v]scale=303:454" in chain
    assert "sin(2*PI*t/" in chain and "fade=t=in" in chain
    assert chain.count("loop=loop=") == 4                    # bg, kolge, sprite, lt
    assert chain.endswith("[v0]")


def test_video_graph_transitions_and_total():
    clips = [mt.Clip("a.png", 6.0, None, None), mt.Clip("b.png", 6.0, None, None)]
    _, table = mt.input_args(clips)
    graph, total = mt.video_graph(clips, table, ["slideleft"], None, None)
    assert "xfade=transition=slideleft:duration=0.5:offset=5.500" in graph
    assert total == pytest.approx(11.5)


def test_video_graph_bad_transition_count():
    clips = [mt.Clip("a.png", 6.0, None, None), mt.Clip("b.png", 6.0, None, None)]
    _, table = mt.input_args(clips)
    with pytest.raises(SystemExit):
        mt.video_graph(clips, table, ["fade", "fade"], None, None)


def test_video_graph_subtitles_style():
    clips = [mt.Clip("a.png", 6.0, None, None)]
    _, table = mt.input_args(clips)
    graph, _ = mt.video_graph(clips, table, None, r"C:\x\n.srt", r"C:\f")
    assert "subtitles='C\\:/x/n.srt'" in graph and "fontsdir='C\\:/f'" in graph
    assert "BorderStyle=3" in graph and graph.endswith("[vsub]")
