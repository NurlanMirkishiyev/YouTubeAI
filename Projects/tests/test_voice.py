import numpy as np

import voice


def test_pad_to_extends_short_bookends_with_silence():
    w = voice.pad_to(np.ones(10, dtype=np.float32), 10, 3.0)
    assert len(w) == 30 and w[-1] == 0 and w[0] == 1


def test_pad_to_keeps_long_audio():
    assert len(voice.pad_to(np.ones(50, dtype=np.float32), 10, 3.0)) == 50


def test_minimum_lengths_are_six_and_ten_seconds():
    assert voice.MIN_S == {"intro": 6.0, "outro": 10.0}


class _Tok:
    def __init__(self, text, s, e):
        self.text, self.start_ts, self.end_ts = text, s, e


def test_word_times_offsets_each_chunk_and_skips_punctuation():
    chunks = [([_Tok("Hello", 0.1, 0.5), _Tok(",", 0.5, 0.6), _Tok("world", 0.6, 1.0)], 24000),   # 1.0 s audio
              ([_Tok("Again", 0.2, 0.7), _Tok("x", None, None)], 12000)]
    assert voice.word_times(chunks, 24000) == [
        {"w": "Hello", "s": 0.1, "e": 0.5}, {"w": "world", "s": 0.6, "e": 1.0}, {"w": "Again", "s": 1.2, "e": 1.7}]
