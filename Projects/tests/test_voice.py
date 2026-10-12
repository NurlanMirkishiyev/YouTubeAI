import numpy as np

import voice


def test_pad_to_extends_short_bookends_with_silence():
    w = voice.pad_to(np.ones(10, dtype=np.float32), 10, 3.0)
    assert len(w) == 30 and w[-1] == 0 and w[0] == 1


def test_pad_to_keeps_long_audio():
    assert len(voice.pad_to(np.ones(50, dtype=np.float32), 10, 3.0)) == 50


def test_minimum_lengths_are_six_and_ten_seconds():
    assert voice.MIN_S == {"intro": 6.0, "outro": 10.0}
