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


def test_single_clip_is_just_converted():
    cmd = mg.crossfade_cmd(["a.wav"], "out.wav", fade=3.0)
    assert "-filter_complex" not in cmd and cmd[-1] == "out.wav"


def test_track_length_matches_clip_count():
    assert mg.track_seconds(6, 45.0, 3.0) == 6 * 45.0 - 5 * 3.0
