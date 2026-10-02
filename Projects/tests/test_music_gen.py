import music_gen as mg


def test_each_episode_gets_its_own_stable_prompt_mix():
    a = mg.pick_prompts("what-is-cash-flow", 4)
    assert a == mg.pick_prompts("what-is-cash-flow", 4)          # resume eyni musiqini verir
    assert len(a) == 4 and len(set(a)) == 4
    assert all(p in mg.STYLES for p in a)
    assert {tuple(mg.pick_prompts(f"topic-{i}", 4)) for i in range(20)} != {tuple(a)}


def test_prompts_are_instrumental_background_music():
    for p in mg.STYLES:
        assert "instrumental" in p.lower()


def test_crossfade_chains_every_clip_into_one_track():
    cmd = mg.crossfade_cmd(["a.wav", "b.wav", "c.wav"], "out.wav", fade=3.0)
    assert cmd.count("-i") == 3 and cmd[-1] == "out.wav"
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count("acrossfade=d=3.0") == 2
    assert "-ar" in cmd and cmd[cmd.index("-ar") + 1] == "48000"


def test_every_clip_is_loudness_normalized_before_crossfade():
    # olculdu 2026-09-27: iki klip -17.3 ve -10.3 LUFS - normallasdirmasa musiqi 7 dB sicrayir
    cmd = mg.crossfade_cmd(["a.wav", "b.wav", "c.wav"], "out.wav", fade=3.0)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count(f"loudnorm=I={mg.CLIP_LUFS}") == 3
    assert graph.index("loudnorm") < graph.index("acrossfade")


def test_clip_edge_silence_is_trimmed():
    # olculdu 2026-09-27: klipler 0.8-2.4 s sukutla bitir -> dovr edende musiqide bosluq
    cmd = mg.crossfade_cmd(["a.wav", "b.wav"], "out.wav", fade=3.0)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count("areverse") == 4 + 2 and graph.count("silenceremove") == 4  # +2: yekun fade-out
    assert graph.index("silenceremove") < graph.index("loudnorm")


def test_reverb_tail_is_cut_harder_so_the_loop_seam_has_no_hole():
    # olculdu 2026-09-27 (what-is-profit-margin): son klip ~4 s reverb quyrugu ile -21 -> -50 dB sonur,
    # -50 dB hedd onu kesmirdi -> dovr noqtesinde videoda 1.25 s sukut
    cmd = mg.crossfade_cmd(["a.wav", "b.wav"], "out.wav", fade=3.0)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count(f"start_threshold={mg.TAIL_DB}dB") == 2       # areverse-den sonra = klipin sonu
    assert graph.count(f"start_threshold={mg.SILENCE_DB}dB") == 2    # klipin basi yumsaq qalir
    assert mg.SILENCE_DB < mg.TAIL_DB <= -30
    last = graph.split(";")[-1]                                     # yekun trek qisa fade ile bitir
    assert f"areverse,afade=t=in:d={mg.END_FADE_S},areverse" in last and cmd[cmd.index("-map") + 1] in last


def test_single_clip_is_normalized_too():
    cmd = mg.crossfade_cmd(["a.wav"], "out.wav", fade=3.0)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "loudnorm" in graph and "acrossfade" not in graph and cmd[-1] == "out.wav"


def test_track_length_matches_clip_count():
    assert mg.track_seconds(6, 45.0, 3.0) == 6 * 45.0 - 5 * 3.0


SILENCE_LOG = """[silencedetect @ 0x1] silence_start: 142.134125
[silencedetect @ 0x1] silence_end: 143.09825 | silence_duration: 0.964125
[silencedetect @ 0x1] silence_start: 221.95
[silencedetect @ 0x1] silence_end: 222.325 | silence_duration: 0.375
"""


def test_internal_music_gaps_are_found_but_end_fade_is_ignored():
    """Real hal 2026-10-03 (why-9-99): model klipin ortasinda ~1 s pauza verdi (-40 dB) - videoda 587 s-de
    danisiq pauzasi ile ust-uste dusub 0.67 s tam sukut oldu."""
    assert mg.parse_gaps(SILENCE_LOG, track_s=222.325) == [(142.134125, 0.964125)]


def test_track_with_a_gap_is_regenerated_with_a_new_seed(tmp_path):
    seeds = []

    def make(seed, out):
        seeds.append(seed)
        open(out, "w").close()

    gaps = iter([[(142.1, 0.96)], []])
    tries = mg.build_track(10, str(tmp_path / "m.wav"), make, lambda p: next(gaps))
    assert tries == 2 and len(set(seeds)) == 2
    assert [p.name for p in tmp_path.iterdir()] == ["m.wav"]


def test_hopeless_gaps_keep_the_least_silent_try(tmp_path):
    out = tmp_path / "m.wav"

    def make(seed, path):
        with open(path, "w") as f:
            f.write(str(seed))

    gaps = iter([[(1.0, 0.9)], [(1.0, 0.5)], [(1.0, 0.8)]])
    mg.build_track(10, str(out), make, lambda p: next(gaps))
    assert out.read_text() == str(10 + mg.SEED_STEP)
