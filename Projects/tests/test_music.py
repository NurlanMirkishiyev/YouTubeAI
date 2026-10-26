import music


def test_clip_count_covers_the_video_but_is_capped():
    assert music.clips_needed(30) == 1
    assert music.clips_needed(100) == 3
    assert music.clips_needed(3600) == 8
    assert len(music.STYLES) >= 3 and all("instrumental" in s for s in music.STYLES)


def test_device_falls_back_to_cpu_without_cuda():
    assert music.pick_device(True) == ("cuda", "float16")
    assert music.pick_device(False) == ("cpu", "float32")


def test_styles_are_calm_and_unobtrusive():
    assert len(music.STYLES) >= 10 and len(set(music.STYLES)) == len(music.STYLES)
    for s in music.STYLES:
        low = s.lower()
        assert any(w in low for w in ("calm", "soft", "gentle", "mellow", "ambient", "relaxed"))
        assert not any(w in low for w in ("energetic", "punchy", "driving", "big", "upbeat", "130 bpm"))
    for w in ("vocals", "loud", "aggressive", "heavy drums", "sad", "dark"):
        assert w in music.NEGATIVE


def test_each_new_video_gets_a_style_no_other_video_used(tmp_path):
    hist = str(tmp_path / "music_history.json")
    got = [music.pick_style(f"video-{i}", hist) for i in range(len(music.STYLES))]
    assert sorted(got) == sorted(music.STYLES)            # butun stiller bitene qeder tekrar yoxdur


def test_resume_keeps_the_same_style_for_the_same_video(tmp_path):
    hist = str(tmp_path / "music_history.json")
    first = music.pick_style("a", hist)
    music.pick_style("b", hist)
    assert music.pick_style("a", hist) == first


def test_after_all_styles_are_used_the_least_recent_is_reused(tmp_path):
    hist = str(tmp_path / "music_history.json")
    order = [music.pick_style(f"v{i}", hist) for i in range(len(music.STYLES))]
    assert music.pick_style("new", hist) == order[0]
