import music


def test_clip_count_covers_the_video_but_is_capped():
    assert music.clips_needed(30) == 1
    assert music.clips_needed(100) == 3
    assert music.clips_needed(3600) == 8
    assert len(music.STYLES) >= 3 and all("instrumental" in s for s in music.STYLES)


def test_device_falls_back_to_cpu_without_cuda():
    assert music.pick_device(True) == ("cuda", "float16")
    assert music.pick_device(False) == ("cpu", "float32")
