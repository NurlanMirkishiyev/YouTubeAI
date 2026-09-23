import motion


def test_motion_cycle():
    assert [motion.motion_for(i) for i in range(5)] == [
        "zoom_in", "pan_lr", "zoom_out", "pan_rl", "zoom_in"]


def test_kenburns_filter_shape():
    f = motion.kenburns(3, 6.0, "pan_lr", "b3")
    assert f.startswith("[3:v]scale=5120:2880")
    assert "crop=5120:2880" in f
    assert "d=1" in f and "s=1920x1080" in f and "fps=30" in f
    assert "vignette" in f
    assert f.endswith("[b3]")


def test_kenburns_uses_easing_and_frames():
    f = motion.kenburns(0, 6.0, "zoom_in", "b0")
    assert "on/179" in f          # 6 s * 30 fps = 180 kadr -> 0..179
    assert "3-2*" in f            # smoothstep


def test_transitions_fade_on_section_change():
    secs = ["a", "a", "b", "b", "b"]
    assert motion.transitions_for(secs) == ["fade", "fade", "wipeleft", "dissolve"]


def test_transitions_single_clip():
    assert motion.transitions_for(["a"]) == []
