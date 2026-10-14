"""ffmpeg: video_raw.mp4 + narration.wav + music.wav (dovr, danisiqda alcalir) -> <slug>.mp4, -14 LUFS.
Gain limiterden SONRA olculur ve hedefe catana qeder duzeldilir (limiter loudness-i yeyir; tek kecidli loudnorm
-16 verirdi), sonra deqiq gain + true-peak limiter ile yazilir.
Musiqi mecburidir (musiqisiz video YOX); cixis *.tmp.mp4-e yazilir, sonra adi deyisir."""
from __future__ import annotations

import json
import os
import re
import subprocess

import generate

MUSIC_DB = -20
TARGET_LUFS = -14.0
LIMIT = 0.79                     # ~ -2 dBTP: AAC-den sonra peak -1 dBFS-den asagi
TOLERANCE_LU, SOLVE_TRIES = 0.3, 5
FFMPEG_TIMEOUT_S = 3600            # ilisme qorumasi
MIX = (f"[2:a]volume={MUSIC_DB}dB[m];[m][1:a]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=400[md];"
       "[1:a][md]amix=inputs=2:duration=first:normalize=0")


def _inputs(ep: str) -> list[str]:
    return ["-i", os.path.join(ep, "video_raw.mp4"), "-i", os.path.join(ep, "narration.wav"),
            "-stream_loop", "-1", "-i", os.path.join(ep, "music.wav")]


def _chain(gain_db: float) -> str:
    return f"{MIX},volume={gain_db}dB,alimiter=limit={LIMIT}:attack=5:release=50:level=0"


def measure_cmd(ep: str, seconds: float, gain_db: float = 0.0) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-nostats", *_inputs(ep), "-filter_complex",
            f"{_chain(gain_db)},loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json[a]", "-map", "[a]",
            "-t", f"{seconds:.3f}", "-f", "null", "-"]


def parse_input_i(stderr: str) -> float:
    m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+|-inf)"', stderr)
    if not m or m.group(1) == "-inf":
        raise ValueError("loudness olculmedi (ffmpeg loudnorm cixisi)")
    return float(m.group(1))


def solve_gain(measure, tries: int = SOLVE_TRIES) -> float:
    """measure(gain) -> limiterden sonraki LUFS. Hedefe TOLERANCE_LU qeder yaxinlasana qeder duzelir."""
    gain = 0.0
    for _ in range(tries):
        err = TARGET_LUFS - measure(gain)
        if abs(err) <= TOLERANCE_LU:
            break
        gain = round(gain + err, 2)
    return gain


def cmd(ep: str, slug: str, seconds: float, gain_db: float, out: str | None = None) -> list[str]:
    out = out or os.path.join(ep, f"{slug}.mp4")
    graph = f"{_chain(gain_db)}[a]"
    return ["ffmpeg", "-y", "-loglevel", "error", *_inputs(ep), "-filter_complex", graph, "-map", "0:v",
            "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}", out]


def narration_seconds(ep: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        os.path.join(ep, "narration.wav")], capture_output=True, text=True, check=True, timeout=120)
    return float(r.stdout.strip())


def main(ep: str) -> None:
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        slug = json.load(f)["slug"]
    music = os.path.join(ep, "music.wav")
    if not os.path.isfile(music):
        raise FileNotFoundError(f"{music} yoxdur - musiqi merhelesi yeniden isleyir (--resume)")
    seconds = narration_seconds(ep)

    def measure(gain: float) -> float:
        r = subprocess.run(measure_cmd(ep, seconds, gain), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", check=True, timeout=FFMPEG_TIMEOUT_S)
        lufs = parse_input_i(r.stderr)
        print(f"  mix: gain {gain:+.2f} dB -> {lufs:.1f} LUFS", flush=True)
        return lufs
    gain = solve_gain(measure)
    out = os.path.join(ep, f"{slug}.mp4")
    subprocess.run(cmd(ep, slug, seconds, gain, out=generate.tmp_path(out)), check=True, timeout=FFMPEG_TIMEOUT_S)
    os.replace(generate.tmp_path(out), out)
