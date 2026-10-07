"""Faza 3.8 (istifadeci 2026-10-07; ideya: docs/referance/video_yarat_v4.py make_sfx/make_ticks).
SFX qati: whoosh, pop, tick, boom ffmpeg lavfi ile yaradilir (pulsuz, lisenziyasiz); Projects/sfx/<ad>.wav|mp3
varsa istifadeci fayli secilir. Hadiseler (remotion props-dan):
  bolme kecidi -> whoosh; reqem/kart reveal -> pop + qisa tick (pop_tick); timeseries enisi -> boom.
Sixliq: her 10 s-de <= 2 (prioritet boom > whoosh > pop_tick). Nitq sozunun ortasina dusmur (sozun evveline
cekilir). Seviyye: nitqin orta seviyyesinden >= 18 dB asagi. Trek audio_master-de nitq ve musiqi ile qarisir,
SONRA mövcud iki kecidli -14 LUFS loudnorm.
"""
from __future__ import annotations

import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
USER_DIR = os.path.join(HERE, "sfx")
SR = 48000
WINDOW_S = 10.0
MAX_PER_WINDOW = 2
BELOW_SPEECH_DB = 18.0
MARGIN_DB = 3.0                 # olcme xetasina ehtiyat
PRIORITY = {"boom": 0, "whoosh": 1, "pop_tick": 2}
WHOOSH_LEAD_S = 0.25            # whoosh kecidden bir az evvel baslayir

LAVFI = {
    "whoosh": ("anoisesrc=d=0.9:c=pink:a=0.7",
               "highpass=f=300,lowpass=f=5000,afade=t=in:d=0.5:curve=exp,afade=t=out:st=0.5:d=0.4"),
    "boom": ("aevalsrc=0.9*sin(2*PI*(58-22*t)*t)*exp(-1.6*t)+0.25*(random(0)*2-1)*exp(-14*t):d=2.8:s=44100",
             "lowpass=f=900"),
    "pop": ("anoisesrc=d=0.35:c=pink:a=0.5", "highpass=f=600,lowpass=f=6000,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.23"),
    "tick": ("aevalsrc=0.7*(random(0)*2-1)*lt(mod(t\\,0.06)\\,0.012):d=0.2:s=44100", "highpass=f=1800"),
}


def _gen(name: str, out: str) -> None:
    src, af = LAVFI[name]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-af",
                    f"{af},aformat=sample_rates={SR}:channel_layouts=stereo", out], check=True)


def sounds(gen_dir: str, user_dir: str = USER_DIR) -> dict[str, str]:
    """{ad: fayl}; istifadeci fayli (wav/mp3) ustundur. pop_tick = pop + 0.12 s sonra tick."""
    os.makedirs(gen_dir, exist_ok=True)
    out: dict[str, str] = {}
    for name in LAVFI:
        user = next((os.path.join(user_dir, name + ext) for ext in (".wav", ".mp3")
                     if os.path.isfile(os.path.join(user_dir, name + ext))), None)
        if user:
            out[name] = user
            continue
        path = os.path.join(gen_dir, name + ".wav")
        if not os.path.isfile(path):
            _gen(name, path)
        out[name] = path
    combo = os.path.join(gen_dir, "pop_tick.wav")
    if not os.path.isfile(combo) or any(os.path.getmtime(out[k]) > os.path.getmtime(combo) for k in ("pop", "tick")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out["pop"], "-i", out["tick"], "-filter_complex",
                        f"[0:a]aresample={SR}[a];[1:a]aresample={SR},adelay=delays=120:all=1[b];"
                        "[a][b]amix=inputs=2:normalize=0", combo], check=True)
    out["pop_tick"] = combo
    return out


def snap(t: float, words: list[dict]) -> float:
    """Sozun ortasina dusen hadise o sozun evveline cekilir."""
    for w in words:
        if w["s"] < t < w["e"]:
            return float(w["s"])
    return t


def events(props: dict, words: list[dict]) -> list[dict]:
    """Props-dan SFX hadiseleri (saniye, qlobal zaman), sixliq limiti ve soz sinxronu ile."""
    fps = props["fps"]
    start = props["introFrames"]
    raw: list[dict] = []
    for i, s in enumerate(props["scenes"]):
        if s.get("title") and i:
            raw.append({"t": max(0.0, start / fps - WHOOSH_LEAD_S), "name": "whoosh"})
        v = s.get("visual")
        rev = s.get("reveal") or []
        if v:
            for f in rev:
                raw.append({"t": (start + f) / fps, "name": "pop_tick"})
            for seg in v.get("segments") or []:
                if seg.get("down") and seg["to"] < len(rev):
                    raw.append({"t": (start + rev[seg["to"]]) / fps, "name": "boom"})
                    break
        start += s["frames"]
    raw = [{**e, "t": round(snap(e["t"], words), 3)} for e in raw]
    kept: list[dict] = []
    for e in sorted(raw, key=lambda e: (PRIORITY[e["name"]], e["t"])):
        ts = sorted([k["t"] for k in kept] + [e["t"]])
        # her 10 s-lik pencerede <= 2: hec bir 3 ardicil hadise 10 s-den qisa araliqda olmur
        if all(ts[i + MAX_PER_WINDOW] - ts[i] >= WINDOW_S for i in range(len(ts) - MAX_PER_WINDOW)):
            kept.append(e)
    return sorted(kept, key=lambda e: e["t"])


def _mean_db(path: str) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return float(r.stderr.split("mean_volume:")[1].split("dB")[0])
    except (IndexError, ValueError) as e:
        raise RuntimeError(f"seviyye olculmedi: {path}") from e


def render_track(evs: list[dict], snd: dict[str, str], total_s: float, out: str, narration: str) -> str:
    """Hadiseleri bir stereo trekde yerlesdirir; her ses nitqin orta seviyyesinden BELOW+MARGIN dB asagi."""
    speech = _mean_db(narration)
    inputs: list[str] = ["-f", "lavfi", "-t", f"{total_s:.3f}", "-i", f"anullsrc=r={SR}:cl=stereo"]
    parts, labels = [], ["[0:a]"]
    for k, e in enumerate(evs, start=1):
        path = snd[e["name"]]
        gain = speech - BELOW_SPEECH_DB - MARGIN_DB - _mean_db(path)
        inputs += ["-i", path]
        parts.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo,volume={gain:.2f}dB,"
                     f"adelay=delays={int(round(e['t'] * 1000))}:all=1[s{k}]")
        labels.append(f"[s{k}]")
    graph = ";".join(parts + ["".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0[out]"])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
                    "-t", f"{total_s:.3f}", out], check=True)
    return out


def problems(evs: list[dict], words: list[dict]) -> list[str]:
    """QA (qa/sfx.json): hadise var, 10 s-de <= 2, heç biri sozun ortasinda deyil."""
    if not evs:
        return ["SFX hadisesi yoxdur"]
    probs = []
    ts = sorted(e["t"] for e in evs)
    if any(ts[i + MAX_PER_WINDOW] - ts[i] < WINDOW_S for i in range(len(ts) - MAX_PER_WINDOW)):
        probs.append(f"SFX sixliq limiti asilib: 10 s-de {MAX_PER_WINDOW}-den cox hadise")
    mid = [e["t"] for e in evs if any(w["s"] < e["t"] < w["e"] for w in words)]
    if mid:
        probs.append(f"SFX sozun ortasina dusur: {mid[:5]}")
    return probs
