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
import math
import re
import os
import shutil
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "_ffmpeg"))
from audio_master import loudnorm_apply, measure, mix_graph  # noqa: E402
from math_check import find_numbers  # noqa: E402
import config  # noqa: E402

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


CARD_OWLS = ("intro", "outro")   # render_owls.run_cards - giris/cixis kartinin movzu bayqusu

def cumulative_frames(durations: list[float], fps: int = FPS, offset_s: float = 0.0) -> list[int]:
    """Her klipin kadr sayi audio saatina gore: sərhədlər yuvarlaqlasdirilir, muddetler yox -
    300 sehnede de toplam surusme 1 kadrdan az qalir."""
    out, t = [], offset_s
    for d in durations:
        out.append(round((t + d) * fps) - round(t * fps))
        t += d
    return out


_NUM_WORDS = set(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million "
    "billion percent half quarter dollars cents".split())


def is_figure(word: str) -> bool:
    """Faza 3.9: reqem sozu (altyazida aktiv olmasa da accent renginde qalir)."""
    w = word.strip().lower().strip(".,!?;:\"'()")
    return bool(re.search(r"\d", w)) or any(p in _NUM_WORDS for p in w.split("-") if p)


def compact_words(words: list[dict]) -> list[dict]:
    """Whisper tokens without a leading space (".99" after " $39") continue the previous word.
    Faza 3.9: reqem sozleri `num: True` ile isarelenir (Captions.tsx accent renginde saxlayir)."""
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
    return [{**w, "num": True} if is_figure(w["w"]) else w for w in out]


REVEAL_LEAD = 4        # element sozden bir az evvel acilir - goz qulaqdan qabaq getsin
REVEAL_MIN = 0         # Faza 2.5: skelet 0-ci kadrdan gorunur - element oz sozunde acilir
REVEAL_TAIL = 20       # son element sehne bitmemis tam acilsin
REVEAL_GAP = 6
_WORD = re.compile(r"[a-z0-9]+")


def visual_elements(v: dict) -> list[dict]:
    """Chart-in ardicil acilan elementleri: {"value": reqem|None, "label": metn}."""
    k = v.get("kind")
    if k in ("bars", "line"):
        return list(v.get("items" if k == "bars" else "points") or [])
    if k == "compare":
        return [v.get("left") or {}, v.get("right") or {}]
    if k in ("ring", "counter"):
        return [{"value": v.get("value"), "label": v.get("label", "")}]
    if k == "equation":
        return [*(v.get("terms") or []), v.get("result") or {}]
    if k == "stats":                     # #57 data kartlari
        return list(v.get("cards") or [])
    # Faza 2: setir "evvel" deyeri deyilende, esik/bugunku deyer, zaman noqteleri, xerite acarlari
    if k == "table":
        return [{"value": r.get("before"), "label": r.get("label", "")} for r in v.get("rows") or []]
    if k == "threshold":
        cur = [v["current"]] if v.get("current") else []
        return [*cur, v.get("threshold") or {}]
    if k == "timeseries":
        return [{"value": p.get("value") if p.get("shown") else None, "label": p.get("label", "")}
                for p in v.get("points") or []]
    if k == "usmap":
        return list(v.get("keys") or [])
    if k == "waterfall":                 # #135 canli novler
        return [v.get("start") or {}, *(v.get("steps") or []), v.get("end") or {}]
    if k in ("gauge", "dotgrid"):
        tgt = [{"value": v["target"], "label": ""}] if v.get("target") is not None else []
        return [{"value": v.get("value"), "label": v.get("label", "")}, *tgt]
    if k in ("balance", "versus"):
        return [v.get("left") or {}, v.get("right") or {}]
    if k == "funnel":
        return list(v.get("stages") or [])
    if k == "timeline":
        return [{"label": e.get("label", "")} for e in v.get("events") or []]
    return [{"label": t} for t in v.get("steps" if k == "flow" else "points") or []]


def _cue(el: dict, words: list[dict], text: str, starts: list[int], after: int) -> int | None:
    """Elementin deyeri (ve ya etiketinin esas sozu) seslenen ilk sozun indeksi (after-dan sonra)."""
    val = el.get("value")
    if isinstance(val, (int, float)):
        for a, _, x in find_numbers(text):
            i = max(k for k, st in enumerate(starts) if st <= a)
            if i > after and abs(x - val) < 1e-6:
                return i
    keys = [t for t in _WORD.findall(str(el.get("label", "")).lower()) if len(t) >= 4]
    if keys:
        for i in range(after + 1, len(words)):
            if keys[0] in _WORD.findall(words[i]["w"].lower()):
                return i
    return None


