"""FAZA F pipeline merheleleri: emr, "bitib" yoxlamasi (fayl sistemi) ve sonraki yoxlama."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable

from PIL import Image

ROOT = r"C:\YouTubeAI"
PROJ = os.path.join(ROOT, "Projects")
PY = {"projects": os.path.join(PROJ, ".venv", "Scripts", "python.exe"),
      "tts": os.path.join(ROOT, "TTS", ".venv", "Scripts", "python.exe"),
      "whisper": os.path.join(ROOT, "Whisper", ".venv", "Scripts", "python.exe")}
BG_MIN = (1344, 768)
HD_MIN = (3840, 2160)
SRT_WORD_TOL = 0.05


@dataclass(frozen=True)
class Ctx:
    topic: str
    slug: str
    ep_dir: str
    words: int
    music: str | None
    min_seconds: float
    provider: str

    def p(self, *parts: str) -> str:
        return os.path.join(self.ep_dir, *parts)


@dataclass(frozen=True)
class Stage:
    name: str
    command: Callable[[Ctx, bool], list[str]]
    done: Callable[[Ctx], bool]
    verify: Callable[[Ctx], list[str]]
    needs_comfy: bool = False


def _proj(script: str, *args: str, force: bool = False) -> list[str]:
    return [PY["projects"], os.path.join(PROJ, script), *args] + (["--force"] if force else [])


def load_scenes(ctx: Ctx) -> list[dict]:
    if not os.path.isfile(ctx.p("scenes.json")):
        return []
    with open(ctx.p("scenes.json"), encoding="utf-8") as f:
        return json.load(f)["scenes"]


def numbered(ctx: Ctx, sub: str, ext: str = ".png") -> list[str]:
    return [ctx.p(sub, f"sc{i:02d}{ext}") for i in range(1, len(load_scenes(ctx)) + 1)]


def all_exist(paths: list[str]) -> bool:
    return bool(paths) and all(os.path.isfile(p) for p in paths)


def size_problems(paths: list[str], minimum: tuple[int, int]) -> list[str]:
    bad = []
    for p in paths:
        if not os.path.isfile(p):
            bad.append(f"{os.path.basename(p)} yoxdur")
            continue
        with Image.open(p) as im:
            if im.width < minimum[0] or im.height < minimum[1]:
                bad.append(f"{os.path.basename(p)} {im.width}x{im.height} < {minimum[0]}x{minimum[1]}")
    return bad


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def verify_script(ctx: Ctx) -> list[str]:
    from script_gen import check_headings
    missing = check_headings(_read(ctx.p("script.md")))
    return [f"catismayan basliqlar: {', '.join(missing)}"] if missing else []


def verify_scenes(ctx: Ctx) -> list[str]:
    bad = [i for i, s in enumerate(load_scenes(ctx), 1)
           if not (s.get("narration") and s.get("bg_prompt") and s.get("sprite_token"))]
    return [f"natamam sehneler: {bad}"] if bad else []


def verify_tts(ctx: Ctx) -> list[str]:
    missing = [os.path.basename(p) for p in numbered(ctx, "audio", ".wav") if not os.path.isfile(p)]
    return ([f"catismayan audio: {missing}"] if missing else []) + \
        ([] if os.path.isfile(ctx.p("narration.wav")) else ["narration.wav yoxdur"])


def spoken_extra_words(ctx: Ctx) -> int:
    """Skriptde olmayan, amma seslendirilen sozler: intro/outro kartlari + bolme basliqlari."""
    with open(ctx.p("scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    cards = " ".join((data.get("card_texts") or {}).values())
    titles = " ".join(s.get("spoken_title") or "" for s in data["scenes"])
    return len(cards.split()) + len(titles.split())


def verify_srt(ctx: Ctx) -> list[str]:
    from script_gen import word_count
    got = len(json.loads(_read(ctx.p("narration.words.json"))))
    want = word_count(_read(ctx.p("script.md"))) + spoken_extra_words(ctx)
    if abs(got - want) > SRT_WORD_TOL * want:
        return [f"whisper {got} soz, skript {want} soz (>{SRT_WORD_TOL:.0%} ferq)"]
    return []


def verify_video(ctx: Ctx) -> list[str]:
    from checks import final_video_problems
    return final_video_problems(ctx.p(f"{ctx.slug}.mp4"))


def verify_pack(ctx: Ctx) -> list[str]:
    from publish_pack import pack_problems
    return pack_problems(ctx.p("youtube"))


def _build_cmd(c: Ctx, f: bool) -> list[str]:
    return _proj("build_episode.py", c.ep_dir, "--srt", "--cards", "--require-hd") + \
        (["--music", c.music] if c.music else [])


STAGES: tuple[Stage, ...] = (
    Stage("script_gen",
          lambda c, f: _proj("script_gen.py", c.topic, "--slug", c.slug, "--words", str(c.words),
                             "--provider", c.provider, force=f),
          lambda c: os.path.isfile(c.p("script.md")), verify_script),
    Stage("scene_plan",
          lambda c, f: _proj("scene_plan.py", c.ep_dir, "--provider", c.provider, force=f),
          lambda c: os.path.isfile(c.p("scenes.json")), verify_scenes),
    Stage("render_bgs", lambda c, f: _proj("render_bgs.py", c.ep_dir, force=f),
          lambda c: all_exist(numbered(c, "bg")), lambda c: size_problems(numbered(c, "bg"), BG_MIN),
          needs_comfy=True),
    Stage("upscale_bgs", lambda c, f: _proj("upscale_bgs.py", c.ep_dir, force=f),
          lambda c: all_exist(numbered(c, "bg_hd")), lambda c: size_problems(numbered(c, "bg_hd"), HD_MIN),
          needs_comfy=True),
    Stage("tts_gen",
          lambda c, f: [PY["tts"], os.path.join(PROJ, "tts_gen.py"), c.ep_dir] + (["--force"] if f else []),
          lambda c: os.path.isfile(c.p("narration.wav")) and all_exist(numbered(c, "audio", ".wav"))
          and all_exist([c.p("audio", "intro.wav"), c.p("audio", "outro.wav")]),
          verify_tts),
    Stage("make_srt",
          lambda c, f: [PY["whisper"], os.path.join(ROOT, "Whisper", "make_srt.py"),
                        c.p("narration.wav"), c.p("narration")],
          lambda c: os.path.isfile(c.p("narration.srt")) and os.path.isfile(c.p("narration.words.json")),
          verify_srt),
    Stage("build_episode", _build_cmd, lambda c: os.path.isfile(c.p(f"{c.slug}.mp4")), verify_video),
    Stage("publish", lambda c, f: _proj("publish_pack.py", c.ep_dir, "--provider", c.provider),
          lambda c: os.path.isfile(c.p("youtube", "thumbnail.png")), verify_pack),
)


def stage_index(name: str) -> int:
    for i, s in enumerate(STAGES):
        if s.name == name:
            return i
    raise KeyError(name)
