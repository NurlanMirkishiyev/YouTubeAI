import pytest

import mix
import render

DATA = {"title": "T", "slug": "t", "scenes": [
    {"n": 1, "type": "photo", "section": "Intro", "section_start": True, "anim": None, "duration": 2.0},
    {"n": 2, "type": "anim", "section": "Intro", "section_start": False,
     "anim": {"kind": "quote", "text": "Hi", "variant": 0}, "duration": 1.5}]}


def test_props_frames_follow_voice_durations():
    p = render.props(DATA, [{"start": 0.0, "end": 1.0, "text": "Hi"}])
    assert [s["from"] for s in p["scenes"]] == [0, 60] and [s["frames"] for s in p["scenes"]] == [60, 45]
    assert p["total"] == 105 and p["scenes"][0]["img"] == "img/sc01.jpg" and p["scenes"][1]["img"] is None
    assert p["scenes"][1]["owl"] == "owl/sc02.png" and p["captions"][0] == {"from": 0, "to": 30, "text": "Hi"}


def test_mix_measures_first_then_applies_exact_gain_and_limiter():
    m = " ".join(mix.measure_cmd("E", 3.5))
    assert "print_format=json" in m and "-stream_loop -1" in m and "-f null" in m
    c = mix.cmd("E", "t", 3.5, gain_db=2.25)
    j = " ".join(c)
    assert "volume=2.25dB" in j and "alimiter=" in j and "level=0" in j and "loudnorm" not in j
    assert "-c:v copy" in j and "music.wav" in j and "-ar" in c and "48000" in c and "3.500" in c


def test_measured_loudness_is_parsed():
    err = 'blah\n[Parsed_loudnorm_5 @ 0x1] \n{\n\t"input_i" : "-17.90",\n\t"input_tp" : "-3.10"\n}\n'
    assert mix.parse_input_i(err) == -17.9


def test_props_no_cumulative_drift():
    data = {"scenes": [{"n": i + 1, "type": "anim", "section": "S", "section_start": False, "anim": None,
                        "duration": 1.017} for i in range(60)]}
    p = render.props(data, [])
    assert p["total"] == round(60 * 1.017 * 30)
    assert all(a["from"] + a["frames"] == b["from"] for a, b in zip(p["scenes"], p["scenes"][1:]))
    assert p["scenes"][-1]["from"] + p["scenes"][-1]["frames"] == p["total"]


def test_props_total_never_shorter_than_narration():
    data = {"scenes": [{"n": 1, "type": "anim", "section": "S", "section_start": False, "anim": None,
                        "duration": 1.01}]}
    assert render.props(data, [])["total"] >= 31


def test_missing_photo_stops_the_render_instead_of_rendering_without_it(tmp_path):
    import json
    import pytest
    from PIL import Image
    (tmp_path / "owl").mkdir()
    for n in (1, 2):
        Image.new("RGBA", (8, 8)).save(tmp_path / "owl" / f"sc0{n}.png")
    (tmp_path / "scenes.json").write_text(json.dumps(DATA))
    (tmp_path / "captions.json").write_text("[]")
    with pytest.raises(FileNotFoundError, match="img.sc01.png"):
        render.main(str(tmp_path), runner=lambda *a, **k: None)


def test_mix_without_music_stops(tmp_path):
    import json
    import pytest
    (tmp_path / "scenes.json").write_text(json.dumps(DATA))
    with pytest.raises(FileNotFoundError, match="music.wav"):
        mix.main(str(tmp_path))


def test_render_writes_to_a_tmp_file_then_renames(tmp_path):
    import json
    from PIL import Image
    for sub in ("img", "owl"):
        (tmp_path / sub).mkdir()
    Image.new("RGB", (32, 18)).save(tmp_path / "img" / "sc01.png")
    for n in (1, 2):
        Image.new("RGBA", (8, 8)).save(tmp_path / "owl" / f"sc0{n}.png")
    (tmp_path / "scenes.json").write_text(json.dumps(DATA))
    (tmp_path / "captions.json").write_text("[]")
    seen = []

    def runner(cmd, **k):
        out = cmd[5]
        seen.append(out)
        open(out, "wb").write(b"mp4")
    render.main(str(tmp_path), runner=runner)
    assert seen[0].endswith("video_raw.tmp.mp4") and (tmp_path / "video_raw.mp4").read_bytes() == b"mp4"


def test_gain_is_corrected_for_what_the_limiter_eats():
    def measure(gain):                       # limiter 0 dB-den yuxari her dB-in 30%-ni yeyir
        return -22.0 + gain - 0.3 * max(0.0, gain)
    gain = mix.solve_gain(measure)
    assert abs(measure(gain) - mix.TARGET_LUFS) <= mix.TOLERANCE_LU


def test_measure_cmd_includes_the_gain_and_limiter():
    m = " ".join(mix.measure_cmd("E", 3.5, gain_db=4.0))
    assert "volume=4.0dB" in m and "alimiter=" in m and "print_format=json" in m


def test_intro_outro_props_carry_their_background_and_the_title():
    data = {"title": "How Apps Pay", "scenes": [
        {"n": 0, "type": "intro", "section": "", "section_start": False, "anim": None, "duration": 6.0},
        {"n": 1, "type": "outro", "section": "", "section_start": False, "anim": None, "duration": 10.0}]}
    p = render.props(data, [])
    assert p["scenes"][0]["img"] == "img/sc00.jpg" and p["scenes"][1]["img"] == "img/sc01.jpg"
    assert p["title"] == "How Apps Pay"
