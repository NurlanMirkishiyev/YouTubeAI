import pytest

import audio_master as am

LOUDNORM_STDERR = """[Parsed_loudnorm_1 @ 0000]
{
	"input_i" : "-20.50",
	"input_tp" : "-3.10",
	"input_lra" : "5.20",
	"input_thresh" : "-30.80",
	"output_i" : "-14.02",
	"output_tp" : "-1.50",
	"output_lra" : "4.10",
	"output_thresh" : "-24.30",
	"normalization_type" : "dynamic",
	"target_offset" : "0.02"
}
"""


def test_mix_without_music():
    g = am.mix_graph(3, None, 4.0, 100.0)
    assert "[3:a]" in g and "aresample=48000" in g
    assert "pan=stereo|c0=c0|c1=c0" in g
    assert "adelay=delays=4000:all=1" in g
    assert "apad=whole_dur=100.000" in g
    assert "sidechaincompress" not in g
    assert g.endswith("[amix]")


def test_mix_with_music_ducks():
    g = am.mix_graph(3, 4, 0.0, 50.0)
    assert "[4:a]" in g and "sidechaincompress" in g and "amix=inputs=2" in g
    assert g.endswith("[amix]")


def test_parse_loudnorm_json():
    m = am.parse_loudnorm_json(LOUDNORM_STDERR)
    assert m["input_i"] == "-20.50" and m["target_offset"] == "0.02"


def test_parse_loudnorm_missing_raises():
    with pytest.raises(ValueError):
        am.parse_loudnorm_json("no json")


def test_loudnorm_apply():
    f = am.loudnorm_apply(am.parse_loudnorm_json(LOUDNORM_STDERR))
    assert f.startswith("[amix]loudnorm=I=-14")
    assert "measured_I=-20.50" in f and "offset=0.02" in f and "linear=true" in f
    assert f.endswith("[aout]")
