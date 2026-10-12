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
