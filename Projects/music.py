"""Stable Audio Open (MusicGen\\.venv, lokal GPU): video uzunlugunda fon musiqisi -> music.wav.
Klipler crossfade ile birlesir; video daha uzundursa mix merhelesi dovr etdirir.
Istifade: MusicGen\\.venv\\Scripts\\python Projects\\music.py Episodes\\<slug>"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys

MODEL = "stabilityai/stable-audio-open-1.0"
MODEL_FILES = ["model_index.json", "projection_model/*", "scheduler/*", "text_encoder/*", "tokenizer/*",
               "transformer/*", "vae/*"]
CLIP_S, FADE_S, STEPS, MAX_CLIPS = 45.0, 3.0, 100, 8
NEGATIVE = "vocals, singing, speech, voice, low quality, distortion, noise, harsh, loud drums"
STYLES = (
    "Light upbeat corporate background music, soft acoustic guitar, warm piano, positive, 110 BPM, instrumental",
    "Calm lo-fi explainer background, mellow electric piano, soft bass, light brushed drums, 90 BPM, instrumental",
    "Modern minimal documentary background, soft piano, warm cello, subtle pulse, 100 BPM, instrumental",
    "Sleek corporate ambient, deep synth bass, soft electric piano chords, steady light beat, 105 BPM, instrumental",
)


def pick_device(cuda_ok: bool) -> tuple[str, str]:
    """GPU varsa cuda/float16; yoxdursa (driver xetasi) CPU/float32 - yavas, amma musiqi yene cekilir."""
    return ("cuda", "float16") if cuda_ok else ("cpu", "float32")


def clips_needed(total_s: float) -> int:
    return max(1, min(MAX_CLIPS, math.ceil(total_s / (CLIP_S - FADE_S))))


def main(ep: str) -> None:
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    import soundfile as sf
    import torch
    from diffusers import StableAudioPipeline
    from huggingface_hub import snapshot_download

    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    total = sum(s["duration"] for s in data["scenes"])
    seed = int.from_bytes(hashlib.sha1(data["slug"].encode()).digest()[:4], "big")
    style = STYLES[seed % len(STYLES)]
    device, dtype = pick_device(torch.cuda.is_available())
    if device == "cpu":
        print("  musiqi: CUDA yoxdur - CPU-da cekilir (yavas)", flush=True)
    pipe = StableAudioPipeline.from_pretrained(snapshot_download(MODEL, allow_patterns=MODEL_FILES),
                                               torch_dtype=getattr(torch, dtype)).to(device)
    parts_dir = os.path.join(ep, "music_parts")
    os.makedirs(parts_dir, exist_ok=True)
    paths = []
    for i in range(clips_needed(total)):
        p = os.path.join(parts_dir, f"part{i + 1:02d}.wav")
        if not os.path.isfile(p):
            audio = pipe(style, negative_prompt=NEGATIVE, num_inference_steps=STEPS, audio_end_in_s=CLIP_S,
                         generator=torch.Generator(device).manual_seed(seed + i)).audios[0]
            sf.write(p[:-4] + ".tmp.wav", audio.T.float().cpu().numpy(), pipe.vae.sampling_rate)
            os.replace(p[:-4] + ".tmp.wav", p)
        paths.append(p)
        print(f"  musiqi {i + 1}/{clips_needed(total)}", flush=True)
    out = os.path.join(ep, "music.wav")
    tmp = os.path.join(ep, "music.tmp.wav")      # music.wav yalniz tam yazilanda gorunur (done isaresi)
    if len(paths) == 1:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", paths[0], tmp], check=True)
        os.replace(tmp, out)
        return
    inputs = sum((["-i", p] for p in paths), [])
    chain, last = [], "[0:a]"
    for i in range(1, len(paths)):
        tag = f"[a{i}]"
        chain.append(f"{last}[{i}:a]acrossfade=d={FADE_S}:c1=tri:c2=tri{tag}")
        last = tag
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain),
                    "-map", last, tmp], check=True)
    os.replace(tmp, out)


if __name__ == "__main__":
    main(sys.argv[1])