def reveal_frames(v: dict, words: list[dict], start_s: float, frames: int, fps: int = FPS) -> list[int]:
    """#45: her element hemin reqem/fikir seslenende acilir; tapilmasa beraber addimla. Sira qorunur."""
    els = visual_elements(v)
    n = len(els)
    last = max(REVEAL_MIN, frames - REVEAL_TAIL)
    step = min(1.2 * fps, (0.55 * frames - REVEAL_MIN) / max(1, n - 1))
    out = [round(REVEAL_MIN + i * step) for i in range(n)]
    scene = [w for w in words if start_s <= w["s"] < start_s + frames / fps]
    starts, pos = [], 0
    for w in scene:
        starts.append(pos)
        pos += len(w["w"]) + 1
    text = " ".join(w["w"] for w in scene)
    after = -1
    for i, el in enumerate(els):
        j = _cue(el, scene, text, starts, after) if scene else None
        if j is not None:
            out[i] = round((scene[j]["s"] - start_s) * fps) - REVEAL_LEAD
            after = j
    for i in range(n):
        lo = REVEAL_MIN if i == 0 else out[i - 1] + REVEAL_GAP
        out[i] = min(max(out[i], lo), last)
    return out


EMPTY_WINDOW_S = 2.0      # Faza 2.5 QA: chart sehnesinin ilk 2 s-i
EMPTY_MAX = 0.03          # "yalniz basliq" kadrlarinin payi <= 3%
OVERLAY_MAX_S = 2.5       # Faza 2.7: foto sehnesinde reqem overlay-i <= 2.5 s, sehnede <= 1
_FIG_WORD = re.compile(r"^\$\d[\d,]*(?:\.\d+)?|^\d[\d,]*(?:\.\d+)?%")


def chart_empty_share(props: dict, fps: int = FPS) -> float:
    """Chart sehnelerinin ilk 2 s-inde hec bir element gorunmeyen ("yalniz basliq") kadrlarin payi.
    Skelet varsa kontur/oxlar/"—" 0-ci kadrdan gorunur -> 0."""
    total = empty = 0
    for s in props["scenes"]:
        if not s.get("visual"):
            continue
        window = min(s["frames"], round(EMPTY_WINDOW_S * fps))
        total += window
        if not s.get("skeleton"):
            empty += min(window, max(0, (s.get("reveal") or [window])[0]))
    return empty / total if total else 0.0


def number_overlay(words: list[dict], start_s: float, frames: int, fps: int = FPS) -> dict | None:
    """Foto sehnesinde danisilan ilk pul/faiz reqemi oz sozunde count-up overlay kimi (reference counter_events).
    Qutu bayqus ve altyazi zonasindan kenardadir (layout.OVERLAY_BOX)."""
    import layout
    end_s = start_s + frames / fps
    for w in words:
        if not start_s <= w["s"] < end_s:
            continue
        m = _FIG_WORD.match(w["w"])
        if not m:
            continue
        text = m.group(0)
        value = float(text.strip("$%").replace(",", ""))
        at = max(0, round((w["s"] - start_s) * fps) - REVEAL_LEAD)
        dur = min(round(OVERLAY_MAX_S * fps), frames - at)
        if dur < fps // 2:
            return None
        return {"value": value, "unit": "$" if text.startswith("$") else "%", "from": at, "frames": dur,
                "box": list(layout.OVERLAY_BOX)}
    return None


