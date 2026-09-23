"""ffprobe / ffmpeg esasli yoxlamalar - FAZA F qebul meyarlari A2, A3, A4, A8."""
from __future__ import annotations

import json
import re
import subprocess

TARGET_LUFS = -14.0
LUFS_TOL = 1.0
MAX_DRIFT_S = 0.2
EXPECT_VIDEO = {"codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p",
                "level": 41, "width": 1920, "height": 1080, "r_frame_rate": "30/1"}
EXPECT_AUDIO = {"codec_name": "aac", "sample_rate": "48000", "channels": 2}


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def ffprobe(path: str) -> dict:
    r = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe ugursuz: {path}: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def duration(path: str) -> float:
    return float(ffprobe(path)["format"]["duration"])


def _stream(info: dict, kind: str) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == kind), None)


def _diff(stream: dict, expect: dict, label: str) -> list[str]:
    return [f"{label} {k}={stream.get(k)!r} (gozlenilen {v!r})"
            for k, v in expect.items() if stream.get(k) != v]


def video_problems(info: dict) -> list[str]:
    v = _stream(info, "video")
    return ["video stream yoxdur"] if v is None else _diff(v, EXPECT_VIDEO, "video")


def audio_problems(info: dict) -> list[str]:
    a = _stream(info, "audio")
    return ["audio stream yoxdur"] if a is None else _diff(a, EXPECT_AUDIO, "audio")


def av_drift(info: dict) -> float:
    v, a = _stream(info, "video"), _stream(info, "audio")
    return abs(float(v["duration"]) - float(a["duration"]))


def parse_ebur128_integrated(stderr: str) -> float:
    """ebur128 her 100 ms-de 'I: ... LUFS' yazir; xulase en sondadir."""
    found = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", stderr)
    if not found:
        raise ValueError("ebur128 xulasesi tapilmadi")
    return float(found[-1])


def integrated_lufs(path: str) -> float:
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a",
              "-af", "ebur128", "-f", "null", "-"])
    return parse_ebur128_integrated(r.stderr)


def decode_errors(path: str) -> str:
    """Bos setir = tam dekod xetasiz (A8)."""
    r = _run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"])
    return r.stderr.strip() or (f"exit {r.returncode}" if r.returncode else "")


def final_video_problems(mp4: str) -> list[str]:
    info = ffprobe(mp4)
    problems = video_problems(info) + audio_problems(info)
    if not problems:
        drift = av_drift(info)
        if drift > MAX_DRIFT_S:
            problems.append(f"A/V drift {drift:.2f}s > {MAX_DRIFT_S}s")
        lufs = integrated_lufs(mp4)
        if abs(lufs - TARGET_LUFS) > LUFS_TOL:
            problems.append(f"loudness {lufs:.1f} LUFS (gozlenilen {TARGET_LUFS}±{LUFS_TOL})")
    errors = decode_errors(mp4)
    if errors:
        problems.append("dekod xetasi: " + errors[:300])
    return problems
