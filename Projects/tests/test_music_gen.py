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
    assert graph.count("areverse") == 4 and graph.count("silenceremove") == 4
    assert graph.index("silenceremove") < graph.index("loudnorm")


def test_single_clip_is_normalized_too():
    cmd = mg.crossfade_cmd(["a.wav"], "out.wav", fade=3.0)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "loudnorm" in graph and "acrossfade" not in graph and cmd[-1] == "out.wav"


def test_track_length_matches_clip_count():
    assert mg.track_seconds(6, 45.0, 3.0) == 6 * 45.0 - 5 * 3.0