def load_words(ep: str) -> list[dict]:
    """#54: altyazi ssenaridən (captions.words.json, "$4,000"); kohne epizodda whisper sozleri."""
    for name in ("captions.words.json", "narration.words.json"):
        path = os.path.join(ep, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise SystemExit("altyazi sozleri yoxdur: captions.words.json / narration.words.json")


def pose_table(sizes: dict[str, tuple[int, int]]) -> dict[str, dict]:
    return {name: {"name": name, "w": w, "h": h, "height": POSE_HEIGHT.get(name, DEFAULT_HEIGHT),
                   "flippable": name not in NOT_FLIPPABLE} for name, (w, h) in sizes.items()}


def episode_props(data: dict, topic: str, words: list[dict], sizes: dict[str, tuple[int, int]],
                  scene_owls: dict[int, tuple[int, int]] | None = None,
                  card_owls: dict[str, tuple[int, int]] | None = None, slug: str | None = None,
                  history: str | None = None) -> dict:
    """Faza 3: slug verilibse hereket plani (motion.py: theme, variantlar, kecidler, Ken Burns) + vurgu.
    scene_owls: {sehne nomresi: (w, h)} - render_owls-in cekdiyi sehne bayqusu (owl/scNN.png).
    card_owls: {"intro"|"outro": (w, h)} - movzuya uygun giris/cixis bayqusu; yoxdursa kohne sprite."""
    scene_owls = scene_owls or {}
    card_owls = card_owls or {}
    scenes = data["scenes"]
    intro, outro = float(data["intro_seconds"]), float(data["outro_seconds"])
    frames = cumulative_frames([intro] + [float(s["duration"]) for s in scenes] + [outro])
    cw = compact_words(words)
    start = frames[0]
    out_scenes = []
    for i, (s, f) in enumerate(zip(scenes, frames[1:-1])):
        pose = s.get("sprite") if s.get("sprite") in VIDEO_POSES else FALLBACK_POSE
        if i + 1 in scene_owls:
            pose = f"sc{i + 1:02d}"
        visual = s.get("visual") or None
        reveal = reveal_frames(visual, cw, start / FPS, f) if visual else []
        overlay = None if visual or not config.NUMBER_OVERLAY else number_overlay(cw, start / FPS, f)  # 2.7
        start += f
        out_scenes.append({"frames": f, "bg": None if visual else f"bg/sc{i + 1:02d}.jpg", "visual": visual,
                           "reveal": reveal, "skeleton": bool(visual), "overlay": overlay,
                           "pose": pose,
                           # Bayqus hemise sagda sabit; fonu bos yeri solda qurulmus (kohne epizod)
                           # sehnelerde sekil guzgulenir - bos yer saga kecir, fonda yazi yoxdur
                           "side": "right", "flip": s.get("pos") == "left",
                           "motion": MOTIONS[i % len(MOTIONS)], "title": s.get("spoken_title"),
                           # #55: chart sehnesinde bolme adi lower-third deyil, chart basliginin ustunde kicik
                           # "kicker" - ikisi ust-uste dusmur
                           "lowerThird": bool(s.get("spoken_title")) and not visual,
                           "kicker": s.get("spoken_title") if visual else None})
    hook = (data.get("card_texts") or {}).get("intro")
    plan = None
    if slug and config.MOTION_VARIANTS:
        import motion
        desc = [{"kind": (sc["visual"] or {}).get("kind"), "section_start": bool(sc["title"])} for sc in out_scenes]
        plan = (motion.plan_with_history(slug, desc, history) if history else motion.plan_motion(slug, desc))
        out_scenes = [{**sc, "transition": m["transition"], "variant": m["variant"], "titleVariant": m["title"],
                       **({"motion": m["motion"]} if m["motion"] else {})}
                      for sc, m in zip(out_scenes, plan["scenes"])]
    props = {"fps": FPS, "topic": topic, "brand": BRAND, "audio": "narration.wav",
            # #56: giris kartinin seslendirdiyi hook cumlesi (reqem/paradoks) kartda da gorunur
            "hook": hook if hook and hook.strip() != topic.strip() else None,
            "introFrames": frames[0], "outroFrames": frames[-1],
            "introOwl": "intro" if "intro" in card_owls else "front",
            "outroOwl": "outro" if "outro" in card_owls else "three_q",
            # #46: kartlar sehne fotosunu tekrar gostermir - Remotion dizayn fonu (StudioBackdrop) cekir
            "introBg": None, "outroBg": None,
            "transitionFrames": TRANSITION_FRAMES, "scenes": out_scenes, "words": cw,
            "poses": {**pose_table(sizes), **{
                f"sc{n:02d}": {"name": f"sc{n:02d}", "w": w, "h": h, "height": DEFAULT_HEIGHT, "flippable": False}
                for n, (w, h) in scene_owls.items()}, **{
                name: {"name": name, "w": w, "h": h, "height": DEFAULT_HEIGHT, "flippable": False}
                for name, (w, h) in card_owls.items()}}}
    props = fit_chart_owls(props)
    if plan:
        import motion
        props["motion"] = {k: plan[k] for k in ("theme", "backdrop", "cold_open", "chart_title")}
        props["emphasis"] = motion.emphasis(props)
    return props


def sfx_enabled() -> bool:
    """Faza 5.1: SFX qati config.SFX ile (default ACIQ)."""
    return bool(config.SFX)


def fit_chart_owls(props: dict) -> dict:
    """#86: genis bayqus (lovhe/esya tutan, en > hundurluk) chart sehnesinde AREA-ya girib reqemi ortturdu.
    Chart sehnesinde bayqusun hundurluyu elə kicildilir ki, sol kenari AREA + bosluqdan sagda qalsin. Ayrica poz
    acari (`<poz>~chart`) eyni sekli gosterir - Owl.tsx deyismir, bayqus sabit ve sagdadir; foto sehneleri toxunulmur."""
    import layout
    max_w = layout.W - layout.OWL_MARGIN_X - (layout.AREA[0] + layout.AREA[2] + layout.CHART_OWL_GAP)
    poses = dict(props["poses"])
    scenes = []
    for s in props["scenes"]:
        pose = poses.get(s["pose"])
        width = pose["w"] / pose["h"] * pose["height"] * layout.H if pose else 0
        if not s.get("visual") or width <= max_w:
            scenes.append(s)
            continue
        key = f"{s['pose']}~chart"
        poses[key] = {**pose, "height": math.floor(max_w * pose["h"] / (pose["w"] * layout.H) * 1e4) / 1e4}
        scenes.append({**s, "pose": key})
    return {**props, "poses": poses, "scenes": scenes}


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


def card_owl_sizes(ep: str) -> dict[str, tuple[int, int]]:
    sizes = {}
    for name in CARD_OWLS:
        p = os.path.join(ep, "owl", f"{name}.png")
        if os.path.isfile(p):
            with Image.open(p) as im:
                sizes[name] = im.size
    return sizes


def prepare_public(ep: str, n_scenes: int, animated: set[int] = frozenset()) -> str:
    pub = os.path.join(ep, "remotion")
    for sub in ("bg", "owl", "fonts"):
        os.makedirs(os.path.join(pub, sub), exist_ok=True)
    for i in range(1, n_scenes + 1):
        dest = os.path.join(pub, "bg", f"sc{i:02d}.jpg")
        if i in animated:          # #45: analitik animasiya - foto yoxdur, kohne JPEG de qalmasin
            if os.path.isfile(dest):
                os.remove(dest)
            continue
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
    for name in card_owl_sizes(ep):
        shutil.copy2(os.path.join(ep, "owl", f"{name}.png"), os.path.join(pub, "owl", f"{name}.png"))
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
           audio_start: float = 0.0, sfx: str | None = None) -> None:
    """Video spec-e yeniden kodlanir, audio narration-dan: 48 kHz stereo, (musiqi), (SFX), -14 LUFS.
    Faza 3.8: SFX treki nitq ve musiqi ile qarisir, loudnorm ondan SONRA."""
    audio_in = ["-ss", f"{audio_start:.3f}", "-i", narration] + (["-stream_loop", "-1", "-i", music] if music else [])
    fx_idx = None
    if sfx:
        fx_idx = len([a for a in audio_in if a == "-i"])
        audio_in += ["-ss", f"{audio_start:.3f}", "-i", sfx]
    measured = measure(audio_in, mix_graph(0, 1 if music else None, 0.0, total_s, fx_idx), total_s)
    graph = ";".join([mix_graph(1, 2 if music else None, 0.0, total_s, fx_idx + 1 if fx_idx is not None else None),
                      loudnorm_apply(measured)])
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video, *audio_in,
           # Remotion JPEG kadrlari tam diapazon (yuvj420p) verir - TV diapazonuna cevrilir
           "-filter_complex", f"[0:v]scale=out_range=tv,format=yuv420p[v];{graph}", "-map", "[v]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", str(FPS),
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-t", f"{total_s:.3f}", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


