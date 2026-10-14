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


class _Res:
    def __init__(self, audio, tokens=None):
        self.audio, self.tokens = audio, tokens


def test_empty_kokoro_chunks_are_skipped():
    got = voice.audio_chunks([_Res(None), _Res(np.ones(5)), _Res(np.zeros(0))])
    assert [len(a) for a, _ in got] == [5]


def test_main_writes_every_scene_and_the_full_narration(tmp_path, monkeypatch):
    import json
    import sys
    import types
    store = {}

    def _write(path, data, sr):
        store[str(path)] = np.asarray(data)
        open(path, "wb").close()

    def _read(path, dtype=None):
        return store[str(path).replace(".tmp", "")] if str(path).replace(".tmp", "") in store else store[str(path)], 24000

    def _replace(src, dst):
        if str(src) in store:
            store[str(dst)] = store.pop(str(src))
        real_replace(src, dst)
    import os as _os
    real_replace = _os.replace
    monkeypatch.setattr(voice.os, "replace", _replace)
    sf = types.SimpleNamespace(write=_write, read=_read)
    monkeypatch.setitem(sys.modules, "soundfile", sf)

    class _Pipe:
        def __init__(self, lang_code):
            pass

        def __call__(self, text, voice, speed):
            for i, w in enumerate(text.split()):
                yield _Res(np.ones(240, dtype=np.float32), [_Tok(w, 0.0, 0.01)])
    monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=_Pipe))
    cfg = tmp_path / "narrator.json"
    cfg.write_text(json.dumps({"sample_rate": 24000, "lang_code": "a", "voice": "v", "speed": 1.0}))
    monkeypatch.setattr(voice, "CONFIG", str(cfg))
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [
        {"n": 1, "text": "Hello there."}, {"n": 2, "text": "Two words more"}, {"n": 3, "text": ""}]}))
    voice.main(str(tmp_path))
    wav, sr = store[str(tmp_path / "narration.wav")], 24000
    data = json.loads((tmp_path / "scenes.json").read_text())
    assert abs(len(wav) / sr - sum(s["duration"] for s in data["scenes"])) < 0.01
    assert json.loads((tmp_path / "voice" / "sc02.words.json").read_text())[0]["w"] == "Two"
