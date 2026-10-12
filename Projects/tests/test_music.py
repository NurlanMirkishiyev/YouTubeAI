import music


def test_clip_count_covers_the_video_but_is_capped():
    assert music.clips_needed(30) == 1
    assert music.clips_needed(100) == 3
    assert music.clips_needed(3600) == 8
    assert len(music.STYLES) >= 3 and all("instrumental" in s for s in music.STYLES)