SHEET_COLS = 3
SHEET_W = 640


def sheet_frames(props: dict) -> list[int]:
    """Faza 3 QA: cold open (giris kartinin ortasi), her bolmenin ilk ~1 s-i, qerar sehnesi (table/threshold)."""
    out = [props["introFrames"] // 2]
    start = props["introFrames"]
    for s in props["scenes"]:
        if s.get("title"):
            out.append(start + min(30, s["frames"] - 1))
        kind = (s.get("visual") or {}).get("kind")
        if kind in ("table", "threshold"):
            out.append(start + min(s["frames"] - 1, (s.get("reveal") or [0])[-1] + 20))
        start += s["frames"]
    return sorted(dict.fromkeys(out))


def motion_sheet(ep: str, props_path: str, pub: str, props: dict) -> str:
    """qa/motion_sheet.png: renderStill kadrlari bir cedvelde (vizual yoxlama ve epizodlar arasi muqayise)."""
    qa = os.path.join(ep, "qa")
    os.makedirs(qa, exist_ok=True)
    npx = "npx.cmd" if os.name == "nt" else "npx"
    stills = []
    for f in sheet_frames(props):
        png = os.path.join(qa, f"still_{f:06d}.png")
        subprocess.run([npx, "remotion", "still", "src/index.ts", "Episode", png, f"--props={props_path}",
                        f"--public-dir={pub}", f"--frame={f}", "--log=error"], cwd=REMOTION_DIR, check=True)
        stills.append(png)
    out = os.path.join(qa, "motion_sheet.png")
    rows = -(-len(stills) // SHEET_COLS)
    inputs = sum((["-i", p] for p in stills), [])
    pads = SHEET_COLS * rows - len(stills)
    graph = "".join(f"[{i}]scale={SHEET_W}:-1[s{i}];" for i in range(len(stills)))
    cells = [f"[s{i}]" for i in range(len(stills))]
    for k in range(pads):
        graph += f"color=c=black:s={SHEET_W}x{SHEET_W * 9 // 16}:d=1[p{k}];"
        cells.append(f"[p{k}]")
    layout = "|".join(f"{(i % SHEET_COLS) * SHEET_W}_{(i // SHEET_COLS) * SHEET_W * 9 // 16}" for i in range(len(cells)))
    graph += "".join(cells) + f"xstack=inputs={len(cells)}:layout={layout}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-frames:v", "1", out],
                   check=True)
    for p in stills:
        os.remove(p)
    return out


