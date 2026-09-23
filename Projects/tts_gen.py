"""Add'im 25 - scenes.json -> her sehne ucun WAV + birlesmis narration.wav (Kokoro, am_fenrir).
Istifade:
  TTS\\.venv\\Scripts\\python Projects\\tts_gen.py Episodes\\<slug> [--only 3 7] [--force]
Cixis: Episodes\\<slug>\\audio\\sc01.wav ... + narration.wav
       scenes.json-da "duration" GERCEK audio uzunluguna yenilenir (tehmin evezine).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import soundfile as sf

CONFIG = r"C:\YouTubeAI\TTS\config\narrator.json"
GAP_S = 0.25          # sehneler arasi qisa nefes
TAIL_S = 0.15         # her sehnenin sonunda kicik bosluq


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def synth(pipeline, text: str, voice: str, speed: float) -> np.ndarray:
    """Kokoro metni oz-ozune parcalayir - butun parcalar birlesdirilir."""
    chunks = [np.asarray(audio, dtype=np.float32)
              for _, _, audio in pipeline(text, voice=voice, speed=speed)]
    if not chunks:
        raise RuntimeError("kokoro bos audio qaytardi")
    return np.concatenate(chunks)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--only", nargs="*", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    scenes_path = os.path.join(a.episode_dir, "scenes.json")
    if not os.path.isfile(scenes_path):
        raise SystemExit("scenes.json tapilmadi: " + scenes_path)
    cfg = load_config()
    sr = int(cfg["sample_rate"])

    with open(scenes_path, encoding="utf-8") as f:
        data = json.load(f)
    scenes = data["scenes"]
    audio_dir = os.path.join(a.episode_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    todo = [i for i in range(len(scenes))
            if (not a.only or i + 1 in a.only)
            and (a.force or not os.path.isfile(os.path.join(audio_dir, f"sc{i + 1:02d}.wav")))]
    print(f"[25] {len(todo)}/{len(scenes)} sehne seslendirilecek  ({cfg['voice']}, {sr} Hz)")

    if todo:
        from kokoro import KPipeline          # yuklenmesi uzun cekir - yalniz lazim olanda
        pipe = KPipeline(lang_code=cfg["lang_code"])
        t0 = time.time()
        for k, i in enumerate(todo, 1):
            wav = synth(pipe, scenes[i]["narration"], cfg["voice"], float(cfg["speed"]))
            wav = np.concatenate([wav, np.zeros(int(TAIL_S * sr), dtype=np.float32)])
            sf.write(os.path.join(audio_dir, f"sc{i + 1:02d}.wav"), wav, sr)
            el = time.time() - t0
            print(f"  [{k}/{len(todo)}] sc{i + 1:02d}  {len(wav) / sr:5.1f}s audio  "
                  f"qalan ~{(len(todo) - k) * el / k / 60:.1f} deq")

    # gercek muddetler + birlesmis narration
    parts: list[np.ndarray] = []
    gap = np.zeros(int(GAP_S * sr), dtype=np.float32)
    missing = []
    for i, s in enumerate(scenes):
        p = os.path.join(audio_dir, f"sc{i + 1:02d}.wav")
        if not os.path.isfile(p):
            missing.append(i + 1)
            continue
        wav, file_sr = sf.read(p, dtype="float32")
        if file_sr != sr:
            raise SystemExit(f"sc{i + 1:02d}.wav sample rate {file_sr} != {sr}")
        s["audio"] = p
        s["duration"] = round(len(wav) / sr + (GAP_S if i < len(scenes) - 1 else 0.0), 2)
        parts += [wav] if i == len(scenes) - 1 else [wav, gap]

    if missing:
        raise SystemExit(f"catismayan audio: {missing} - once onlari seslendir")

    narration = np.concatenate(parts)
    narration_path = os.path.join(a.episode_dir, "narration.wav")
    sf.write(narration_path, narration, sr)

    total = len(narration) / sr
    data["total_seconds"] = round(total, 2)
    data["audio_seconds"] = round(total, 2)
    with open(scenes_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    drift = abs(sum(s["duration"] for s in scenes) - total)
    print(f"  narration.wav  {total / 60:.2f} deq  -> {narration_path}")
    print(f"  sehne muddetleri cemi ile ferq: {drift:.2f}s")
    if drift > 0.05:
        print("  DIQQET: muddet cemi audio ile uygun gelmir")


if __name__ == "__main__":
    main()
