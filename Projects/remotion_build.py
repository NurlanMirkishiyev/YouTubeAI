"""scenes.json + narration -> Remotion ile final MP4 (build_episode.py-nin evezi).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\remotion_build.py Episodes\\<slug> [--music Music\\x.mp3]
                                     [--frames 0-299] [--out x.mp4]
Merheleler: public qovlugu (fon JPEG, bayqus, srift, narration) -> props.json -> `remotion render`
(sessiz, CRF 16) -> ffmpeg: video spec-e (H.264 High 4.1 yuv420p) + iki kecidli loudnorm -14 LUFS.
Niye Remotion: CSS transform sub-pixel hereket edir - ffmpeg zoompan tam piksele yuvarlaqlasdirir
ve hereket "dona-dona" gorunurdu; bayqus/altyazi/basliqlar kadr-kadr animasiya olunur.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "_ffmpeg"))
from audio_master import loudnorm_apply, measure, mix_graph  # noqa: E402

REMOTION_DIR = r"C:\YouTubeAI\Remotion"
SPRITE_DIR = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"
FONTS_DIR = r"C:\YouTubeAI\Assets\fonts"
FPS = 30
TRANSITION_FRAMES = 15
BG_SIZE = (2880, 1620)          # Ken Burns max zoom 1.12 -> 2150 px lazimdir
BG_QUALITY = 90
BRAND = "ELI5 Business"
VIDEO_POSES = ("front", "three_q", "side", "box", "chart")
POSE_HEIGHT = {"chart": 0.50, "box": 0.44}      # ekran hundurluyu payi; qalanlar DEFAULT
DEFAULT_HEIGHT = 0.46
NOT_FLIPPABLE = {"chart"}       # guzgulense qrafik "enir" kimi gorunur
MOTIONS = ("zoom_in", "pan_lr", "zoom_out", "pan_rl")
FALLBACK_POSE = "three_q"


def cumulative_frames(durations: list[float], fps: int = FPS, offset_s: float = 0.0) -> list[int]:
    """Her klipin kadr sayi audio saatina gore: sərhədlər yuvarlaqlasdirilir, muddetler yox -
    300 sehnede de toplam surusme 1 kadrdan az qalir."""
    out, t = [], offset_s
    for d in durations:
        out.append(round((t + d) * fps) - round(t * fps))
        t += d
    return out


def compact_words(words: list[dict]) -> list[dict]:
    """Whisper tokens without a leading space (".99" after " $39") continue the previous word."""
    out: list[dict] = []
    for w in words:
        text = w["word"]
        if not text.strip():
            continue
        start, end = round(float(w["start"]), 3), round(float(w["end"]), 3)
        if out and not text[0].isspace():
            prev = out[-1]
            out[-1] = {"w": prev["w"] + text.strip(), "s": prev["s"], "e": end}
        else:
            out.append({"w": text.strip(), "s": start, "e": end})
    return out


def pose_table(sizes: dict[str, tuple[int, int]]) -> dict[str, dict]:
    return {name: {"name": name, "w": w, "h": h, "height": POSE_HEIGHT.get(name, DEFAULT_HEIGHT),
                   "flippable": name not in NOT_FLIPPABLE} for name, (w, h) in sizes.items()}


def episode_props(data: dict, topic: str, words: list[dict], sizes: dict[str, tuple[int, int]],
                  scene_owls: dict[int, tuple[int, int]] | None = None) -> dict:
    """scene_owls: {sehne nomresi: (w, h)} - render_owls-in cekdiyi sehne bayqusu (owl/scNN.png)."""
    scene_owls = scene_owls or {}
    scenes = data["scenes"]
    intro, outro = float(data["intro_seconds"]), float(data["outro_seconds"])
    frames = cumulative_frames([intro] + [float(s["duration"]) for s in scenes] + [outro])
    out_scenes = []
    for i, (s, f) in enumerate(zip(scenes, frames[1:-1])):
        pose = s.get("sprite") if s.get("sprite") in VIDEO_POSES else FALLBACK_POSE
        if i + 1 in scene_owls:
            pose = f"sc{i + 1:02d}"
        out_scenes.append({"frames": f, "bg": f"bg/sc{i + 1:02d}.jpg", "pose": pose,
                           # Bayqus hemise sagda sabit; fonu bos yeri solda qurulmus (kohne epizod)
                           # sehnelerde sekil guzgulenir - bos yer saga kecir, fonda yazi yoxdur
                           "side": "right", "flip": s.get("pos") == "left",
                           "motion": MOTIONS[i % len(MOTIONS)], "title": s.get("spoken_title")})
    return {"fps": FPS, "topic": topic, "brand": BRAND, "audio": "narration.wav",
            "introFrames": frames[0], "outroFrames": frames[-1],
            "introBg": out_scenes[0]["bg"], "outroBg": out_scenes[-1]["bg"],
            "transitionFrames": TRANSITION_FRAMES, "scenes": out_scenes, "words": compact_words(words),
            "poses": {**pose_table(sizes), **{
                f"sc{n:02d}": {"name": f"sc{n:02d}", "w": w, "h": h, "height": DEFAULT_HEIGHT, "flippable": False}
                for n, (w, h) in scene_owls.items()}}}


def sprite_sizes() -> dict[str, tuple[int, int]]:
    sizes = {}
    for name in VIDEO_POSES:
        with Image.open(os.path.join(SPRITE_DIR, f"{name}.png")) as im:
            sizes[name] = im.size
    return sizes


def scene_owl_sizes(ep: str, n_scenes: int) -> dict[int, tuple[int, int]]:
    sizes = {}
    for n in range(1, n_scenes + 1):
        p = os.path.join(ep, "owl", f"sc{n:02d}.png")
        if os.path.isfile(p):
            with Image.open(p) as im:
                sizes[n] = im.size
    return sizes


def prepare_public(ep: str, n_scenes: int) -> str:
    pub = os.path.join(ep, "remotion")
    for sub in ("bg", "owl", "fonts"):
        os.makedirs(os.path.join(pub, sub), exist_ok=True)
    for i in range(1, n_scenes + 1):
        dest = os.path.join(pub, "bg", f"sc{i:02d}.jpg")
        src = next((p for p in (os.path.join(ep, "bg_hd", f"sc{i:02d}.png"), os.path.join(ep, "bg", f"sc{i:02d}.png"))
                    if os.path.isfile(p)), None)
        if src is None:
            raise SystemExit(f"fon yoxdur: sc{i:02d} - once render_bgs/upscale_bgs")
        if os.path.isfile(dest) and os.path.getmtime(dest) >= os.path.getmtime(src):
            continue
        with Image.open(src) as im:
            im.convert("RGB").resize(BG_SIZE, Image.LANCZOS).save(dest, quality=BG_QUALITY)
    for name in VIDEO_POSES:
        shutil.copy2(os.path.join(SPRITE_DIR, f"{name}.png"), os.path.join(pub, "owl", f"{name}.png"))
    for n in scene_owl_sizes(ep, n_scenes):
        shutil.copy2(os.path.join(ep, "owl", f"sc{n:02d}.png"), os.path.join(pub, "owl", f"sc{n:02d}.png"))
    for f in os.listdir(FONTS_DIR):
        if f.endswith(".ttf"):
            shutil.copy2(os.path.join(FONTS_DIR, f), os.path.join(pub, "fonts", f))
    shutil.copy2(os.path.join(ep, "narration.wav"), os.path.join(pub, "narration.wav"))
    return pub


def render_cmd(props: str, pub: str, out: str, frames: str | None) -> list[str]:
    npx = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", "Episode", out, f"--props={props}",
           f"--public-dir={pub}", "--muted", "--codec=h264", "--crf=16", "--log=info"]
    return cmd + ([f"--frames={frames}"] if frames else [])


def master(video: str, narration: str, music: str | None, out: str, total_s: float,
           audio_start: float = 0.0) -> None:
    """Video spec-e yeniden kodlanir, audio narration-dan: 48 kHz stereo, (musiqi), -14 LUFS."""
    audio_in = ["-ss", f"{audio_start:.3f}", "-i", narration] + (["-stream_loop", "-1", "-i", music] if music else [])
    measured = measure(audio_in, mix_graph(0, 1 if music else None, 0.0, total_s), total_s)
    graph = ";".join([mix_graph(1, 2 if music else None, 0.0, total_s), loudnorm_apply(measured)])
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video, *audio_in,
           # Remotion JPEG kadrlari tam diapazon (yuvj420p) verir - TV diapazonuna cevrilir
           "-filter_complex", f"[0:v]scale=out_range=tv,format=yuv420p[v];{graph}", "-map", "[v]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", str(FPS),
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-t", f"{total_s:.3f}", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--music")
    ap.add_argument("--out")
    ap.add_argument("--frames", help="yalniz bu kadr araligi (yoxlama ucun), mes. 0-299")
    a = ap.parse_args()
    ep = os.path.abspath(a.episode_dir)
    slug = os.path.basename(ep)
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    if "intro_seconds" not in data:
        raise SystemExit("scenes.json-da intro_seconds yoxdur - tts_gen.py --force ile yeniden seslendir")
    with open(os.path.join(ep, "meta.json"), encoding="utf-8") as f:
        topic = json.load(f)["topic"]
    with open(os.path.join(ep, "narration.words.json"), encoding="utf-8") as f:
        words = json.load(f)
    if a.music and not os.path.isfile(a.music):
        raise SystemExit("musiqi tapilmadi: " + a.music)

    pub = prepare_public(ep, len(data["scenes"]))
    props = episode_props(data, topic, words, sprite_sizes(), scene_owl_sizes(ep, len(data["scenes"])))
    props_path = os.path.join(ep, "remotion_props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)
    total_frames = props["introFrames"] + sum(s["frames"] for s in props["scenes"]) + props["outroFrames"]
    print(f"[R] {len(props['scenes'])} sehne, {total_frames} kadr ({total_frames / FPS / 60:.2f} deq)", flush=True)

    silent = os.path.join(ep, "remotion_video.mp4")
    subprocess.run(render_cmd(props_path, pub, silent, a.frames), cwd=REMOTION_DIR, check=True)
    out = a.out or os.path.join(ep, f"{slug}.mp4")
    total_s, start = total_frames / FPS, 0.0
    if a.frames:
        lo, hi = (int(x) for x in a.frames.split("-"))
        total_s, start = (hi - lo + 1) / FPS, lo / FPS
    master(silent, os.path.join(ep, "narration.wav"), a.music, out, total_s, start)
    os.remove(silent)
    print("OK ->", out)


if __name__ == "__main__":
    main()
