"""#54 (istifadeci 2026-10-05): altyazi ssenaridən yaradilir (whisper yalniz vaxt verir), reqemler "$4,000"."""
from captions import align_segment, build_captions, number_problems, to_srt


def _w(text, start, step=0.4):
    return [{"word": " " + t, "start": round(start + i * step, 3), "end": round(start + i * step + 0.3, 3)}
            for i, t in enumerate(text.split())]


def test_script_words_take_whisper_timings():
    out = align_segment("Rent is $4,000 a month.", _w("Rent is $4,000 a month.", 1.0), 1.0, 3.5)
    assert [w["word"].strip() for w in out] == ["Rent", "is", "$4,000", "a", "month."]
    assert out[2]["start"] == 1.8


def test_spelled_whisper_number_maps_to_one_display_word():
    whisper = _w("It costs four thousand dollars now.", 0.0)
    out = align_segment("It costs four thousand dollars now.", whisper, 0.0, 3.0)
    assert [w["word"].strip() for w in out] == ["It", "costs", "$4,000", "now."]
    assert out[2]["start"] == 0.8 and out[2]["end"] == 1.9


def test_misheard_word_is_interpolated_in_order():
    out = align_segment("Maria runs a bakery in Austin.", _w("Maria runs a backery in Boston.", 0.0), 0.0, 3.0)
    words = [w["word"].strip() for w in out]
    assert words == ["Maria", "runs", "a", "bakery", "in", "Austin."]
    starts = [w["start"] for w in out]
    assert starts == sorted(starts) and 0.0 <= starts[0] and out[-1]["end"] <= 3.0


def test_captions_cover_cards_titles_and_narration():
    data = {"intro_seconds": 2.0, "outro_seconds": 2.0,
            "card_texts": {"intro": "A $9.99 price can lose money.", "outro": "Thanks for watching!"},
            "scenes": [{"narration": "Rent is $4,000.", "spoken_title": None, "duration": 2.0},
                       {"narration": "Margins are thin.", "spoken_title": "Pricing", "duration": 2.0}]}
    whisper = (_w("A $9.99 price can lose money.", 0.0, 0.3) + _w("Rent is $4,000.", 2.0)
               + _w("Pricing. Margins are thin.", 4.0) + _w("Thanks for watching!", 6.0))
    words, _ = build_captions(data, whisper)
    text = " ".join(w["word"].strip() for w in words)
    assert text == "A $9.99 price can lose money. Rent is $4,000. Pricing. Margins are thin. Thanks for watching!"


def test_mispronounced_number_is_reported():
    data = {"intro_seconds": 0.5, "outro_seconds": 0.5, "card_texts": {"intro": "Hi.", "outro": "Bye."},
            "scenes": [{"narration": "It costs $9.99 today.", "spoken_title": None, "duration": 2.0}]}
    whisper = _w("Hi.", 0.0, 0.1) + _w("It costs $999 today.", 0.5) + _w("Bye.", 2.5, 0.1)
    _, report = build_captions(data, whisper)
    assert number_problems(report) and "9.99" in number_problems(report)[0]


def test_correct_numbers_pass():
    data = {"intro_seconds": 0.5, "outro_seconds": 0.5, "card_texts": {"intro": "Hi.", "outro": "Bye."},
            "scenes": [{"narration": "It costs $9.99, about fifteen percent more.", "spoken_title": None,
                        "duration": 3.0}]}
    whisper = _w("Hi.", 0.0, 0.1) + _w("It costs $9.99, about 15% more.", 0.5) + _w("Bye.", 3.5, 0.1)
    words, report = build_captions(data, whisper)
    assert number_problems(report) == []
    assert "15%" in " ".join(w["word"] for w in words)


def test_srt_uses_display_numbers():
    srt = to_srt(_w("Rent is $4,000 a month.", 0.0))
    assert "$4,000" in srt and srt.startswith("1\n00:00:00,000 --> ")
