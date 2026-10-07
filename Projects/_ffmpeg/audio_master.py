"""Audio master (FAZA F 3.7): narration 24 kHz mono -> 48 kHz stereo, intro qeder gecikme,
musiqi ducking (sidechaincompress), iki kecidli loudnorm -14 LUFS / -1.5 dBTP."""
from __future__ import annotations

import json
import subprocess

SR = 48000
TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -1.5, 11.0
MUSIC_DB = -10          # pauzada musiqi seviyyesi; danisanda ducking ~8 dB de endirir
DUCK = "sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350"
_KEYS = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")


def mix_graph(narr_in: int, music_in: int | None, delay_s: float, total_s: float,
              sfx_in: int | None = None) -> str:
    """Faza 3.8: sfx_in (SFX treki, qlobal zaman) nitq + musiqi ile qarisir - loudnorm bundan SONRA."""
    ms = int(round(delay_s * 1000))
    narr = (f"[{narr_in}:a]aresample={SR},aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0,"
            f"adelay=delays={ms}:all=1,apad=whole_dur={total_s:.3f}")
    out = "[amix]" if sfx_in is None else "[nm]"
    if music_in is None:
        graph = narr + out
    else:
        graph = (f"{narr},asplit=2[nmain][nkey];"
                 f"[{music_in}:a]aresample={SR},aformat=channel_layouts=stereo,volume={MUSIC_DB}dB[mus];"
                 f"[mus][nkey]{DUCK}[duck];"
                 f"[nmain][duck]amix=inputs=2:duration=first:normalize=0{out}")
    if sfx_in is None:
        return graph
    return (graph + f";[{sfx_in}:a]aresample={SR},aformat=channel_layouts=stereo[fx];"
            "[nm][fx]amix=inputs=2:duration=first:normalize=0[amix]")


def _target() -> str:
    return f"I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"


def loudnorm_measure() -> str:
    return f"[amix]loudnorm={_target()}:print_format=json[aout]"


def parse_loudnorm_json(stderr: str) -> dict:
    start, end = stderr.rfind("{"), stderr.rfind("}")
    if start < 0 or end < start:
        raise ValueError("loudnorm JSON tapilmadi")
    data = json.loads(stderr[start:end + 1])
    missing = [k for k in _KEYS if k not in data]
    if missing:
        raise ValueError(f"loudnorm JSON natamamdir: {missing}")
    return data


def loudnorm_apply(m: dict) -> str:
    return (f"[amix]loudnorm={_target()}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true,aresample={SR}[aout]")


def measure(audio_inputs: list[str], graph: str, total_s: float) -> dict:
    """1-ci kecid: yalniz audio render olunur, loudnorm olcusu qaytarilir."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", *audio_inputs,
           "-filter_complex", f"{graph};{loudnorm_measure()}", "-map", "[aout]",
           "-t", f"{total_s:.3f}", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("loudnorm olcme ugursuz: " + r.stderr.strip()[-500:])
    return parse_loudnorm_json(r.stderr)
