import copy

import pytest

import checks

GOOD = {
    "streams": [
        {"codec_type": "video", "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p",
         "level": 41, "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "600.000"},
        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2,
         "duration": "600.050"},
    ],
    "format": {"duration": "600.050"},
}


def test_good_info_has_no_problems():
    assert checks.video_problems(GOOD) == []
    assert checks.audio_problems(GOOD) == []


def test_yuv444_is_reported():
    bad = copy.deepcopy(GOOD)
    bad["streams"][0]["pix_fmt"] = "yuv444p"
    assert any("yuv444p" in p for p in checks.video_problems(bad))


def test_mono_24k_audio_is_reported():
    bad = copy.deepcopy(GOOD)
    bad["streams"][1].update(sample_rate="24000", channels=1)
    probs = checks.audio_problems(bad)
    assert any("24000" in p for p in probs) and any("channels=1" in p for p in probs)


def test_av_drift():
    assert checks.av_drift(GOOD) == pytest.approx(0.05)


def test_parse_ebur128_takes_summary_not_frame_lines():
    stderr = ("[Parsed_ebur128_0 @ 0] t: 0.1  TARGET:-23 LUFS  M: -70.0 S:-70.0  I: -70.0 LUFS\n"
              "[Parsed_ebur128_0 @ 0] Summary:\n\n  Integrated loudness:\n    I:         -14.2 LUFS\n"
              "    Threshold: -24.3 LUFS\n")
    assert checks.parse_ebur128_integrated(stderr) == pytest.approx(-14.2)


def test_parse_ebur128_missing_raises():
    with pytest.raises(ValueError):
        checks.parse_ebur128_integrated("nothing here")
