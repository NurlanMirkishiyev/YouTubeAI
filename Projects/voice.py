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


def audio_chunks(results) -> list[tuple[np.ndarray, list]]:
    """Kokoro neticeleri -> [(audio, tokens)]; sessiz / bos parca atilir (sehne cokmur)."""
    out = []
    for r in results:
        if r.audio is None:
            continue
        a = np.asarray(r.audio, dtype=np.float32).reshape(-1)
        if a.size:
            out.append((a, r.tokens or []))
    return out


def word_times(chunks: list[tuple], sr: int) -> list[dict]:
    """[(tokens, audio_uzunlugu), ...] -> [{"w", "s", "e"}] sehne sesinin evvelinden (saniye). Durgu/vaxtsiz token atilir."""
    out, offset = [], 0.0
    for tokens, n_samples in chunks:
        for t in tokens or []:
            if t.start_ts is None or t.end_ts is None or not any(ch.isalnum() for ch in t.text):
                continue
            out.append({"w": t.text, "s": round(offset + t.start_ts, 3), "e": round(offset + t.end_ts, 3)})
        offset += n_samples / sr
    return out


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
            text = to_speech(s["text"]).strip()
            pieces = audio_chunks(pipe(text, voice=cfg["voice"], speed=cfg["speed"])) if text else []
            chunks = [a for a, _ in pieces]
            generate.atomic_json(os.path.join(ep, "voice", f"sc{s['n']:02d}.words.json"),
                                 word_times([(t, len(a)) for a, t in pieces], sr))
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
