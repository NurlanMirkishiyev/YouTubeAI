from PIL import Image

import publish_pack as pp

SCENES = [{"section": "Hook", "duration": 10}, {"section": "Hook", "duration": 10},
          {"section": "Section 1: A", "duration": 30}, {"section": "Section 2: B", "duration": 5},
          {"section": "Recap", "duration": 40}, {"section": "Call to Action", "duration": 20}]


def test_fmt_ts():
    assert pp.fmt_ts(0) == "00:00"
    assert pp.fmt_ts(754.2) == "12:34"
    assert pp.fmt_ts(3725) == "1:02:05"


def test_chapters_start_at_zero_and_drop_short():
    assert pp.chapters(SCENES, 4.0, 125.0) == [
        (0.0, "Intro"), (24.0, "A"), (59.0, "Recap"), (99.0, "Call to Action")]


def test_chapters_need_three():
    assert pp.chapters(SCENES[:3], 4.0, 60.0) == []


def test_fit_tags_dedupes_and_limits():
    tags = ["Trademark", "trademark", "a, b"] + ["x" * 100] * 10
    out = pp.fit_tags(tags, limit=120)
    assert out[:2] == ["Trademark", "a b"]
    assert sum(len(t) for t in out) + len(out) - 1 <= 120


def test_pick_title():
    assert pp.pick_title(["x" * 90, "Good Title"]) == "Good Title"
    assert len(pp.pick_title(["word " * 30])) <= 70


def test_description_has_chapters():
    d = pp.description("Sum.", [(0.0, "Hook"), (24.0, "A"), (59.0, "Recap")], ["eli5", "#business"])
    assert "00:00 Hook" in d and "00:24 A" in d and "#eli5 #business" in d


def test_pack_problems(tmp_path):
    (tmp_path / "title.txt").write_text("T", encoding="utf-8")
    (tmp_path / "description.txt").write_text("00:00 Hook", encoding="utf-8")
    (tmp_path / "tags.txt").write_text("a,b", encoding="utf-8")
    Image.new("RGB", (1280, 720)).save(tmp_path / "thumbnail.png")
    assert pp.pack_problems(str(tmp_path)) == []
    Image.new("RGB", (100, 100)).save(tmp_path / "thumbnail.png")
    assert pp.pack_problems(str(tmp_path))


def test_music_credit_for_cc_by_track():
    c = pp.music_credit(r"C:\YouTubeAI\Music\Carefree.mp3", {"Carefree.mp3": "Carefree"})
    assert '"Carefree" Kevin MacLeod (incompetech.com)' in c
    assert "Creative Commons: By Attribution 4.0" in c


def test_music_credit_empty_for_unknown_or_missing_track():
    assert pp.music_credit(None, {"Carefree.mp3": "Carefree"}) == ""
    assert pp.music_credit("own.mp3", {"Carefree.mp3": "Carefree"}) == ""


def test_description_appends_credit():
    d = pp.description("Sum.", [(0.0, "Hook")], ["eli5"], credit="Music: X")
    assert d.rstrip().endswith("Music: X") and "00:00 Hook" in d
