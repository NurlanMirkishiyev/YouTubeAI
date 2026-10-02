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
import re
import shutil
import subprocess
import time
from typing import Callable

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
TAIL_DB = -35  # klip sonu reverb quyrugu ile -50 dB-e qeder 4 s sonur - dovr noqtesinde desik olurdu
END_FADE_S = 0.4
# Reyestr #44 (2026-10-03): model klipin ORTASINDA da ~1 s pauza verir -> danisiq pauzasi ile tam sukut
GAP_DB = -40
GAP_S = 0.4
MAX_TRIES = 3
SEED_STEP = 1000
NEGATIVE = "vocals, singing, speech, voice, low quality, distortion, noise, harsh, loud drums"
STYLES = (
    "Light upbeat corporate background music, soft acoustic guitar, warm piano, gentle claps, positive, "
    "110 BPM, instrumental, no vocals",
    "Calm lo-fi explainer background, mellow electric piano, soft bass, light brushed drums, curious and "
    "friendly, 90 BPM, instrumental",
    # istifadeci (2026-09-28): usaq videosu kimi gorunmesin - usaq/oyun musiqisi stilleri cixarildi
    "Modern minimal documentary background, soft piano, warm cello, subtle pulse, confident and focused, "
    "100 BPM, instrumental",
    "Sleek corporate ambient, deep synth bass, soft electric piano chords, steady light beat, professional, "
    "105 BPM, instrumental",
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
    head = f"silenceremove=start_periods=1:start_threshold={SILENCE_DB}dB:start_silence=0.05"
    tail = f"silenceremove=start_periods=1:start_threshold={TAIL_DB}dB:start_silence=0.05"
    parts = [f"[{i}:a]{head},areverse,{tail},areverse,"
             f"loudnorm=I={CLIP_LUFS}:TP={CLIP_TP}:LRA=11[n{i}]" for i in range(len(clips))]
    prev = "[n0]"
    for i in range(1, len(clips)):
        label = f"[x{i}]"
        parts.append(f"{prev}[n{i}]acrossfade=d={fade}:c1=tri:c2=tri{label}")
        prev = label
    parts.append(f"{prev}areverse,afade=t=in:d={END_FADE_S},areverse[out]")  # dovr ucun kesik yox
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]"]
    return cmd + ["-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", out]


def parse_gaps(log: str, track_s: float) -> list[tuple[float, float]]:
    """silencedetect loqundan daxili bosluqlar; trekin sonundaki fade-out sayilmir."""
    starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", log)]
    durs = [float(m) for m in re.findall(r"silence_duration: ([\d.]+)", log)]
    return [(s, d) for s, d in zip(starts, durs) if s + d < track_s - 0.05]


def track_gaps(path: str) -> list[tuple[float, float]]:
    import soundfile as sf
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                          f"silencedetect=n={GAP_DB}dB:d={GAP_S}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return parse_gaps(log, sf.info(path).duration)


def build_track(seed: int, out: str, make: Callable[[int, str], None],
                gaps: Callable[[str], list[tuple[float, float]]]) -> int:
    """Daxili bosluqsuz trek alinana qeder yeni seed ile (MAX_TRIES); alinmasa en az sukutlu qalir."""
    best: tuple[float, str] | None = None
    for i in range(MAX_TRIES):
        tmp = f"{out}.try{i}.wav"
        make(seed + i * SEED_STEP, tmp)
        found = gaps(tmp)
        total = sum(d for _, d in found)
        print(f"[music] cehd {i + 1}: daxili bosluq {found or 'yoxdur'}", flush=True)
        if best is None or total < best[0]:
            if best:
                os.remove(best[1])
            best = (total, tmp)
        else:
            os.remove(tmp)
        if not found:
            break
    os.replace(best[1], out)
    return i + 1


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
    prompts = pick_prompts(slug, a.clips)

    def make(seed: int, path: str) -> None:
        clips = generate(prompts, seed, parts_dir)
        subprocess.run(crossfade_cmd(clips, path, FADE_S), check=True)

    tries = build_track(_seed(slug), out, make, track_gaps)
    shutil.rmtree(parts_dir, ignore_errors=True)
    print(f"[music] OK {track_seconds(a.clips, CLIP_S, FADE_S):.0f} s, {tries} cehd -> {out}")


if __name__ == "__main__":
    main()
