"""AI fon musiqisi: Stable Audio Open 1.0 (lokal GPU, pulsuz) -> Episodes\\<slug>\\music.wav
Istifade:
  MusicGen\\.venv\\Scripts\\python Projects\\music_gen.py Episodes\\<slug> [--clips 6] [--force]

Istifadeci 2026-09-27: musiqi lisenziya/istinad teleb etmesin ve odenisli olmasin. Stability AI Community
License: illik gelir < $1M pulsuz, cixis istifadeciye mexsusdur, cixis ucun istinad yoxdur (kommersiya
istifadesi ucun pulsuz qeydiyyat). Model bir defede <= 47 s verir - ferqli ussluba CLIPS hisse cekilir,
crossfade ile birlesdirilir; remotion_build videonun uzunluguna qeder dovr etdirir (-stream_loop).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import time

MODEL = "stabilityai/stable-audio-open-1.0"
MODEL_FILES = ["model_index.json", "projection_model/*", "scheduler/*", "text_encoder/*", "tokenizer/*",
               "transformer/*", "vae/*"]
CLIPS = 6
CLIP_S = 45.0
FADE_S = 3.0
STEPS = 100
OUT = "music.wav"
CLIP_LUFS = -18  # kohne CC BY trekler -18..-20 idi; audio_master.MUSIC_DB buna gore kalibrlidir
CLIP_TP = -1.5
SILENCE_DB = -50
NEGATIVE = "vocals, singing, speech, voice, low quality, distortion, noise, harsh, loud drums"
STYLES = (
    "Light upbeat corporate background music, soft acoustic guitar, warm piano, gentle claps, positive, "
    "110 BPM, instrumental, no vocals",
    "Calm lo-fi explainer background, mellow electric piano, soft bass, light brushed drums, curious and "
    "friendly, 90 BPM, instrumental",
    "Playful pizzicato strings and marimba, light percussion, cheerful kids educational background, "
    "100 BPM, instrumental",
    "Soft ukulele and glockenspiel, whistling-free, sunny and optimistic background, 105 BPM, instrumental",
    "Gentle ambient pads with plucked synth arpeggio, focused and thoughtful tech explainer background, "
    "95 BPM, instrumental",
    "Warm jazzy piano trio, soft upright bass, brushed snare, relaxed cafe background, 92 BPM, instrumental",
    "Bright indie pop background, clean electric guitar, light shaker, uplifting, 115 BPM, instrumental",
    "Minimal soft piano and light strings, calm and hopeful background, 80 BPM, instrumental",
)


def _seed(slug: str) -> int:
    return int.from_bytes(hashlib.sha1(slug.encode("utf-8")).digest()[:4], "big")


def pick_prompts(slug: str, n: int) -> list[str]:
    """Slug-a gore sabit (resume eyni musiqi), epizodlar arasinda ferqli usslub qarisigi."""
    k = _seed(slug) % len(STYLES)
    order = STYLES[k:] + STYLES[:k]
    return list(order[:n])


def track_seconds(clips: int, clip_s: float, fade: float) -> float:
    return clips * clip_s - (clips - 1) * fade


def crossfade_cmd(clips: list[str], out: str, fade: float) -> list[str]:
    """Her klipin bas/son sukutu kesilir (model 0.8-2.4 s sukutla bitirir, dovrde bosluq olurdu),
    sonra eyni seviyyeye (CLIP_LUFS) getirilir - model klipleri 7 dB ferqli verir."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", c]
    trim = f"silenceremove=start_periods=1:start_threshold={SILENCE_DB}dB:start_silence=0.05"
    parts = [f"[{i}:a]{trim},areverse,{trim},areverse,"
             f"loudnorm=I={CLIP_LUFS}:TP={CLIP_TP}:LRA=11[n{i}]" for i in range(len(clips))]
    prev = "[n0]"
    for i in range(1, len(clips)):
        label = f"[x{i}]"
        parts.append(f"{prev}[n{i}]acrossfade=d={fade}:c1=tri:c2=tri{label}")
        prev = label
    cmd += ["-filter_complex", ";".join(parts), "-map", prev]
    return cmd + ["-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", out]


def model_dir() -> str:
    """Yalniz diffusers komponentleri (~5.3 GB). Repo id ile from_pretrained kokdeki lazimsiz
    4.8 GB model.safetensors-u da yukleyir (2026-09-27 olculdu), ona gore lokal qovluq verilir."""
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # Xet yuklemesi ilisirdi
    from huggingface_hub import snapshot_download
    return snapshot_download(MODEL, allow_patterns=MODEL_FILES)


def generate(prompts: list[str], seed: int, out_dir: str) -> list[str]:
    import soundfile as sf
    import torch
    from diffusers import StableAudioPipeline

    t0 = time.time()
    pipe = StableAudioPipeline.from_pretrained(model_dir(), torch_dtype=torch.float16).to("cuda")
    print(f"[music] model {time.time() - t0:.0f} s", flush=True)
    paths = []
    for i, p in enumerate(prompts):
        t = time.time()
        audio = pipe(p, negative_prompt=NEGATIVE, num_inference_steps=STEPS, audio_end_in_s=CLIP_S,
                     generator=torch.Generator("cuda").manual_seed(seed + i)).audios[0]
        path = os.path.join(out_dir, f"part{i + 1:02d}.wav")
        sf.write(path, audio.T.float().cpu().numpy(), pipe.vae.sampling_rate)
        paths.append(path)
        print(f"[music] {i + 1}/{len(prompts)} {time.time() - t:.0f} s  {p[:60]}", flush=True)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--clips", type=int, default=CLIPS)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    ep = os.path.abspath(a.episode_dir)
    out = os.path.join(ep, OUT)
    if os.path.isfile(out) and not a.force:
        raise SystemExit(f"artiq movcuddur: {out}  (--force ile uzerine yaz)")
    slug = os.path.basename(ep)
    parts_dir = os.path.join(ep, "music_parts")
    os.makedirs(parts_dir, exist_ok=True)
    clips = generate(pick_prompts(slug, a.clips), _seed(slug), parts_dir)
    subprocess.run(crossfade_cmd(clips, out, FADE_S), check=True)
    shutil.rmtree(parts_dir, ignore_errors=True)
    print(f"[music] OK {track_seconds(len(clips), CLIP_S, FADE_S):.0f} s -> {out}")


if __name__ == "__main__":
    main()
