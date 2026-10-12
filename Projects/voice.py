"""Kokoro (TTS\\.venv): sehne-sehne WAV + narration.wav; scenes.json-da duration = ses + TAIL_S.
Istifade: TTS\\.venv\\Scripts\\python Projects\\voice.py Episodes\\<slug>"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402
from speech import to_speech  # noqa: E402

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TTS", "config", "narrator.json")
TAIL_S = 0.35
MIN_S = {"intro": 6.0, "outro": 10.0}


def pad_to(wav: np.ndarray, sr: int, seconds: float) -> np.ndarray:
    need = int(round(seconds * sr)) - len(wav)
    return np.concatenate([wav, np.zeros(need, dtype=wav.dtype)]) if need > 0 else wav


def main(ep: str) -> None:
    import soundfile as sf
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    sr = int(cfg["sample_rate"])
    path = os.path.join(ep, "scenes.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.join(ep, "voice"), exist_ok=True)
    from kokoro import KPipeline
    pipe = KPipeline(lang_code=cfg["lang_code"])
    parts = []
    for s in data["scenes"]:
        wav_path = os.path.join(ep, "voice", f"sc{s['n']:02d}.wav")
        if os.path.isfile(wav_path):
            wav, _ = sf.read(wav_path, dtype="float32")
        else:
            chunks = [np.asarray(a, dtype=np.float32) for _, _, a in pipe(to_speech(s["text"]), voice=cfg["voice"], speed=cfg["speed"])]
            wav = np.concatenate(chunks + [np.zeros(int(TAIL_S * sr), dtype=np.float32)])
            wav = pad_to(wav, sr, MIN_S.get(s.get("type"), 0.0))
            sf.write(generate.tmp_path(wav_path), wav, sr)
            os.replace(generate.tmp_path(wav_path), wav_path)
        s["duration"] = round(len(wav) / sr, 3)
        parts.append(wav)
        print(f"  ses sc{s['n']:02d} {s['duration']:.1f} s", flush=True)
    generate.atomic_json(path, data)   # evvel duration-lar, sonra narration.wav (done isaresi)
    out = os.path.join(ep, "narration.wav")
    sf.write(generate.tmp_path(out), np.concatenate(parts), sr)
    os.replace(generate.tmp_path(out), out)


if __name__ == "__main__":
    main(sys.argv[1])