def motion_problems(props: dict, sims: list[float]) -> list[str]:
    """QA (qa/motion.json): son epizodlarla oxsarliq <= 50%, cold open typewriter, bos chart <= 3%."""
    import motion
    probs = []
    if max(sims, default=0.0) > motion.SIMILARITY_MAX:
        probs.append(f"hereket plani son epizodlara cox oxsardir ({max(sims):.0%} > 50%)")
    if (props.get("motion") or {}).get("cold_open") != "typewriter":
        probs.append("cold open-da typewriter tetbiq olunmayib")
    share = chart_empty_share(props) if props.get("scenes") else 0.0
    if share > EMPTY_MAX:
        probs.append(f"chart-larin ilk 2 s-inde bos kadr payi {share:.1%} > {EMPTY_MAX:.0%}")
    return probs


def write_qa(ep: str, name: str, data: dict) -> None:
    """qa/<name> - skriptin sha256-si ile (Faza 5.3: quality_gate kohne hesabati qebul etmir)."""
    import qa_stamp
    qa_stamp.write(ep, os.path.join("qa", name), data, indent=1)


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
    words = load_words(ep)
    if a.music and not os.path.isfile(a.music):
        raise SystemExit("musiqi tapilmadi: " + a.music)

    animated = {n for n, s in enumerate(data["scenes"], 1) if s.get("visual")}
    pub = prepare_public(ep, len(data["scenes"]), animated)
    history = os.path.join(os.path.dirname(ep), "_motion_history.json")
    props = episode_props(data, topic, words, sprite_sizes(), scene_owl_sizes(ep, len(data["scenes"])),
                          card_owl_sizes(ep), slug=slug, history=history)
    import motion
    import sfx as sfx_mod
    sims = [motion.similarity(motion.signature_of_props(props), h.get("signature") or [])
            for h in motion._load(history) if h.get("slug") != slug][-motion.HISTORY_WINDOW:]
    plan = props.get("motion") or {}           # MOTION_VARIANTS sondurulubse plan yoxdur (motion_problems tutur)
    write_qa(ep, "motion.json", {"theme": plan.get("theme"), "signature": motion.signature_of_props(props),
                                 "similarity_max": max(sims, default=0.0), "chart_empty_share": chart_empty_share(props),
                                 "typewriter_cold_open": plan.get("cold_open") == "typewriter",
                                 "emphasis": len(props.get("emphasis") or []), "problems": motion_problems(props, sims)})
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
    narration = os.path.join(ep, "narration.wav")
    evs = sfx_mod.events(props, compact_words(words))           # Faza 3.8
    track = sfx_mod.render_track(evs, sfx_mod.sounds(os.path.join(ep, "sfx")), total_frames / FPS,
                                 os.path.join(ep, "sfx_track.wav"), narration) if evs and sfx_enabled() else None
    write_qa(ep, "sfx.json", {"events": evs, "count": len(evs), "problems": sfx_mod.problems(evs, compact_words(words))})
    master(silent, narration, a.music, out, total_s, start, sfx=track)
    os.remove(silent)
    if not a.frames and plan:
        motion.remember(history, slug, {"theme": plan["theme"], "signature": motion.signature_of_props(props)})
        print("  motion sheet ->", motion_sheet(ep, props_path, pub, props), flush=True)
    print("OK ->", out)


if __name__ == "__main__":
    main()
