import captions


def test_chunks_keep_every_word():
    text = "Imagine an app you use every single day, and you never pay for it."
    got = captions.chunks(text, 5)
    assert " ".join(got) == text and all(len(c.split()) <= 5 for c in got)


def test_timing_fills_each_scene_in_order():
    scenes = [{"text": "One two three four.", "duration": 2.35}, {"text": "Five six.", "duration": 1.35}]
    caps = captions.build(scenes, tail=0.35)
    assert caps[0]["start"] == 0.0 and abs(caps[-1]["end"] - 3.7) < 1e-6
    assert all(a["end"] <= b["start"] + 1e-9 for a, b in zip(caps, caps[1:]))


def test_srt_format():
    srt = captions.to_srt([{"start": 0.0, "end": 1.5, "text": "Hi there."}])
    assert srt == "1\n00:00:00,000 --> 00:00:01,500\nHi there.\n"


def test_empty_scene_text_yields_no_captions():
    assert captions.build([{"text": "", "duration": 1.0}]) == []


def test_empty_middle_scene_does_not_stretch_previous_caption():
    scenes = [
        {"text": "A b.", "duration": 1.0},
        {"text": "", "duration": 1.0},
        {"text": "C d.", "duration": 1.0},
    ]
    caps = captions.build(scenes)
    assert [c["text"] for c in caps] == ["A b.", "C d."]
    assert caps[0]["end"] == 1.0
    assert caps[1]["start"] == 2.0 and caps[1]["end"] == 3.0


def test_whitespace_only_scene_text_is_treated_as_empty():
    assert captions.build([{"text": "   \n ", "duration": 1.0}]) == []


def test_negative_duration_is_clamped_to_zero():
    caps = captions.build([{"text": "A b.", "duration": -1.0}])
    assert caps[0]["start"] == 0.0 and caps[0]["end"] == 0.0


def test_chunks_split_after_closing_quote():
    assert captions.chunks('a b c "d." e f', 7) == ['a b c "d."', "e f"]


def test_chunks_split_after_closing_bracket():
    assert captions.chunks("a b (c.) d e", 7) == ["a b (c.)", "d e"]


def test_every_caption_has_contiguous_word_timings_without_tts_timings():
    caps = captions.build([{"n": 1, "text": "One two three four five six seven eight nine.", "duration": 4.35}])
    words = [w for c in caps for w in c["words"]]
    assert [w["text"] for w in words] == "One two three four five six seven eight nine.".split()
    assert words[0]["start"] == 0.0 and all(a["end"] <= b["start"] + 1e-9 for a, b in zip(words, words[1:]))
    for c in caps:
        assert c["words"][0]["start"] >= c["start"] - 1e-9 and c["words"][-1]["end"] <= c["end"] + 1e-9


def test_tts_timings_drive_words_even_when_numbers_are_spoken_as_words():
    toks = [{"w": "It", "s": 0.1, "e": 0.3}, {"w": "costs", "s": 0.3, "e": 0.6}, {"w": "fifteen", "s": 0.6, "e": 0.9},
            {"w": "dollars", "s": 0.9, "e": 1.2}, {"w": "today", "s": 1.4, "e": 1.8}]
    caps = captions.build([{"n": 1, "text": "It costs $15 today.", "duration": 2.35}], timings={1: toks})
    got = [(w["text"], w["start"], w["end"]) for w in caps[0]["words"]]
    assert got == [("It", 0.1, 0.3), ("costs", 0.3, 0.6), ("$15", 0.6, 1.2), ("today.", 1.4, 1.8)]


def test_unmatched_word_is_interpolated_between_neighbours():
    toks = [{"w": "A", "s": 0.0, "e": 0.5}, {"w": "C", "s": 1.5, "e": 2.0}]
    caps = captions.build([{"n": 1, "text": "A Zzz C", "duration": 2.35}], timings={1: toks})
    a, z, c = caps[0]["words"]
    assert a["end"] <= z["start"] < z["end"] <= c["start"]


def test_scene_offsets_apply_to_tts_timings():
    toks = [{"w": "Hi", "s": 0.2, "e": 0.6}]
    caps = captions.build([{"n": 1, "text": "Yo.", "duration": 1.0}, {"n": 2, "text": "Hi", "duration": 1.0}],
                          timings={2: toks})
    assert caps[1]["words"][0]["start"] == 1.2 and caps[1]["words"][0]["end"] == 1.6


def test_main_reads_word_timings_from_voice_dir(tmp_path):
    import json
    (tmp_path / "voice").mkdir()
    (tmp_path / "voice" / "sc01.words.json").write_text(json.dumps([{"w": "Hi", "s": 0.25, "e": 0.5}]))
    (tmp_path / "scenes.json").write_text(json.dumps(
        {"slug": "s", "scenes": [{"n": 1, "text": "Hi", "duration": 1.0}]}))
    captions.main(str(tmp_path))
    caps = json.loads((tmp_path / "captions.json").read_text())
    assert caps[0]["words"][0]["start"] == 0.25
