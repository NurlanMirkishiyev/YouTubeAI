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
NEGATIVE = ("vocals, singing, speech, voice, low quality, distortion, noise, harsh, sad, melancholic, boring, "
            "sleepy, dark, slow, monotonous")
# Her video ferqli stil (HISTORY: hamisi istifade olunana qeder tekrar yoxdur); hamisi heveslendirici, enerjili.
STYLES = (
    "Uplifting motivational corporate pop, bright piano, punchy claps, driving acoustic guitar, 120 BPM, instrumental",
    "Energetic inspiring indie pop, ukulele, hand claps, glockenspiel, happy bouncy groove, 125 BPM, instrumental",
    "Inspiring cinematic build, pulsing strings, bright piano, big uplifting drums, 118 BPM, instrumental",
    "Upbeat motivational electronic pop, shiny synth plucks, punchy kick, positive energy, 124 BPM, instrumental",
    "Uplifting funky groove, slap bass, bright electric guitar, tight drums, confident and fun, 112 BPM, instrumental",
    "Energetic inspiring tropical house, marimba, warm synth, clap beat, sunny and positive, 115 BPM, instrumental",
    "Driving motivational rock-pop, crunchy electric guitar, steady energetic drums, optimistic, 128 BPM, instrumental",
    "Uplifting future bass, bright chords, playful synth melody, energetic beat, 130 BPM, instrumental",
    "Inspiring piano pop, bouncy piano chords, upbeat drums, warm bass, hopeful and motivating, 116 BPM, instrumental",
    "Energetic motivational hip-hop beat, punchy drums, bright brass stabs, confident groove, 95 BPM, instrumental",
    "Uplifting folk pop, strummed acoustic guitar, whistles, stomps and claps, cheerful energy, 122 BPM, instrumental",
    "Inspiring synthwave, driving arpeggios, bright lead synth, energetic drums, forward motion, 118 BPM, instrumental",
)
HISTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "music_history.json")


def pick_style(slug: str, path: str = HISTORY) -> str:
    """Video ucun stil: evvel secilibse eynisi (resume), yoxsa hec bir videoda olmayan stil; hamisi istifade
    olunubsa en kohne istifade olunan. Secim path-e yazilir ({slug: stil}, sira = istifade ardicilligi)."""
    hist = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            hist = json.load(f)
    if hist.get(slug) in STYLES:
        return hist[slug]
    used = [s for s in hist.values() if s in STYLES]
    fresh = [s for s in STYLES if s not in used]
    style = fresh[0] if fresh else min(STYLES, key=lambda s: max(i for i, u in enumerate(used) if u == s))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({**hist, slug: style}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return style


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
    style = pick_style(data["slug"])
    print(f"  musiqi stili: {style}", flush=True)
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
