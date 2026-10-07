"""Faza 3.8 (istifadeci 2026-10-07; reference make_sfx/make_ticks): SFX qati - pulsuz, lisenziyasiz (ffmpeg lavfi),
Projects/sfx/-de istifadeci fayli varsa o secilir. Hadiseler: bolme kecidi -> whoosh; reqem/kart reveal -> pop + tick;
timeseries enisi -> boom. Sixliq: her 10 s-de <= 2; nitq sozunun ortasina dusmur; nitqden >= 18 dB asagi;
nitq + musiqi + SFX qarisir, SONRA iki kecidli -14 LUFS loudnorm."""
import os
import subprocess

import pytest

import audio_master as am
import sfx

WORDS = [{"w": "Rosa", "s": 4.0, "e": 4.5}, {"w": "now", "s": 4.6, "e": 5.0}, {"w": "charges", "s": 5.1, "e": 5.8}]
PROPS = {"fps": 30, "introFrames": 60, "scenes": [
    {"frames": 300, "title": "Pricing", "visual": None},
    {"frames": 300, "title": None, "visual": {"kind": "stats"}, "reveal": [30, 120, 200]},
    {"frames": 300, "title": "Decision", "visual": {"kind": "timeseries",
                                                    "segments": [{"from": 0, "to": 1, "down": False},
                                                                 {"from": 1, "to": 2, "down": True}]},
     "reveal": [10, 100, 200]},
]}


def test_events_follow_the_timeline():
    ev = sfx.events(PROPS, [])
    names = [e["name"] for e in ev]
    assert "whoosh" in names and "pop_tick" in names and "boom" in names
    whoosh = next(e for e in ev if e["name"] == "whoosh")
    assert abs(whoosh["t"] - ((60 + 600) / 30 - sfx.WHOOSH_LEAD_S)) < 1e-3      # bolme kecidinde
    boom = next(e for e in ev if e["name"] == "boom")
    assert abs(boom["t"] - (60 + 600 + 200) / 30) < 1e-3        # ms deqiqliyi


def test_density_is_at_most_two_per_ten_seconds():
    ev = sfx.events(PROPS, [])
    ts = [e["t"] for e in ev]
    assert all(sum(1 for x in ts if t <= x < t + 10) <= sfx.MAX_PER_WINDOW for t in ts)
    assert any(e["name"] == "boom" for e in ev)          # prioritet: boom qalir


def test_sfx_never_lands_in_the_middle_of_a_word():
    t = sfx.snap(4.8, WORDS)
    assert not any(w["s"] < t < w["e"] for w in WORDS)
    assert sfx.snap(5.05, WORDS) == 5.05                # sozler arasi bosluq


def test_user_file_overrides_the_generated_sound(tmp_path):
    user = tmp_path / "user"
    user.mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=900:d=0.2",
                    str(user / "pop.wav")], check=True)
    got = sfx.sounds(str(tmp_path / "gen"), user_dir=str(user))
    assert got["pop"] == str(user / "pop.wav") and os.path.isfile(got["whoosh"])


def _mean_db(path: str) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(r.stderr.split("mean_volume:")[1].split("dB")[0])


@pytest.fixture(scope="module")
def mixdir(tmp_path_factory):
    d = tmp_path_factory.mktemp("mix")
    narr = str(d / "narr.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=f=220:d=12:sample_rate=24000,volume=0.3", "-ac", "1", narr], check=True)
    ev = [{"t": 2.0, "name": "whoosh"}, {"t": 6.0, "name": "pop_tick"}, {"t": 9.0, "name": "boom"}]
    track = str(d / "sfx.wav")
    sfx.render_track(ev, sfx.sounds(str(d / "gen")), 12.0, track, narr)
    return d, narr, track


def test_sfx_sits_at_least_18_db_below_speech(mixdir):
    d, narr, track = mixdir
    loud = str(d / "sfx_only_active.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", track, "-af",
                    "silenceremove=stop_periods=-1:stop_duration=0.05:stop_threshold=-90dB", loud], check=True)
    assert _mean_db(narr) - _mean_db(loud) >= sfx.BELOW_SPEECH_DB


def test_master_mixes_sfx_before_loudnorm_to_minus_14(mixdir):
    d, narr, track = mixdir
    graph = am.mix_graph(0, None, 0.0, 12.0, sfx_in=1)
    assert "[1:a]" in graph and graph.endswith("[amix]")
    m = am.measure(["-i", narr, "-i", track], graph, 12.0)
    out = str(d / "final.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", narr, "-i", track, "-filter_complex",
                    f"{graph};{am.loudnorm_apply(m)}", "-map", "[aout]", "-t", "12", out], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    lufs = float(r.stderr.rsplit("I:", 1)[1].split("LUFS")[0])
    assert abs(lufs - (-14.0)) <= 1.0


def test_sfx_problems_catch_density_mid_word_and_silence():
    assert sfx.problems([], WORDS) == ["SFX hadisesi yoxdur"]
    assert sfx.problems([{"t": 1.0, "name": "pop_tick"}], WORDS) == []
    assert any("ortasina" in p for p in sfx.problems([{"t": 4.8, "name": "pop_tick"}], WORDS))
    dense = [{"t": 1.0, "name": "a"}, {"t": 2.0, "name": "b"}, {"t": 3.0, "name": "c"}]
    assert any("sixliq" in p for p in sfx.problems(dense, []))
