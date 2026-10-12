# FAZA F / Faza 1 — Automation + Keyfiyyət Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python run.py "Mövzu"` → ≥ 10 dəqiqəlik, YouTube-a hazır MP4 + `youtube/` paketi; personaj kəskin və yerə oturmuş, fon 5K mənbədən, peşəkar subtitr/keçid/audio.

**Architecture:** Mövcud mərhələ skriptləri (`script_gen`, `scene_plan`, `render_bgs`, `tts_gen`, `make_srt`, `build_episode`) öz venv-ləri ilə subprocess kimi çağırılır; yeni `pipeline.py` state.json + fayl sistemi əsasında resume edir. Keyfiyyət işi kiçik, test edilə bilən modullara bölünür: `motion.py` (Ken Burns/keçid), `audio_master.py` (48 kHz stereo, ducking, iki keçidli loudnorm), `cards.py` (intro/outro/lower-third/thumbnail), `upscale.py` (ComfyUI upscale modeli), `timeline.py` (müddət/chapter riyaziyyatı). `montage.py` bunları birləşdirir.

**Tech Stack:** Python 3.11 (`Projects\.venv`, Pillow, numpy, pytest), ffmpeg 8.1 (gyan full build), ComfyUI (core `UpscaleModelLoader`/`ImageUpscaleWithModel` node-ları), Kokoro TTS (TTS\.venv), faster-whisper (Whisper\.venv), OpenAI `gpt-4o-mini` (`Projects/llm.py`, stdlib).

**Spec:** `docs/superpowers/specs/2026-09-23-faza-f-automation-design.md`

## Global Constraints

- Video: 1920×1080 @ 30 fps, H.264 **High**, `yuv420p`, level **4.1** (`-pix_fmt yuv420p -profile:v high -level 4.1` — heç vaxt çıxarılmır).
- Audio: AAC **48 kHz stereo**, integrated loudness **−14 ±1 LUFS**, true peak −1.5 dBTP.
- A/V drift < **0.2 s**. Narration ≥ **600 s** (sərt qayda; `--min-seconds` yalnız inteqrasiya testi üçün aşağı salınır).
- Sprite heç vaxt böyüdülmür (A5): ekran hündürlüyü default **0.42** × 1080 = 454 px, HD sprite mənbəyi ≥ 454 px.
- Fon Ken Burns-a ≥ 3840×2160 mənbədən girir (A6); `bg_hd/` şəkilləri **5120×2880**.
- Personaj heç vaxt generativ çəkilmir — yalnız sprite overlay.
- Sprite mövqeyi koddan (`scene_plan.assign_positions`), LLM-dən yox.
- `XFADE = 0.5`; montaj uzunluğu `total = Σd − XFADE·(n−1)`; son klipdən başqa hər klipə `+XFADE` əlavə olunur.
- Kokoro sürəti **199 wpm** (`script_gen.WPM`). Default `--words 2150`.
- Windows: Git Bash; ComfyUI `.bat` ilə yox, birbaşa `ComfyUI/.venv/Scripts/python.exe main.py --listen 127.0.0.1 --port 8188 --lowvram`.
- Python interpreterləri: Projects → `C:\YouTubeAI\Projects\.venv\Scripts\python.exe`; TTS → `C:\YouTubeAI\TTS\.venv\Scripts\python.exe`; Whisper → `C:\YouTubeAI\Whisper\.venv\Scripts\python.exe`. PATH-dakı `python` (hermes venv) **istifadə olunmur**.
- Kod üslubu: mövcud faylların üslubu — ASCII Azərbaycanca şərhlər/mesajlar, `from __future__ import annotations`, funksiyalar < 50 sətir, fayllar < 800 sətir.
- Faylları Edit tool ilə düzəlt; heredoc `str.replace` səssiz uğursuz olur (progress.md "yanlış yollar").
- Placeholder musiqi (`Music/_placeholder_tone.wav`) **istifadə olunmur**; musiqi verilməyibsə video musiqisiz çıxır və xəbərdarlıq yazılır.

## Spec-dən dəqiqləşdirmələr (plan yazılarkən aşkarlandı)

1. **"sistem python" = `Projects\.venv`** (PATH-dakı python hermes venv-dir, Pillow yoxdur).
2. **Subtitr ölçüsü:** libass SRT üçün `PlayResY=288` götürür → `FontSize=13` ≈ 49 px, `MarginV=24` ≈ 90 px (spec-dəki "15 / 70" 288-miqyasında deyil). `BorderStyle=3` qutusunu libass **OutlineColour** ilə çəkir → `OutlineColour=&H80000000`.
3. **Lower-third yuxarı-solda** (spec: sol-aşağı). Səbəb: sprite `left` mövqeyində sol-aşağı küncü tutur, subtitr aşağı-mərkəzdədir — toqquşma olmasın.
4. **Uzunluq qaydası iki qapılı:** (a) `script_gen`-dən dərhal sonra söz sayı qapısı (ucuz; `--extend` 2 cəhdə qədər); (b) TTS-dən sonra real saniyə qapısı — qısa olarsa skript uzadılır, `scenes.json`/`bg`/`bg_hd`/`audio` silinir və `scene_plan`-dan yenidən başlanır (səhnə nömrələri sürüşdüyü üçün köhnə fonlar təkrar istifadə edilə bilməz).
5. **comfy_up** ayrıca state mərhələsi deyil — `ComfyGuard` ComfyUI-ni `render_bgs`-dən əvvəl qaldırır, `upscale_bgs`-dən sonra (özü qaldırıbsa) dayandırır.
6. **Filter qrafı fayla yazılır** (`-/filter_complex <fayl>`, ffmpeg ≥ 7): 30+ səhnə × 4 giriş Windows-un 32 767 simvolluq əmr limitini keçir.
7. **Intro 4 s < YouTube-un 10 s minimum chapter-i** → ilk chapter `00:00 Hook` (intro Hook-a daxildir).
8. **Git:** layihə git repo deyil → Task 0-da `git init` + `.gitignore` (böyük/generasiya olunan qovluqlar və `.env` xaric).

## Fayl strukturu

| Fayl | Məsuliyyət |
|---|---|
| `.gitignore`, `pytest.ini` | yeni — repo və test konfiqurasiyası |
| `run.py` | yeni — wrapper, özünü `Projects\.venv` ilə yenidən işə salır |
| `Projects/tests/conftest.py` + `test_*.py` | yeni — unit testlər |
| `Projects/checks.py` | yeni — ffprobe/ebur128/decode yoxlamaları (A2–A4, A8) |
| `Projects/timeline.py` | yeni — `plan_timeline`, `shift_srt`, `section_starts`, `first_of_section`, `display_title`, `INTRO_S`, `OUTRO_S` |
| `Projects/imaging.py` | yeni — `cover_box`, `fit_cover` |
| `Projects/_ffmpeg/motion.py` | yeni — Ken Burns ifadələri, `motion_for`, `transitions_for` |
| `Projects/_ffmpeg/audio_master.py` | yeni — `mix_graph`, loudnorm ölçmə/tətbiq |
| `Projects/_ffmpeg/montage.py` | **yenidən yazılır** — Clip/Sprite, kölgə, lower-third, keçidlər, subtitr stili, audio master |
| `Projects/upscale.py` | yeni — ComfyUI upscale klienti |
| `Projects/_workflows/upscale_4x_api.json` | yeni |
| `Projects/upscale_bgs.py` | yeni — `bg/` → `bg_hd/` 5120×2880 |
| `Projects/sprites/upscale_sprites.py` | yeni — `sprites/` → `sprites_hd/` (+ `_shadow.png`) |
| `Projects/cards.py` | yeni — intro/outro/lower-third/thumbnail |
| `Projects/build_episode.py` | **dəyişir** — `bg_hd`, `--cards`, `--require-hd`, keçidlər, SRT sürüşməsi |
| `Projects/script_gen.py` | **dəyişir** — `--extend`, `words_to_add`, `words_for_seconds`, default 2150, meta-da `domains` |
| `Projects/publish_pack.py` | yeni — YouTube paketi |
| `Projects/state.py` | yeni — state.json (atomik, immutable yeniləmə) |
| `Projects/comfy.py` | yeni — ComfyUI start/stop/wait + `ComfyGuard` |
| `Projects/stages.py` | yeni — `Ctx`, `Stage`, `STAGES`, done/verify funksiyaları |
| `Projects/pipeline.py` | yeni — orchestrator, uzunluq qapıları, CLI |
| `Assets/fonts/Montserrat-SemiBold.ttf`, `Montserrat-ExtraBold.ttf` | yeni (OFL) |
| `Models/upscale_models/4x-UltraSharp.pth`, `RealESRGAN_x4plus_anime_6B.pth` | yeni (git-ə daxil deyil) |

Test əmri (hər task-da): `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe -m pytest -q`

---

### Task 0: Repo, pytest, test skeleti

**Files:**
- Create: `.gitignore`, `pytest.ini`, `Projects/tests/__init__.py` (boş), `Projects/tests/conftest.py`, `Projects/tests/test_smoke.py`

**Interfaces:**
- Produces: `Projects`, `Projects/_ffmpeg`, `Projects/sprites` `sys.path`-dədir → testlər `import timeline`, `import motion`, `import upscale_sprites` yaza bilir.

- [ ] **Step 1: pytest qur**

Run: `uv pip install --python /c/YouTubeAI/Projects/.venv/Scripts/python.exe pytest`
Expected: `Installed ... pytest-...`

- [ ] **Step 2: `.gitignore` yaz**

```gitignore
# boyuk / generasiya olunan
ComfyUI/
Models/
Episodes/
Output/
Temp/
Music/
Character/ELI5_Owl/sprites_hd/
**/.venv/
__pycache__/
.pytest_cache/
*.pyc
# sirler
.env
# TTS / Whisper: yalniz skriptler ve konfiq
TTS/*
!TTS/*.py
!TTS/config/
Whisper/*
!Whisper/*.py
```

- [ ] **Step 3: `pytest.ini` yaz**

```ini
[pytest]
testpaths = Projects/tests
addopts = -p no:cacheprovider
```

- [ ] **Step 4: `Projects/tests/conftest.py` yaz**

```python
"""Test importlari: Projects, Projects/_ffmpeg, Projects/sprites sys.path-e elave olunur."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
for p in (PROJ, os.path.join(PROJ, "_ffmpeg"), os.path.join(PROJ, "sprites")):
    if p not in sys.path:
        sys.path.insert(0, p)
```

- [ ] **Step 5: smoke test yaz** — `Projects/tests/test_smoke.py`

```python
def test_existing_modules_import():
    import montage  # noqa: F401
    import script_gen

    assert script_gen.WPM == 199.0
```

- [ ] **Step 6: testi işlət**

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe -m pytest -q`
Expected: `1 passed`

- [ ] **Step 7: git init + ilk commit**

```bash
cd /c/YouTubeAI && git init && git add -A && git status --short | head -50
```
Yoxla: siyahıda `.env`, `.venv`, `ComfyUI/`, `Models/`, `Episodes/`, `*.wav`, `*.mp4` **yoxdur**. Varsa `.gitignore`-u düzəlt, `git rm -r --cached <yol>`.

```bash
git commit -m "chore: init repo, pytest scaffold"
```

---

### Task 1: `checks.py` — video/audio yoxlamaları

**Files:**
- Create: `Projects/checks.py`
- Test: `Projects/tests/test_checks.py`

**Interfaces:**
- Produces: `ffprobe(path) -> dict`, `duration(path) -> float`, `video_problems(info) -> list[str]`, `audio_problems(info) -> list[str]`, `av_drift(info) -> float`, `parse_ebur128_integrated(stderr) -> float`, `integrated_lufs(path) -> float`, `decode_errors(path) -> str`, `final_video_problems(mp4) -> list[str]`; sabitlər `TARGET_LUFS=-14.0`, `LUFS_TOL=1.0`, `MAX_DRIFT_S=0.2`.

- [ ] **Step 1: Failing test yaz** — `Projects/tests/test_checks.py`

```python
import copy

import pytest

import checks

GOOD = {
    "streams": [
        {"codec_type": "video", "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p",
         "level": 41, "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "600.000"},
        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2,
         "duration": "600.050"},
    ],
    "format": {"duration": "600.050"},
}


def test_good_info_has_no_problems():
    assert checks.video_problems(GOOD) == []
    assert checks.audio_problems(GOOD) == []


def test_yuv444_is_reported():
    bad = copy.deepcopy(GOOD)
    bad["streams"][0]["pix_fmt"] = "yuv444p"
    assert any("yuv444p" in p for p in checks.video_problems(bad))


def test_mono_24k_audio_is_reported():
    bad = copy.deepcopy(GOOD)
    bad["streams"][1].update(sample_rate="24000", channels=1)
    probs = checks.audio_problems(bad)
    assert any("24000" in p for p in probs) and any("1" in p for p in probs)


def test_av_drift():
    assert checks.av_drift(GOOD) == pytest.approx(0.05)


def test_parse_ebur128_takes_summary_not_frame_lines():
    stderr = ("[Parsed_ebur128_0 @ 0] t: 0.1  TARGET:-23 LUFS  M: -70.0 S:-70.0  I: -70.0 LUFS\n"
              "[Parsed_ebur128_0 @ 0] Summary:\n\n  Integrated loudness:\n    I:         -14.2 LUFS\n"
              "    Threshold: -24.3 LUFS\n")
    assert checks.parse_ebur128_integrated(stderr) == pytest.approx(-14.2)


def test_parse_ebur128_missing_raises():
    with pytest.raises(ValueError):
        checks.parse_ebur128_integrated("nothing here")
```

- [ ] **Step 2: Fail olduğunu yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_checks.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'checks'`

- [ ] **Step 3: `Projects/checks.py` yaz**

```python
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
```

- [ ] **Step 4: Testləri işlət**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_checks.py -q`
Expected: `6 passed`

- [ ] **Step 5: Real faylda yoxla** (mövcud epizod: 24 kHz mono gözlənilir)

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'Projects'); import checks; print(checks.final_video_problems('Episodes/trademark-copyright-patent/trademark-copyright-patent.mp4'))"`
Expected: yalnız audio problemləri (`sample_rate='24000'`, `channels=1`) — video problemi yox, dekod xətası yox.

- [ ] **Step 6: Commit**

```bash
git add Projects/checks.py Projects/tests/test_checks.py
git commit -m "feat: checks.py - ffprobe/ebur128/decode acceptance checks"
```

---

### Task 2: `timeline.py` — müddət, SRT sürüşməsi, bölmə başlanğıcları

**Files:**
- Create: `Projects/timeline.py`
- Test: `Projects/tests/test_timeline.py`

**Interfaces:**
- Produces: `INTRO_S = 4.0`, `OUTRO_S = 6.0`, `plan_timeline(scene_durs: list[float], xfade: float, intro_s: float = 0.0, outro_s: float = 0.0) -> list[float]`, `montage_total(durs: list[float], xfade: float) -> float`, `shift_srt(text: str, offset_s: float) -> str`, `display_title(section: str) -> str`, `section_starts(scenes: list[dict], offset_s: float = 0.0) -> list[tuple[str, float]]`, `first_of_section(scenes: list[dict]) -> list[bool]`.

- [ ] **Step 1: Failing test yaz** — `Projects/tests/test_timeline.py`

```python
import pytest

import timeline as tl

SCENES = [{"section": "Hook", "duration": 10}, {"section": "Hook", "duration": 5},
          {"section": "Section 1: A", "duration": 20}, {"section": "Recap", "duration": 8}]


def test_plan_timeline_without_cards():
    assert tl.plan_timeline([10, 20, 30], 0.5) == [10.5, 20.5, 30]


def test_plan_timeline_with_cards_total_matches():
    durs = tl.plan_timeline([10, 20], 0.5, 4.0, 6.0)
    assert durs == [4.5, 10.5, 20.5, 6.0]
    assert tl.montage_total(durs, 0.5) == pytest.approx(40.0)


def test_plan_timeline_empty_raises():
    with pytest.raises(ValueError):
        tl.plan_timeline([], 0.5)


def test_shift_srt():
    src = "1\n00:00:01,000 --> 00:00:02,500\nHi\n"
    assert tl.shift_srt(src, 4.0) == "1\n00:00:05,000 --> 00:00:06,500\nHi\n"


def test_shift_srt_crosses_minute():
    assert "00:01:03,200" in tl.shift_srt("00:00:59,200 --> 00:01:00,000", 4.0)


def test_display_title():
    assert tl.display_title("Section 2: Why Brands Matter") == "Why Brands Matter"
    assert tl.display_title("Recap") == "Recap"


def test_section_starts_with_offset():
    assert tl.section_starts(SCENES, 4.0) == [("Hook", 4.0), ("Section 1: A", 19.0), ("Recap", 39.0)]


def test_first_of_section():
    assert tl.first_of_section(SCENES) == [True, False, True, True]
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_timeline.py -q`
Expected: FAIL — `No module named 'timeline'`

- [ ] **Step 3: `Projects/timeline.py` yaz**

```python
"""Epizod zaman xetti: montage muddetleri, intro/outro, SRT surusmesi, bolme baslangiclari."""
from __future__ import annotations

import re

INTRO_S = 4.0    # intro karti; narration bu qeder surusur
OUTRO_S = 6.0    # outro karti; narration bitenden sonra

_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def plan_timeline(scene_durs: list[float], xfade: float,
                  intro_s: float = 0.0, outro_s: float = 0.0) -> list[float]:
    """montage.py ucun klip muddetleri. montage her kecidde xfade qeder ortusme yaradir
    (total = sum(d) - xfade*(n-1)), ona gore sonuncudan basqa her klip xfade qeder uzadilir."""
    clips = ([intro_s] if intro_s > 0 else []) + [float(d) for d in scene_durs] \
        + ([outro_s] if outro_s > 0 else [])
    if not clips:
        raise ValueError("bos timeline")
    return [round(d + xfade, 3) for d in clips[:-1]] + [round(clips[-1], 3)]


def montage_total(durs: list[float], xfade: float) -> float:
    return sum(durs) - xfade * (len(durs) - 1)


def _fmt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def shift_srt(text: str, offset_s: float) -> str:
    def rep(m: re.Match) -> str:
        t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
        return _fmt(max(0.0, t + offset_s))
    return _TS.sub(rep, text)


def display_title(section: str) -> str:
    return re.sub(r"^Section\s+\d+\s*:\s*", "", section).strip()


def section_starts(scenes: list[dict], offset_s: float = 0.0) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    t = offset_s
    for s in scenes:
        if not out or out[-1][0] != s["section"]:
            out.append((s["section"], round(t, 2)))
        t += float(s["duration"])
    return out


def first_of_section(scenes: list[dict]) -> list[bool]:
    return [i == 0 or scenes[i - 1]["section"] != s["section"] for i, s in enumerate(scenes)]
```

- [ ] **Step 4: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_timeline.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add Projects/timeline.py Projects/tests/test_timeline.py
git commit -m "feat: timeline.py - clip durations, srt shift, section starts"
```

---

### Task 3: `motion.py` — çoxoxlu Ken Burns + keçid növbəsi

**Files:**
- Create: `Projects/_ffmpeg/motion.py`
- Test: `Projects/tests/test_motion.py`

**Interfaces:**
- Produces: `FPS=30`, `W=1920`, `H=1080`, `KB_W=5120`, `KB_H=2880`, `TRANSITIONS=("fade","slideleft","wipeleft","dissolve")`, `MOTIONS: dict[str, Motion]`, `motion_for(i: int) -> str`, `kenburns(idx: int, dur: float, motion: str, out: str) -> str` (giriş `[idx:v]`, çıxış `[out]`), `transitions_for(sections: list[str]) -> list[str]` (uzunluq `len(sections)-1`).
- Giriş şəkli montage-də `-loop 1 -framerate 30` ilə verilir → `zoompan d=1` (hər giriş kadrı = 1 çıxış kadrı).

- [ ] **Step 1: Failing test** — `Projects/tests/test_motion.py`

```python
import motion


def test_motion_cycle():
    assert [motion.motion_for(i) for i in range(5)] == [
        "zoom_in", "pan_lr", "zoom_out", "pan_rl", "zoom_in"]


def test_kenburns_filter_shape():
    f = motion.kenburns(3, 6.0, "pan_lr", "b3")
    assert f.startswith("[3:v]scale=5120:2880")
    assert "crop=5120:2880" in f
    assert "d=1" in f and "s=1920x1080" in f and "fps=30" in f
    assert "vignette" in f
    assert f.endswith("[b3]")


def test_kenburns_uses_easing_and_frames():
    f = motion.kenburns(0, 6.0, "zoom_in", "b0")
    assert "on/179" in f          # 6 s * 30 fps = 180 kadr -> 0..179
    assert "3-2*" in f            # smoothstep


def test_transitions_fade_on_section_change():
    secs = ["a", "a", "b", "b", "b"]
    assert motion.transitions_for(secs) == ["fade", "fade", "wipeleft", "dissolve"]


def test_transitions_single_clip():
    assert motion.transitions_for(["a"]) == []
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_motion.py -q`
Expected: FAIL — `No module named 'motion'`

- [ ] **Step 3: `Projects/_ffmpeg/motion.py` yaz**

```python
"""Ken Burns hereket novleri + kecid novbesi (FAZA F 3.3, 3.4).
Fon 5120x2880 menbeden kesilir: 1 px giris titremesi cixisda ~0.4 px olur - hamar hereket."""
from __future__ import annotations

from dataclasses import dataclass

FPS = 30
W, H = 1920, 1080
KB_W, KB_H = 5120, 2880
VIGNETTE = "vignette=angle=PI/5"
TRANSITIONS = ("fade", "slideleft", "wipeleft", "dissolve")


@dataclass(frozen=True)
class Motion:
    z0: float    # baslangic zoom
    z1: float    # son zoom
    px0: float   # ufuqi movqe 0 = sol, 1 = sag
    px1: float


MOTIONS: dict[str, Motion] = {
    "zoom_in": Motion(1.00, 1.10, 0.5, 0.5),
    "zoom_out": Motion(1.10, 1.00, 0.5, 0.5),
    "pan_lr": Motion(1.08, 1.10, 0.0, 1.0),
    "pan_rl": Motion(1.08, 1.10, 1.0, 0.0),
}
ORDER = ("zoom_in", "pan_lr", "zoom_out", "pan_rl")


def motion_for(i: int) -> str:
    return ORDER[i % len(ORDER)]


def kenburns(idx: int, dur: float, motion: str, out: str) -> str:
    """[idx:v] -> [out]: smoothstep easing ile zoom + pan, yumsaq vignette."""
    m = MOTIONS[motion]
    frames = max(2, round(dur * FPS))
    p = f"min(on/{frames - 1},1)"
    e = f"({p})*({p})*(3-2*({p}))"
    z = f"{m.z0}+({m.z1 - m.z0:.4f})*{e}"
    x = f"(iw-iw/zoom)*({m.px0}+({m.px1 - m.px0:.4f})*{e})"
    y = "(ih-ih/zoom)/2"
    return (f"[{idx}:v]scale={KB_W}:{KB_H}:force_original_aspect_ratio=increase,crop={KB_W}:{KB_H},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},{VIGNETTE},"
            f"format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[{out}]")


def transitions_for(sections: list[str]) -> list[str]:
    """Klipler arasi kecidler: bolme deyisende 'fade', bolme daxilinde novbe ile."""
    return ["fade" if sections[i] != sections[i + 1] else TRANSITIONS[i % len(TRANSITIONS)]
            for i in range(len(sections) - 1)]
```

- [ ] **Step 4: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_motion.py -q`
Expected: `5 passed`

- [ ] **Step 5: ffmpeg-in ifadəni qəbul etdiyini yoxla** (5 s test klip, mövcud fon)

```bash
cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'Projects/_ffmpeg'); import motion
print(motion.kenburns(0, 5.0, 'pan_lr', 'v'))" > Temp/kb.txt && \
ffmpeg -y -v error -loop 1 -framerate 30 -t 6 -i Episodes/trademark-copyright-patent/bg/sc01.png \
  -/filter_complex Temp/kb.txt -map "[v]" -t 5 -c:v libx264 -pix_fmt yuv420p Temp/kb_test.mp4 && \
ffprobe -v error -show_entries format=duration -of csv=p=0 Temp/kb_test.mp4
```
Expected: `5.000000` və xəta yoxdur. `Temp/kb_test.mp4`-ü aç — soldan sağa hamar pan, kənarlarda yüngül vignette.

- [ ] **Step 6: Commit**

```bash
git add Projects/_ffmpeg/motion.py Projects/tests/test_motion.py
git commit -m "feat: motion.py - eased multi-axis Ken Burns and transition rotation"
```

---

### Task 4: `audio_master.py` — 48 kHz stereo, ducking, iki keçidli loudnorm

**Files:**
- Create: `Projects/_ffmpeg/audio_master.py`
- Test: `Projects/tests/test_audio_master.py`

**Interfaces:**
- Produces: `SR=48000`, `mix_graph(narr_in: int, music_in: int | None, delay_s: float, total_s: float) -> str` (sonu `[amix]`), `loudnorm_measure() -> str` (`[amix]`→`[aout]`), `parse_loudnorm_json(stderr: str) -> dict`, `loudnorm_apply(m: dict) -> str` (`[amix]`→`[aout]`), `measure(audio_inputs: list[str], graph: str, total_s: float) -> dict`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_audio_master.py`

```python
import pytest

import audio_master as am

LOUDNORM_STDERR = """[Parsed_loudnorm_1 @ 0000] 
{
	"input_i" : "-20.50",
	"input_tp" : "-3.10",
	"input_lra" : "5.20",
	"input_thresh" : "-30.80",
	"output_i" : "-14.02",
	"output_tp" : "-1.50",
	"output_lra" : "4.10",
	"output_thresh" : "-24.30",
	"normalization_type" : "dynamic",
	"target_offset" : "0.02"
}
"""


def test_mix_without_music():
    g = am.mix_graph(3, None, 4.0, 100.0)
    assert "[3:a]" in g and "aresample=48000" in g
    assert "pan=stereo|c0=c0|c1=c0" in g
    assert "adelay=delays=4000:all=1" in g
    assert "apad=whole_dur=100.000" in g
    assert "sidechaincompress" not in g
    assert g.endswith("[amix]")


def test_mix_with_music_ducks():
    g = am.mix_graph(3, 4, 0.0, 50.0)
    assert "[4:a]" in g and "sidechaincompress" in g and "amix=inputs=2" in g
    assert g.endswith("[amix]")


def test_parse_loudnorm_json():
    m = am.parse_loudnorm_json(LOUDNORM_STDERR)
    assert m["input_i"] == "-20.50" and m["target_offset"] == "0.02"


def test_parse_loudnorm_missing_raises():
    with pytest.raises(ValueError):
        am.parse_loudnorm_json("no json")


def test_loudnorm_apply():
    f = am.loudnorm_apply(am.parse_loudnorm_json(LOUDNORM_STDERR))
    assert f.startswith("[amix]loudnorm=I=-14")
    assert "measured_I=-20.50" in f and "offset=0.02" in f and "linear=true" in f
    assert f.endswith("[aout]")
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_audio_master.py -q`
Expected: FAIL — `No module named 'audio_master'`

- [ ] **Step 3: `Projects/_ffmpeg/audio_master.py` yaz**

```python
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


def mix_graph(narr_in: int, music_in: int | None, delay_s: float, total_s: float) -> str:
    ms = int(round(delay_s * 1000))
    narr = (f"[{narr_in}:a]aresample={SR},aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0,"
            f"adelay=delays={ms}:all=1,apad=whole_dur={total_s:.3f}")
    if music_in is None:
        return narr + "[amix]"
    return (f"{narr},asplit=2[nmain][nkey];"
            f"[{music_in}:a]aresample={SR},aformat=channel_layouts=stereo,volume={MUSIC_DB}dB[mus];"
            f"[mus][nkey]{DUCK}[duck];"
            f"[nmain][duck]amix=inputs=2:duration=first:normalize=0[amix]")


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
```

- [ ] **Step 4: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_audio_master.py -q`
Expected: `5 passed`

- [ ] **Step 5: Real audio ilə ölçmə**

```bash
cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'Projects/_ffmpeg'); import audio_master as am
g = am.mix_graph(0, None, 4.0, 64.0)
print(am.measure(['-t','60','-i','Episodes/trademark-copyright-patent/narration.wav'], g, 64.0))"
```
Expected: `input_i` təxminən −15…−25 olan dict, xəta yoxdur.

- [ ] **Step 6: Commit**

```bash
git add Projects/_ffmpeg/audio_master.py Projects/tests/test_audio_master.py
git commit -m "feat: audio_master.py - 48k stereo, ducking, two-pass loudnorm"
```

---

### Task 5: Modellər və fontlar

**Files:**
- Create: `Models/upscale_models/4x-UltraSharp.pth`, `Models/upscale_models/RealESRGAN_x4plus_anime_6B.pth`, `Assets/fonts/Montserrat-SemiBold.ttf`, `Assets/fonts/Montserrat-ExtraBold.ttf`, `Assets/fonts/OFL.txt`

**Interfaces:**
- Produces: ComfyUI `UpscaleModelLoader` siyahısında `4x-UltraSharp.pth` və `RealESRGAN_x4plus_anime_6B.pth`; `cards.load_font("SemiBold"|"ExtraBold", size)` və libass `FontName=Montserrat SemiBold` üçün fayllar.

- [ ] **Step 1: Upscale modellərini yüklə**

```bash
cd /c/YouTubeAI/Models/upscale_models && \
curl -L --fail -o 4x-UltraSharp.pth https://huggingface.co/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth && \
curl -L --fail -o RealESRGAN_x4plus_anime_6B.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth && \
ls -l
```
Expected: `4x-UltraSharp.pth` ≈ 67 MB, `RealESRGAN_x4plus_anime_6B.pth` ≈ 18 MB. Hər hansı < 10 MB-dırsa (HTML xəta səhifəsi) — **dayan, istifadəçiyə bildir**.

- [ ] **Step 2: Fontları yüklə (OFL)**

```bash
mkdir -p /c/YouTubeAI/Assets/fonts && cd /c/YouTubeAI/Assets/fonts && \
curl -L --fail -o Montserrat-SemiBold.ttf https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf && \
curl -L --fail -o Montserrat-ExtraBold.ttf https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf && \
curl -L --fail -o OFL.txt https://github.com/JulietaUla/Montserrat/raw/master/OFL.txt && ls -l
```

- [ ] **Step 3: Fontların oxunduğunu yoxla**

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe -c "from PIL import ImageFont; [print(ImageFont.truetype(f'Assets/fonts/Montserrat-{w}.ttf', 40).getname()) for w in ('SemiBold','ExtraBold')]"`
Expected: `('Montserrat', 'SemiBold')` və `('Montserrat', 'ExtraBold')`

- [ ] **Step 4: ComfyUI-ni qaldır və modelləri gördüyünü yoxla** (Bash `run_in_background: true`)

```bash
cd /c/YouTubeAI/ComfyUI && .venv/Scripts/python.exe main.py --listen 127.0.0.1 --port 8188 --lowvram
```
Sonra:
```bash
curl -s http://127.0.0.1:8188/object_info/UpscaleModelLoader | Projects/.venv/Scripts/python.exe -c "import sys,json; print(json.load(sys.stdin)['UpscaleModelLoader']['input']['required']['model_name'][0])"
```
(`/c/YouTubeAI`-dən işlət.) Expected: siyahıda hər iki `.pth`. ComfyUI növbəti task üçün açıq qalır.

- [ ] **Step 5: Commit** (yalnız fontlar; modellər `.gitignore`-dadır)

```bash
cd /c/YouTubeAI && git add Assets/fonts && git commit -m "chore: add Montserrat SemiBold/ExtraBold (OFL)"
```

---

### Task 6: `imaging.py` + `upscale.py` + `upscale_bgs.py`

**Files:**
- Create: `Projects/imaging.py`, `Projects/upscale.py`, `Projects/_workflows/upscale_4x_api.json`, `Projects/upscale_bgs.py`
- Test: `Projects/tests/test_imaging_upscale.py`

**Interfaces:**
- Consumes: `run_workflow.submit(workflow: dict) -> str`, `run_workflow.wait(prompt_id: str, timeout_s: int) -> list[str]`, `render_bgs.require_server() -> None`.
- Produces: `imaging.cover_box(w, h, tw, th) -> tuple[int,int,int,int]`, `imaging.fit_cover(img, tw, th) -> Image.Image`; `upscale.build_workflow(image_name: str, model: str, prefix: str) -> dict`, `upscale.upscale_file(src: str, model: str, prefix: str, timeout_s: int = 900) -> str` (ComfyUI output yolu); CLI `upscale_bgs.py <episode_dir> [--only N ...] [--force] [--model NAME]` → `bg_hd/scNN.png` 5120×2880.

- [ ] **Step 1: Failing test** — `Projects/tests/test_imaging_upscale.py`

```python
from PIL import Image

import imaging
import upscale


def test_cover_box_sdxl_4x_to_16x9():
    assert imaging.cover_box(5376, 3072, 5120, 2880) == (0, 24, 5376, 3048)


def test_cover_box_too_wide():
    assert imaging.cover_box(2000, 1000, 1600, 900) == (111, 0, 1889, 1000)


def test_fit_cover_size():
    img = Image.new("RGB", (1344, 768), "red")
    assert imaging.fit_cover(img, 1280, 720).size == (1280, 720)


def test_build_workflow_placeholders():
    wf = upscale.build_workflow("hd_x_01.png", "4x-UltraSharp.pth", "hd_x_01")
    assert wf["1"]["inputs"]["image"] == "hd_x_01.png"
    assert wf["2"]["inputs"]["model_name"] == "4x-UltraSharp.pth"
    assert wf["4"]["inputs"]["filename_prefix"] == "hd_x_01"
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_imaging_upscale.py -q`
Expected: FAIL — `No module named 'imaging'`

- [ ] **Step 3: `Projects/imaging.py` yaz**

```python
"""Ortaq sekil yardimcilari."""
from __future__ import annotations

from PIL import Image


def cover_box(w: int, h: int, tw: int, th: int) -> tuple[int, int, int, int]:
    """Merkezden kesim qutusu: (w, h) -> tw:th nisbeti, hec bir bos zolaq qalmadan."""
    target = tw / th
    if w / h > target:
        nw = round(h * target)
        left = (w - nw) // 2
        return (left, 0, left + nw, h)
    nh = round(w / target)
    top = (h - nh) // 2
    return (0, top, w, top + nh)


def fit_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
    return img.crop(cover_box(img.width, img.height, tw, th)).resize((tw, th), Image.LANCZOS)
```

- [ ] **Step 4: `Projects/_workflows/upscale_4x_api.json` yaz**

```json
{
  "1": {"class_type": "LoadImage", "inputs": {"image": "__IMAGE__"}},
  "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "__MODEL__"}},
  "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
  "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 0], "filename_prefix": "__PREFIX__"}}
}
```

- [ ] **Step 5: `Projects/upscale.py` yaz**

```python
"""ComfyUI upscale modeli ile sekil boyutme (4x-UltraSharp fonlar, RealESRGAN anime sprite-ler).
ComfyUI serveri isleyir olmalidir; ImageUpscaleWithModel 8 GB VRAM-da ozu tile-layir."""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_workflow import submit, wait  # noqa: E402

COMFY_IN = r"C:\YouTubeAI\ComfyUI\input"
COMFY_OUT = r"C:\YouTubeAI\ComfyUI\output"
WORKFLOW = r"C:\YouTubeAI\Projects\_workflows\upscale_4x_api.json"


def build_workflow(image_name: str, model: str, prefix: str) -> dict:
    with open(WORKFLOW, encoding="utf-8") as f:
        text = f.read()
    text = (text.replace("__IMAGE__", image_name).replace("__MODEL__", model)
                .replace("__PREFIX__", prefix))
    return json.loads(text)


def upscale_file(src: str, model: str, prefix: str, timeout_s: int = 900) -> str:
    """src -> ComfyUI/input/<prefix>.png -> upscale -> ComfyUI/output-daki fayl yolu."""
    name = f"{prefix}.png"
    shutil.copyfile(src, os.path.join(COMFY_IN, name))
    files = wait(submit(build_workflow(name, model, prefix)), timeout_s=timeout_s)
    out = os.path.join(COMFY_OUT, files[-1])
    if not os.path.isfile(out):
        raise RuntimeError("upscale cixisi tapilmadi: " + out)
    return out
```

- [ ] **Step 6: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_imaging_upscale.py -q`
Expected: `4 passed`

- [ ] **Step 7: `Projects/upscale_bgs.py` yaz**

```python
"""FAZA F 3.2 - bg\\scNN.png (SDXL 1344x768) -> 4x-UltraSharp -> bg_hd\\scNN.png (5120x2880).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\upscale_bgs.py Episodes\\<slug> [--only 3 7] [--force]
ComfyUI serveri isleyir olmalidir.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imaging import fit_cover  # noqa: E402
from render_bgs import require_server  # noqa: E402
from upscale import upscale_file  # noqa: E402

MODEL = "4x-UltraSharp.pth"
HD_W, HD_H = 5120, 2880


def upscale_one(src: str, dest: str, model: str, prefix: str) -> None:
    out = upscale_file(src, model, prefix)
    with Image.open(out) as im:
        fit_cover(im.convert("RGB"), HD_W, HD_H).save(dest, compress_level=3)
    os.remove(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--only", nargs="*", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()

    srcs = sorted(glob.glob(os.path.join(a.episode_dir, "bg", "sc[0-9][0-9].png")))
    if not srcs:
        raise SystemExit("bg\\scNN.png tapilmadi - once render_bgs.py isledin")
    require_server()
    hd_dir = os.path.join(a.episode_dir, "bg_hd")
    os.makedirs(hd_dir, exist_ok=True)
    slug = os.path.basename(os.path.normpath(a.episode_dir))

    todo = [s for s in srcs
            if (not a.only or int(os.path.basename(s)[2:4]) in a.only)
            and (a.force or not os.path.isfile(os.path.join(hd_dir, os.path.basename(s))))]
    print(f"[F] {len(todo)}/{len(srcs)} fon boyudulecek -> {hd_dir}")
    failed, t0 = [], time.time()
    for k, src in enumerate(todo, 1):
        name = os.path.basename(src)
        try:
            upscale_one(src, os.path.join(hd_dir, name), a.model, f"hd_{slug}_{name[:-4]}")
        except (SystemExit, RuntimeError, OSError) as e:
            print(f"  {name} UGURSUZ: {e}")
            failed.append(name)
            continue
        el = time.time() - t0
        print(f"  [{k}/{len(todo)}] {name}  {el / k:.0f}s/eded  qalan ~{(len(todo) - k) * el / k / 60:.1f} deq")
    if failed:
        raise SystemExit(f"ugursuz fonlar: {failed}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Mövcud epizodun 1 fonunda sına** (ComfyUI Task 5-dən açıqdır)

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe Projects/upscale_bgs.py Episodes/trademark-copyright-patent --only 1`
Expected: `[1/1] sc01.png ...`; sonra
`Projects/.venv/Scripts/python.exe -c "from PIL import Image; print(Image.open('Episodes/trademark-copyright-patent/bg_hd/sc01.png').size)"` → `(5120, 2880)`. Bir fonun müddətini qeyd et (progress.md üçün).

- [ ] **Step 9: Qalan 28 fonu boyüt** (Task 10-un yoxlaması üçün lazımdır; Bash `run_in_background: true`)

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe Projects/upscale_bgs.py Episodes/trademark-copyright-patent`
Expected: sonda `ugursuz` yoxdur; `ls Episodes/trademark-copyright-patent/bg_hd | wc -l` → `29`.

- [ ] **Step 10: Commit**

```bash
git add Projects/imaging.py Projects/upscale.py Projects/upscale_bgs.py Projects/_workflows/upscale_4x_api.json Projects/tests/test_imaging_upscale.py
git commit -m "feat: 4x-UltraSharp background upscale to 5120x2880 via ComfyUI"
```

---

### Task 7: HD sprite-lər + kontakt kölgəsi

**Files:**
- Create: `Projects/sprites/upscale_sprites.py`
- Test: `Projects/tests/test_upscale_sprites.py`

**Interfaces:**
- Consumes: `upscale.upscale_file(src, model, prefix) -> str`, `render_bgs.require_server()`.
- Produces: `Character/ELI5_Owl/sprites_hd/<ad>.png` (RGBA, ~4×), `sprites_hd/<ad>_shadow.png` (RGBA, eni = sprite eni), `sprites_hd/sprites.json` (`{ad: {"file", "w", "h"}}`); funksiyalar `finish_alpha(alpha: Image, size: tuple[int,int], erode_px: int) -> Image`, `compose_rgba(rgb: Image, alpha: Image) -> Image`, `make_shadow(width: int) -> Image`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_upscale_sprites.py`

```python
from PIL import Image, ImageDraw

import upscale_sprites as us


def _square_alpha() -> Image.Image:
    a = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(a).rectangle((4, 4, 15, 15), fill=255)
    return a


def test_finish_alpha_erodes_edge_keeps_core():
    out = us.finish_alpha(_square_alpha(), (20, 20), 1)
    assert out.getpixel((4, 10)) < 128        # evvelki kenar (halo) yeyildi
    assert out.getpixel((10, 10)) >= 250      # merkez qalir


def test_finish_alpha_resizes():
    assert us.finish_alpha(_square_alpha(), (80, 80), 3).size == (80, 80)


def test_compose_rgba():
    rgb = Image.new("RGB", (20, 20), "white")
    out = us.compose_rgba(rgb, _square_alpha())
    assert out.mode == "RGBA" and out.getpixel((0, 0))[3] == 0 and out.getpixel((10, 10))[3] == 255


def test_make_shadow_soft_and_faint():
    sh = us.make_shadow(800)
    assert sh.mode == "RGBA" and sh.width == 800
    alpha = sh.getchannel("A")
    cx, cy = sh.width // 2, sh.height // 2
    assert alpha.getpixel((cx, cy)) > alpha.getpixel((cx, 2))
    assert max(alpha.getdata()) <= round(255 * us.SHADOW_OPACITY) + 1
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_upscale_sprites.py -q`
Expected: FAIL — `No module named 'upscale_sprites'`

- [ ] **Step 3: `Projects/sprites/upscale_sprites.py` yaz**

```python
"""FAZA F 3.1 - sprites\\*.png -> RealESRGAN anime 4x -> sprites_hd\\*.png (+ <ad>_shadow.png).
RGB ESRGAN ile, alpha ayrica lanczos ile boyudulur, sonra erode (ag halo gedir).
Istifade (bir defelik, ComfyUI isleyir olmalidir):
  Projects\\.venv\\Scripts\\python Projects\\sprites\\upscale_sprites.py
Boyuk character sheet gelende: make_sprites.py -> bu skript yeniden.
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)

SRC_JSON = r"C:\YouTubeAI\Character\ELI5_Owl\sprites\sprites.json"
HD_DIR = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"
MODEL = "RealESRGAN_x4plus_anime_6B.pth"
ERODE_PX = 3             # HD miqyasinda (~1 px orijinalda)
SHADOW_W_RATIO = 0.70    # kolge eni / sprite eni
SHADOW_ASPECT = 0.18     # ellips hundurluyu / eni
SHADOW_BLUR = 18
SHADOW_OPACITY = 0.35


def finish_alpha(alpha: Image.Image, size: tuple[int, int], erode_px: int) -> Image.Image:
    a = alpha.convert("L").resize(size, Image.LANCZOS)
    if erode_px > 0:
        a = a.filter(ImageFilter.MinFilter(2 * erode_px + 1))
    return a.filter(ImageFilter.GaussianBlur(0.8))


def compose_rgba(rgb: Image.Image, alpha: Image.Image) -> Image.Image:
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def make_shadow(width: int) -> Image.Image:
    ew = round(width * SHADOW_W_RATIO)
    eh = max(4, round(ew * SHADOW_ASPECT))
    pad = SHADOW_BLUR * 3
    mask = Image.new("L", (width, eh + 2 * pad), 0)
    x0 = (width - ew) // 2
    ImageDraw.Draw(mask).ellipse((x0, pad, x0 + ew, pad + eh), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)).point(
        lambda v: round(v * SHADOW_OPACITY))
    shadow = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    shadow.putalpha(mask)
    return shadow


def upscale_sprite(name: str, src: str) -> dict:
    from upscale import upscale_file  # ComfyUI klienti yalniz real isde lazimdir
    out = upscale_file(src, MODEL, f"sprite_{name}")
    with Image.open(out) as up, Image.open(src) as orig:
        rgb = up.convert("RGB")
        alpha = finish_alpha(orig.getchannel("A"), rgb.size, ERODE_PX)
    hd = compose_rgba(rgb, alpha)
    dest = os.path.join(HD_DIR, f"{name}.png")
    hd.save(dest)
    make_shadow(hd.width).save(os.path.join(HD_DIR, f"{name}_shadow.png"))
    os.remove(out)
    return {"file": dest, "w": hd.width, "h": hd.height}


def main() -> None:
    from render_bgs import require_server
    with open(SRC_JSON, encoding="utf-8") as f:
        sprites = json.load(f)
    require_server()
    os.makedirs(HD_DIR, exist_ok=True)
    index = {}
    for name, info in sprites.items():
        index[name] = upscale_sprite(name, info["file"])
        print(f"  {name}: {info['w']}x{info['h']} -> {index[name]['w']}x{index[name]['h']}")
    with open(os.path.join(HD_DIR, "sprites.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"OK -> {HD_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_upscale_sprites.py -q`
Expected: `4 passed`

- [ ] **Step 5: Real sprite-ləri çevir** (ComfyUI açıq)

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe Projects/sprites/upscale_sprites.py`
Expected: 8 sətir, hər biri ~4× (məs. `front: 277x401 -> 1108x1604`), sonda `OK`. Ən kiçik HD hündürlük ≥ 454 olmalıdır (A5) — yoxla: `Projects/.venv/Scripts/python.exe -c "import json; d=json.load(open('Character/ELI5_Owl/sprites_hd/sprites.json')); print(min(v['h'] for v in d.values()))"`.

- [ ] **Step 6: Vizual yoxlama** — `Character/ELI5_Owl/sprites_hd/front.png`-ni Read tool ilə aç: kənarda ağ halo olmamalı, kəskin olmalı. Halo qalırsa `ERODE_PX = 4`, Step 5-i təkrarla.

- [ ] **Step 7: Commit**

```bash
git add Projects/sprites/upscale_sprites.py Projects/tests/test_upscale_sprites.py
git commit -m "feat: HD sprites via RealESRGAN anime + alpha erode + contact shadow"
```

---

### Task 8: `cards.py` — intro, outro, lower-third, thumbnail

**Files:**
- Create: `Projects/cards.py`
- Test: `Projects/tests/test_cards.py`

**Interfaces:**
- Consumes: `imaging.fit_cover`.
- Produces: `load_font(weight: str, size: int)`, `wrap(text: str, font, max_w: int) -> list[str]`, `intro_card(title, bg_path, sprite_path, out) -> str`, `outro_card(bg_path, sprite_path, out) -> str`, `lower_third(text, out) -> str` (1920×1080 RGBA, şəffaf, panel yuxarı-solda), `thumbnail(bg_path, sprite_path, text, out) -> str` (1280×720). Hamısı `out` yolunu qaytarır.

- [ ] **Step 1: Failing test** — `Projects/tests/test_cards.py`

```python
from PIL import Image

import cards


def _bg(tmp_path):
    p = tmp_path / "bg.png"
    Image.new("RGB", (1344, 768), (40, 90, 160)).save(p)
    return str(p)


def _sprite(tmp_path):
    p = tmp_path / "owl.png"
    Image.new("RGBA", (400, 600), (200, 150, 90, 255)).save(p)
    return str(p)


def test_wrap_splits_long_text():
    font = cards.load_font("ExtraBold", 96)
    lines = cards.wrap("Trademark vs Copyright vs Patent explained simply", font, 900)
    assert len(lines) >= 2 and all(font.getlength(ln) <= 900 for ln in lines if " " in ln)


def test_intro_card(tmp_path):
    out = cards.intro_card("Trademark vs Copyright", _bg(tmp_path), _sprite(tmp_path), str(tmp_path / "i.png"))
    assert Image.open(out).size == (1920, 1080)


def test_outro_card(tmp_path):
    out = cards.outro_card(_bg(tmp_path), _sprite(tmp_path), str(tmp_path / "o.png"))
    assert Image.open(out).size == (1920, 1080)


def test_lower_third_is_transparent_except_panel(tmp_path):
    img = Image.open(cards.lower_third("Why Brands Matter", str(tmp_path / "lt.png")))
    assert img.mode == "RGBA" and img.size == (1920, 1080)
    assert img.getpixel((960, 540))[3] == 0
    assert img.getpixel((90, 100))[3] > 0


def test_thumbnail_size(tmp_path):
    out = cards.thumbnail(_bg(tmp_path), _sprite(tmp_path), "Protect Your Idea", str(tmp_path / "t.png"))
    assert Image.open(out).size == (1280, 720)


def test_load_font_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "FONTS_DIR", str(tmp_path))
    assert cards.load_font("SemiBold", 30).size == 30
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_cards.py -q`
Expected: FAIL — `No module named 'cards'`

- [ ] **Step 3: `Projects/cards.py` yaz**

```python
"""FAZA F 3.6 / 5 - intro, outro, bolme basligi (lower-third) ve YouTube thumbnail (Pillow)."""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imaging import fit_cover  # noqa: E402

FONTS_DIR = r"C:\YouTubeAI\Assets\fonts"
FALLBACK_FONT = r"C:\Windows\Fonts\segoeuib.ttf"
W, H = 1920, 1080
THUMB_W, THUMB_H = 1280, 720
ACCENT = (255, 196, 0)
WHITE = (255, 255, 255)
PANEL = (15, 18, 28, 200)
BRAND = "ELI5 Business"


def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS_DIR, f"Montserrat-{weight}.ttf")
    if os.path.isfile(path):
        return ImageFont.truetype(path, size)
    print(f"  DIQQET: {path} yoxdur - {FALLBACK_FONT} istifade olunur")
    return ImageFont.truetype(FALLBACK_FONT, size)


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        test = f"{cur} {word}".strip()
        if not cur or font.getlength(test) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def backdrop(bg_path: str, size: tuple[int, int], blur: int, dim: float) -> Image.Image:
    with Image.open(bg_path) as im:
        img = fit_cover(im.convert("RGB"), *size)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return ImageEnhance.Brightness(img).enhance(1.0 - dim)


def paste_sprite(canvas: Image.Image, sprite_path: str, height: int, right: int, bottom: int) -> None:
    """Sprite-i hundurluye gore kicildib sag-asagi kunce yapisdirir (canvas yerinde deyisir)."""
    with Image.open(sprite_path) as im:
        owl = im.convert("RGBA")
    owl = owl.resize((round(owl.width * height / owl.height), height), Image.LANCZOS)
    canvas.paste(owl, (canvas.width - owl.width - right, canvas.height - owl.height - bottom), owl)


def _title_block(draw: ImageDraw.ImageDraw, lines: list[str], font, x: int, y: int, step: int) -> int:
    draw.rectangle((x - 50, y - 30, x - 38, y + len(lines) * step - 20), fill=ACCENT)
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=WHITE)
        y += step
    return y


def intro_card(title: str, bg_path: str, sprite_path: str, out: str) -> str:
    img = backdrop(bg_path, (W, H), blur=10, dim=0.45)
    draw = ImageDraw.Draw(img)
    font = load_font("ExtraBold", 96)
    lines = wrap(title, font, 1100)
    y = _title_block(draw, lines, font, 170, H // 2 - len(lines) * 110 // 2, 110)
    draw.text((170, y + 10), BRAND, font=load_font("SemiBold", 40), fill=ACCENT)
    paste_sprite(img, sprite_path, 620, 140, 60)
    img.save(out)
    return out


def outro_card(bg_path: str, sprite_path: str, out: str) -> str:
    img = backdrop(bg_path, (W, H), blur=10, dim=0.5)
    draw = ImageDraw.Draw(img)
    y = _title_block(draw, ["Thanks for watching!"], load_font("ExtraBold", 88), 170, 400, 110)
    draw.text((170, y + 10), f"Subscribe for more {BRAND}", font=load_font("SemiBold", 44), fill=ACCENT)
    paste_sprite(img, sprite_path, 600, 160, 60)
    img.save(out)
    return out


def lower_third(text: str, out: str) -> str:
    """Seffaf 1920x1080 kadr; panel yuxari-solda (sprite asagi kunclerde, subtitr asagi-merkezde)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = load_font("SemiBold", 44)
    x0, y0, tw = 70, 60, round(font.getlength(text))
    draw.rounded_rectangle((x0, y0, x0 + tw + 80, y0 + 84), radius=14, fill=PANEL)
    draw.rectangle((x0, y0, x0 + 10, y0 + 84), fill=ACCENT)
    draw.text((x0 + 40, y0 + 16), text, font=font, fill=WHITE)
    img.save(out)
    return out


def thumbnail(bg_path: str, sprite_path: str, text: str, out: str) -> str:
    img = backdrop(bg_path, (THUMB_W, THUMB_H), blur=0, dim=0.25)
    draw = ImageDraw.Draw(img)
    font = load_font("ExtraBold", 110)
    y = 90
    for ln in wrap(text, font, 700):
        draw.text((60, y), ln, font=font, fill=WHITE, stroke_width=8, stroke_fill=(0, 0, 0))
        y += 125
    paste_sprite(img, sprite_path, 640, 40, 0)
    img.save(out)
    return out
```

- [ ] **Step 4: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_cards.py -q`
Expected: `6 passed`

- [ ] **Step 5: Real nümunələr və vizual yoxlama**

```bash
cd /c/YouTubeAI && mkdir -p Temp/cards && Projects/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'Projects'); import cards
bg='Episodes/trademark-copyright-patent/bg_hd/sc01.png'; hd='Character/ELI5_Owl/sprites_hd/'
cards.intro_card('Trademark vs Copyright vs Patent', bg, hd+'front.png', 'Temp/cards/intro.png')
cards.outro_card(bg, hd+'happy.png', 'Temp/cards/outro.png')
cards.lower_third('What Is a Trademark', 'Temp/cards/lt.png')
cards.thumbnail(bg, hd+'confident.png', 'Name, Song or Invention?', 'Temp/cards/thumb.png')"
```
4 PNG-ni Read tool ilə aç: mətn bayquşla üst-üstə düşmür, font Montserrat-dır, thumbnail 1280×720-də oxunaqlıdır.

- [ ] **Step 6: Commit**

```bash
git add Projects/cards.py Projects/tests/test_cards.py
git commit -m "feat: cards.py - intro/outro/lower-third/thumbnail"
```

---

### Task 9: `montage.py` yenidən yazılır

**Files:**
- Modify (tam əvəz): `Projects/_ffmpeg/montage.py`
- Test: `Projects/tests/test_montage.py`

**Interfaces:**
- Consumes: `motion.kenburns`, `motion.motion_for`, `motion.FPS/W/H`; `audio_master.mix_graph`, `audio_master.measure`, `audio_master.loudnorm_apply`.
- Produces: `XFADE = 0.5`, `SPRITE_DIR` (= `sprites_hd`), `SPRITE_H = 0.42`, `SUB_STYLE`; `Sprite` (`parse(token, sprite_dir) -> Sprite | None`, `size() -> (w, h)`, `x() -> int`, `y() -> int`, `shadow_size() -> (w, h) | None`, `shadow_y() -> int`), `Clip(image, duration, sprite, lower_third)`, `input_args(clips) -> (list[str], list[dict[str,int]])`, `clip_chain(i, clip, row) -> list[str]`, `video_graph(clips, table, transitions, srt, fontsdir) -> (str, float)`, `main(argv=None)`.
- CLI (köhnə arqumentlər geriyə uyğun): `--images`, `--durations`, `--audio`, `--sprites`, `--srt`, `--music`, `--out` + yeni `--transitions`, `--lower-thirds`, `--audio-delay`, `--fontsdir`, `--sprite-dir`, `--verbose`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_montage.py`

```python
import pytest
from PIL import Image

import montage as mt


def _sprite(**kw):
    base = dict(path="s.png", shadow="sh.png", pos="right", height=0.42,
                src_w=800, src_h=1200, shadow_w=800, shadow_h=150)
    base.update(kw)
    return mt.Sprite(**base)


def test_sprite_geometry_right():
    s = _sprite()
    assert s.size() == (303, 454)
    assert s.x() == 1920 - 303 - mt.SPRITE_MARGIN_X
    assert s.y() == 1080 - 454 - mt.SPRITE_MARGIN_Y
    assert s.shadow_size() == (303, 57)
    assert s.shadow_y() == s.y() + 454 - round(454 * mt.SHADOW_INSET) - 57 // 2


def test_sprite_never_upscaled():
    with pytest.raises(SystemExit):
        _sprite(src_h=300, src_w=200).size()


def test_sprite_parse_reads_dims(tmp_path):
    Image.new("RGBA", (800, 1200)).save(tmp_path / "front.png")
    Image.new("RGBA", (800, 150)).save(tmp_path / "front_shadow.png")
    s = mt.Sprite.parse("front@left:0.4", str(tmp_path))
    assert (s.pos, s.height, s.src_w, s.src_h, s.shadow_h) == ("left", 0.4, 800, 1200, 150)
    assert mt.Sprite.parse("-", str(tmp_path)) is None


def test_input_args_table():
    clips = [mt.Clip("a.png", 6.0, _sprite(), "lt.png"), mt.Clip("b.png", 6.0, None, None)]
    args, table = mt.input_args(clips)
    assert table == [{"bg": 0, "shadow": 1, "sprite": 2, "lt": 3}, {"bg": 4}]
    assert args.count("-i") == 5 and "-framerate" in args


def test_clip_chain_labels():
    clip = mt.Clip("a.png", 6.0, _sprite(), "lt.png")
    chain = ";".join(mt.clip_chain(0, clip, {"bg": 0, "shadow": 1, "sprite": 2, "lt": 3}))
    assert "[1:v]scale=303:-1" in chain and "[2:v]scale=303:454" in chain
    assert "sin(2*PI*t/" in chain and "fade=t=in" in chain
    assert chain.endswith("[v0]")


def test_video_graph_transitions_and_total():
    clips = [mt.Clip("a.png", 6.0, None, None), mt.Clip("b.png", 6.0, None, None)]
    _, table = mt.input_args(clips)
    graph, total = mt.video_graph(clips, table, ["slideleft"], None, None)
    assert "xfade=transition=slideleft:duration=0.5:offset=5.500" in graph
    assert total == pytest.approx(11.5)


def test_video_graph_bad_transition_count():
    clips = [mt.Clip("a.png", 6.0, None, None), mt.Clip("b.png", 6.0, None, None)]
    _, table = mt.input_args(clips)
    with pytest.raises(SystemExit):
        mt.video_graph(clips, table, ["fade", "fade"], None, None)


def test_video_graph_subtitles_style():
    clips = [mt.Clip("a.png", 6.0, None, None)]
    _, table = mt.input_args(clips)
    graph, _ = mt.video_graph(clips, table, None, r"C:\x\n.srt", r"C:\f")
    assert "subtitles='C\\:/x/n.srt'" in graph and "fontsdir='C\\:/f'" in graph
    assert "BorderStyle=3" in graph and graph.endswith("[vsub]")
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_montage.py -q`
Expected: FAIL — `AttributeError: module 'montage' has no attribute 'Clip'` (və ya Sprite imzası)

- [ ] **Step 3: `Projects/_ffmpeg/montage.py`-ı tam əvəz et**

```python
"""Sekil siyahisi + narration (+ SRT, + musiqi, + personaj sprite, + bolme basligi) -> 1080p30 MP4.
Istifade:
  python montage.py --images a.png b.png ... --durations 6 5 ... --audio narr.wav
                    [--sprites front@right - thinking@left ...] [--lower-thirds - lt.png ...]
                    [--transitions fade slideleft ...] [--audio-delay 4] [--srt subs.srt --fontsdir DIR]
                    [--music bg.mp3] --out out.mp4
--sprites: her klip ucun token: `-` = sprite yoxdur, `<ad>[@left|right|center][:<hund>]`
  = <sprite-dir>/<ad>.png (+ <ad>_shadow.png), hund = ekran hundurluyu / 1080 (default 0.42).
  Sprite hec vaxt boyudulmur (A5). Kolge sabit durur, sprite ustunde yungul "bob" edir.
Audio: 48 kHz stereo, musiqi ducking, iki kecidli loudnorm -14 LUFS.
Filter qrafi fayla yazilir (-/filter_complex): 30+ sehnede Windows emr limiti (32767) asilir.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_master import loudnorm_apply, measure, mix_graph  # noqa: E402
from motion import FPS, H, W, kenburns, motion_for  # noqa: E402

XFADE = 0.5
SPRITE_DIR = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"
SPRITE_H = 0.42
SPRITE_MARGIN_X = 90
SPRITE_MARGIN_Y = 30
SHADOW_INSET = 0.02            # kolge merkezi ayaq xettinden bu qeder (sprite hundurluyu payi) yuxarida
BOB_PX, BOB_PERIOD = 4, 2.6
LT_IN, LT_OUT, LT_FADE = 0.3, 3.3, 0.4
# libass SRT ucun PlayResY=288: FontSize 13 ~ 49 px, MarginV 24 ~ 90 px (1080p).
# BorderStyle=3 qutusunu OutlineColour ile cekir.
SUB_STYLE = ("FontName=Montserrat SemiBold,FontSize=13,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H80000000,BackColour=&H80000000,BorderStyle=3,Outline=6,"
             "Shadow=0,MarginV=24,Alignment=2")


@dataclass(frozen=True)
class Sprite:
    path: str
    shadow: str | None
    pos: str
    height: float
    src_w: int
    src_h: int
    shadow_w: int = 0
    shadow_h: int = 0

    @staticmethod
    def parse(token: str, sprite_dir: str = SPRITE_DIR) -> "Sprite | None":
        """'front@right:0.42' -> Sprite; '-' -> None"""
        if token == "-":
            return None
        name, _, rest = token.partition("@")
        pos, _, h = rest.partition(":") if rest else ("right", "", "")
        pos = pos or "right"
        if pos not in ("left", "right", "center"):
            raise SystemExit("sprite pos left|right|center olmalidir: " + token)
        path = os.path.join(sprite_dir, f"{name}.png")
        if not os.path.isfile(path):
            raise SystemExit(f"sprite tapilmadi: {path} - upscale_sprites.py isledin")
        with Image.open(path) as im:
            src_w, src_h = im.size
        shadow = os.path.join(sprite_dir, f"{name}_shadow.png")
        sw = sh = 0
        if os.path.isfile(shadow):
            with Image.open(shadow) as im:
                sw, sh = im.size
        return Sprite(path, shadow if sw else None, pos, float(h) if h else SPRITE_H,
                      src_w, src_h, sw, sh)

    def size(self) -> tuple[int, int]:
        h = round(H * self.height)
        if h > self.src_h:
            raise SystemExit(f"sprite boyudulmeli olardi ({self.src_h} -> {h} px): {self.path} (A5)")
        return round(self.src_w * h / self.src_h), h

    def x(self) -> int:
        w = self.size()[0]
        return {"left": SPRITE_MARGIN_X, "right": W - w - SPRITE_MARGIN_X, "center": (W - w) // 2}[self.pos]

    def y(self) -> int:
        return H - self.size()[1] - SPRITE_MARGIN_Y

    def shadow_size(self) -> tuple[int, int] | None:
        if not self.shadow:
            return None
        w = self.size()[0]
        return w, round(self.shadow_h * w / self.shadow_w)

    def shadow_y(self) -> int:
        h = self.size()[1]
        return self.y() + h - round(h * SHADOW_INSET) - self.shadow_size()[1] // 2


@dataclass(frozen=True)
class Clip:
    image: str
    duration: float
    sprite: Sprite | None
    lower_third: str | None


def esc(p: str) -> str:
    """ffmpeg filter arqumenti ucun Windows yolu: C:\\x -> C\\:/x"""
    return p.replace("\\", "/").replace(":", "\\:")


def _loop(path: str, dur: float) -> list[str]:
    return ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur + 1:.2f}", "-i", path]


def input_args(clips: list[Clip]) -> tuple[list[str], list[dict[str, int]]]:
    """ffmpeg giris arqumentleri + her klip ucun giris indeksleri (bg/shadow/sprite/lt)."""
    args: list[str] = []
    table: list[dict[str, int]] = []
    count = 0
    for c in clips:
        paths = {"bg": c.image,
                 "shadow": c.sprite.shadow if c.sprite else None,
                 "sprite": c.sprite.path if c.sprite else None,
                 "lt": c.lower_third}
        row: dict[str, int] = {}
        for key, path in paths.items():
            if path:
                args += _loop(path, c.duration)
                row[key] = count
                count += 1
        table.append(row)
    return args, table


def _sprite_parts(i: int, spr: Sprite, row: dict[str, int], cur: str) -> tuple[list[str], str]:
    w, h = spr.size()
    x, y = spr.x(), spr.y()
    parts = []
    if "shadow" in row:
        parts.append(f"[{row['shadow']}:v]scale={w}:-1:flags=lanczos,format=rgba[sh{i}];"
                     f"[{cur}][sh{i}]overlay=x={x}:y={spr.shadow_y()}:eof_action=pass[c{i}]")
        cur = f"c{i}"
    bob = f"{y}+{BOB_PX}*sin(2*PI*t/{BOB_PERIOD})"
    parts.append(f"[{row['sprite']}:v]scale={w}:{h}:flags=lanczos,format=rgba[s{i}];"
                 f"[{cur}][s{i}]overlay=x={x}:y='{bob}':eof_action=pass[d{i}]")
    return parts, f"d{i}"


def clip_chain(i: int, clip: Clip, row: dict[str, int]) -> list[str]:
    """Bir klip: Ken Burns fon -> (kolge + sprite) -> (bolme basligi) -> [v{i}]."""
    parts = [kenburns(row["bg"], clip.duration, motion_for(i), f"b{i}")]
    cur = f"b{i}"
    if clip.sprite:
        more, cur = _sprite_parts(i, clip.sprite, row, cur)
        parts += more
    if "lt" in row:
        parts.append(f"[{row['lt']}:v]format=rgba,fade=t=in:st={LT_IN}:d={LT_FADE}:alpha=1,"
                     f"fade=t=out:st={LT_OUT}:d={LT_FADE}:alpha=1[l{i}];"
                     f"[{cur}][l{i}]overlay=0:0:eof_action=pass[e{i}]")
        cur = f"e{i}"
    parts.append(f"[{cur}]format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
    return parts


def video_graph(clips: list[Clip], table: list[dict[str, int]], transitions: list[str] | None,
                srt: str | None, fontsdir: str | None) -> tuple[str, float]:
    n = len(clips)
    trans = transitions or ["fade"] * (n - 1)
    if len(trans) != n - 1:
        raise SystemExit(f"transitions sayi {len(trans)} != klip sayi - 1 ({n - 1})")
    parts = [p for i, c in enumerate(clips) for p in clip_chain(i, c, table[i])]
    prev, offset = "v0", 0.0
    for i in range(1, n):
        offset += clips[i - 1].duration - XFADE
        out = f"x{i}" if i < n - 1 else "vout"
        parts.append(f"[{prev}][v{i}]xfade=transition={trans[i - 1]}:duration={XFADE}:offset={offset:.3f}[{out}]")
        prev = out
    if n == 1:
        parts.append("[v0]null[vout]")
    if srt:
        fd = f":fontsdir='{esc(fontsdir)}'" if fontsdir else ""
        parts.append(f"[vout]subtitles='{esc(srt)}'{fd}:force_style='{SUB_STYLE}'[vsub]")
    return ";".join(parts), sum(c.duration for c in clips) - XFADE * (n - 1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--durations", nargs="+", type=float, required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--sprites", nargs="+", help="her klip ucun token: - | ad[@pos][:hund]")
    ap.add_argument("--lower-thirds", nargs="+", help="her klip ucun: - | seffaf 1920x1080 PNG")
    ap.add_argument("--transitions", nargs="+", help="klip sayi - 1 eded xfade kecidi")
    ap.add_argument("--audio-delay", type=float, default=0.0, help="narration bu qeder saniye gec baslayir")
    ap.add_argument("--srt")
    ap.add_argument("--fontsdir")
    ap.add_argument("--music")
    ap.add_argument("--sprite-dir", default=SPRITE_DIR)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verbose", action="store_true", help="ffmpeg loglevel info (font secimi gorunur)")
    return ap.parse_args(argv)


def load_clips(a: argparse.Namespace) -> list[Clip]:
    n = len(a.images)
    sprites = a.sprites or ["-"] * n
    lts = a.lower_thirds or ["-"] * n
    if not len(a.durations) == len(sprites) == len(lts) == n:
        raise SystemExit("images, durations, sprites, lower-thirds sayi eyni olmalidir")
    extra = [a.audio] + [p for p in (a.srt, a.music) if p] + [p for p in lts if p != "-"]
    for p in a.images + extra:
        if not os.path.isfile(p):
            raise SystemExit("fayl tapilmadi: " + p)
    return [Clip(img, d, Sprite.parse(tok, a.sprite_dir), None if lt == "-" else lt)
            for img, d, tok, lt in zip(a.images, a.durations, sprites, lts)]


def main(argv: list[str] | None = None) -> None:
    a = parse_args(argv)
    clips = load_clips(a)
    vin, table = input_args(clips)
    vgraph, total = video_graph(clips, table, a.transitions, a.srt, a.fontsdir)
    audio_in = ["-i", a.audio] + (["-stream_loop", "-1", "-i", a.music] if a.music else [])
    narr_idx = sum(len(r) for r in table)
    measured = measure(audio_in, mix_graph(0, 1 if a.music else None, a.audio_delay, total), total)
    fc = ";".join([vgraph, mix_graph(narr_idx, narr_idx + 1 if a.music else None, a.audio_delay, total),
                   loudnorm_apply(measured)])
    fc_path = a.out + ".filter.txt"
    with open(fc_path, "w", encoding="utf-8") as f:
        f.write(fc)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info" if a.verbose else "error",
           *vin, *audio_in, "-/filter_complex", fc_path,
           "-map", "[vsub]" if a.srt else "[vout]", "-map", "[aout]",
           # PNG girisleri RGB oldugu ucun ffmpeg oz-ozune yuv444p (High 4:4:4) secir --
           # bunu Windows pleyerleri, telefonlar ve YouTube acmir. yuv420p mecburidir.
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-t", f"{total:.3f}", "-movflags", "+faststart", a.out]
    print("video length %.1fs, %d clips, loudnorm input %s LUFS" % (total, len(clips), measured["input_i"]))
    subprocess.run(cmd, check=True)
    os.remove(fc_path)
    print("OK ->", a.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testlər (bütün dəst)**

Run: `Projects/.venv/Scripts/python.exe -m pytest -q`
Expected: bütün testlər PASS (`test_smoke` də daxil — `montage` import olunur).

- [ ] **Step 5: 3 klipli smoke render** (real fonlar, HD sprite, lower-third, SRT sürüşməsi)

```bash
cd /c/YouTubeAI && E=Episodes/trademark-copyright-patent && \
Projects/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'Projects'); import timeline
open('Temp/smoke.srt','w',encoding='utf-8').write(timeline.shift_srt(open('$E/narration.srt',encoding='utf-8').read(), 0.0))" && \
Projects/.venv/Scripts/python.exe Projects/_ffmpeg/montage.py --verbose \
  --images $E/bg_hd/sc01.png $E/bg_hd/sc02.png $E/bg_hd/sc03.png --durations 6.5 6.5 6 \
  --sprites three_q@center front@right thinking@left --lower-thirds - Temp/cards/lt.png - \
  --transitions slideleft fade --audio $E/narration.wav --srt Temp/smoke.srt \
  --fontsdir Assets/fonts --out Temp/smoke.mp4 2> Temp/smoke.log; \
grep -i "fontselect" Temp/smoke.log | head -3; \
Projects/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'Projects'); import checks; print(checks.final_video_problems('Temp/smoke.mp4'))"
```
Expected: `fontselect: (Montserrat SemiBold, ...) -> ...Montserrat-SemiBold.ttf`; son sətir `[]`.
Uzunluq 18 s-dir — ebur128 qısa klipdə ±1 LU tolerantlıqdan kənara çıxarsa, bu yalnız smoke üçündür; qeyd et və davam et (tam epizodda Task 10-da yoxlanır).

- [ ] **Step 6: Kadrları çıxar və bax**

```bash
cd /c/YouTubeAI && for t in 2 8 15; do ffmpeg -y -v error -ss $t -i Temp/smoke.mp4 -frames:v 1 Temp/smoke_$t.png; done
```
3 PNG-ni Read tool ilə aç: bayquş kəskin, ~454 px, ayağının altında yumşaq kölgə; subtitr qara yarımşəffaf qutuda, bayquşla üst-üstə düşmür; 8-ci saniyədə yuxarı-solda bölmə başlığı.

- [ ] **Step 7: Commit**

```bash
git add Projects/_ffmpeg/montage.py Projects/tests/test_montage.py
git commit -m "feat: montage - HD sprite+shadow, lower-thirds, transitions, subtitle style, audio master"
```

---

### Task 10: `build_episode.py` — HD fonlar, kartlar, keçidlər

**Files:**
- Modify (tam əvəz): `Projects/build_episode.py`
- Test: `Projects/tests/test_build_episode.py`

**Interfaces:**
- Consumes: `timeline.plan_timeline/INTRO_S/OUTRO_S/shift_srt/display_title/first_of_section`, `motion.transitions_for`, `cards.intro_card/outro_card/lower_third`, `montage.XFADE/SPRITE_DIR`.
- Produces: `scene_image(ep_dir, n, scene, require_hd) -> str`, `lower_third_titles(scenes) -> list[str | None]`, `assemble(scenes, images, card_paths, xfade) -> dict` (açarlar: `images`, `durations` (str), `sprites`, `lower_thirds`, `transitions`, `delay`); CLI `build_episode.py <dir> [--srt] [--cards] [--require-hd] [--music M] [--out O] [--dry]`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_build_episode.py`

```python
import pytest
from PIL import Image

import build_episode as be

SCENES = [
    {"section": "Hook", "duration": 10, "sprite_token": "three_q@center"},
    {"section": "Section 1: A", "duration": 20, "sprite_token": "front@right"},
    {"section": "Section 1: A", "duration": 30, "sprite_token": "box@right"},
]
CARDS = {"intro": "i.png", "outro": "o.png", "lower_thirds": ["-", "lt2.png", "-"]}


def test_lower_third_titles_skip_hook():
    assert be.lower_third_titles(SCENES) == [None, "A", None]


def test_assemble_with_cards():
    p = be.assemble(SCENES, ["1.png", "2.png", "3.png"], CARDS, 0.5)
    assert p["images"] == ["i.png", "1.png", "2.png", "3.png", "o.png"]
    assert p["durations"] == ["4.500", "10.500", "20.500", "30.500", "6.000"]
    assert p["sprites"] == ["-", "three_q@center", "front@right", "box@right", "-"]
    assert p["lower_thirds"] == ["-", "-", "lt2.png", "-", "-"]
    assert len(p["transitions"]) == 4 and p["transitions"][0] == "fade"
    assert p["delay"] == 4.0


def test_assemble_without_cards():
    p = be.assemble(SCENES, ["1.png", "2.png", "3.png"], None, 0.5)
    assert p["durations"] == ["10.500", "20.500", "30.000"]
    assert p["delay"] == 0.0 and len(p["transitions"]) == 2


def test_scene_image_prefers_hd(tmp_path):
    (tmp_path / "bg_hd").mkdir()
    Image.new("RGB", (5120, 2880)).save(tmp_path / "bg_hd" / "sc01.png")
    assert be.scene_image(str(tmp_path), 1, {}, True).endswith("sc01.png")


def test_scene_image_rejects_small_hd(tmp_path):
    (tmp_path / "bg_hd").mkdir()
    Image.new("RGB", (1344, 768)).save(tmp_path / "bg_hd" / "sc01.png")
    with pytest.raises(SystemExit):
        be.scene_image(str(tmp_path), 1, {}, False)


def test_scene_image_require_hd_missing(tmp_path):
    with pytest.raises(SystemExit):
        be.scene_image(str(tmp_path), 1, {}, True)
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_build_episode.py -q`
Expected: FAIL — `AttributeError: module 'build_episode' has no attribute 'lower_third_titles'`

- [ ] **Step 3: `Projects/build_episode.py`-ı tam əvəz et**

```python
"""Add'im 27 / FAZA F - scenes.json -> final MP4 (montage.py cagirisini qurur).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\build_episode.py Episodes\\<slug> [--srt] [--cards]
                                     [--require-hd] [--music Music\\bg.mp3] [--dry]
--cards: 4 s intro + 6 s outro + bolme basliqlari; narration ve SRT INTRO_S qeder surusur.
--require-hd: her sehne ucun bg_hd\\scNN.png (>= 3840x2160) mecburidir (A6).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MONTAGE = os.path.join(HERE, "_ffmpeg", "montage.py")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(MONTAGE))
import cards  # noqa: E402
from montage import SPRITE_DIR, XFADE  # noqa: E402
from motion import transitions_for  # noqa: E402
from timeline import (INTRO_S, OUTRO_S, display_title, first_of_section,  # noqa: E402
                      montage_total, plan_timeline, shift_srt)

MIN_HD = (3840, 2160)
FONTS_DIR = r"C:\YouTubeAI\Assets\fonts"


def scene_image(ep_dir: str, n: int, scene: dict, require_hd: bool) -> str:
    hd = os.path.join(ep_dir, "bg_hd", f"sc{n:02d}.png")
    if os.path.isfile(hd):
        with Image.open(hd) as im:
            if im.width < MIN_HD[0] or im.height < MIN_HD[1]:
                raise SystemExit(f"{hd} {im.width}x{im.height} < {MIN_HD[0]}x{MIN_HD[1]} (A6)")
        return hd
    if require_hd:
        raise SystemExit(f"{hd} yoxdur - once upscale_bgs.py isledin")
    img = scene.get("bg") or os.path.join(ep_dir, "bg", f"sc{n:02d}.png")
    if not os.path.isfile(img):
        raise SystemExit(f"fon yoxdur: {img} - once render_bgs.py isledin")
    return img


def lower_third_titles(scenes: list[dict]) -> list[str | None]:
    return [display_title(s["section"]) if first and not s["section"].lower().startswith("hook") else None
            for s, first in zip(scenes, first_of_section(scenes))]


def make_cards(ep_dir: str, topic: str, scenes: list[dict], images: list[str]) -> dict:
    cdir = os.path.join(ep_dir, "cards")
    os.makedirs(cdir, exist_ok=True)
    lts = [cards.lower_third(t, os.path.join(cdir, f"lt_{i:02d}.png")) if t else "-"
           for i, t in enumerate(lower_third_titles(scenes), 1)]
    return {"intro": cards.intro_card(topic, images[0], os.path.join(SPRITE_DIR, "front.png"),
                                      os.path.join(cdir, "intro.png")),
            "outro": cards.outro_card(images[-1], os.path.join(SPRITE_DIR, "happy.png"),
                                      os.path.join(cdir, "outro.png")),
            "lower_thirds": lts}


def assemble(scenes: list[dict], images: list[str], card_paths: dict | None, xfade: float) -> dict:
    durs = [float(s["duration"]) for s in scenes]
    sprites = [s.get("sprite_token", "-") for s in scenes]
    sections = [s["section"] for s in scenes]
    if card_paths is None:
        return {"images": list(images), "sprites": sprites, "lower_thirds": ["-"] * len(scenes),
                "durations": [f"{d:.3f}" for d in plan_timeline(durs, xfade)],
                "transitions": transitions_for(sections), "delay": 0.0}
    return {"images": [card_paths["intro"], *images, card_paths["outro"]],
            "sprites": ["-", *sprites, "-"],
            "lower_thirds": ["-", *card_paths["lower_thirds"], "-"],
            "durations": [f"{d:.3f}" for d in plan_timeline(durs, xfade, INTRO_S, OUTRO_S)],
            "transitions": transitions_for(["__intro__", *sections, "__outro__"]),
            "delay": INTRO_S}


def srt_arg(ep_dir: str, delay: float) -> str:
    srt = os.path.join(ep_dir, "narration.srt")
    if not os.path.isfile(srt):
        raise SystemExit("narration.srt tapilmadi - once make_srt.py isledin")
    if delay <= 0:
        return srt
    shifted = os.path.join(ep_dir, "narration.shifted.srt")
    with open(srt, encoding="utf-8") as f, open(shifted, "w", encoding="utf-8", newline="\n") as g:
        g.write(shift_srt(f.read(), delay))
    return shifted


def montage_cmd(plan: dict, narration: str, out: str) -> list[str]:
    cmd = [sys.executable, MONTAGE, "--images", *plan["images"], "--durations", *plan["durations"],
           "--sprites", *plan["sprites"], "--lower-thirds", *plan["lower_thirds"],
           "--audio-delay", f"{plan['delay']:.3f}", "--audio", narration, "--out", out]
    return cmd + (["--transitions", *plan["transitions"]] if plan["transitions"] else [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--out", help="default: Episodes\\<slug>\\<slug>.mp4")
    ap.add_argument("--srt", action="store_true", help="narration.srt yandirilir")
    ap.add_argument("--cards", action="store_true", help="intro/outro + bolme basliqlari")
    ap.add_argument("--require-hd", action="store_true")
    ap.add_argument("--music")
    ap.add_argument("--dry", action="store_true", help="yalniz emri cap et")
    a = ap.parse_args()

    ep = a.episode_dir
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        scenes = json.load(f)["scenes"]
    slug = os.path.basename(os.path.normpath(ep))
    meta_path = os.path.join(ep, "meta.json")
    topic = json.load(open(meta_path, encoding="utf-8")).get("topic", slug) if os.path.isfile(meta_path) else slug
    narration = os.path.join(ep, "narration.wav")
    if not os.path.isfile(narration):
        raise SystemExit("narration.wav tapilmadi - once tts_gen.py isledin")

    images = [scene_image(ep, i, s, a.require_hd) for i, s in enumerate(scenes, 1)]
    plan = assemble(scenes, images, make_cards(ep, topic, scenes, images) if a.cards else None, XFADE)
    out = a.out or os.path.join(ep, f"{slug}.mp4")
    cmd = montage_cmd(plan, narration, out)
    if a.srt:
        cmd += ["--srt", srt_arg(ep, plan["delay"]), "--fontsdir", FONTS_DIR]
    if a.music:
        if not os.path.isfile(a.music):
            raise SystemExit("musiqi tapilmadi: " + a.music)
        cmd += ["--music", a.music]

    total = montage_total([float(d) for d in plan["durations"]], XFADE)
    print(f"[27] {len(scenes)} sehne (+kartlar: {bool(a.cards)}), {total / 60:.2f} deq -> {out}")
    if a.dry:
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testlər (bütün dəst)**

Run: `Projects/.venv/Scripts/python.exe -m pytest -q`
Expected: hamısı PASS.

- [ ] **Step 5: Mövcud epizodu yeni keyfiyyətlə yenidən qur** (fonlar Task 6-da boyüdülüb; Bash `run_in_background: true`; render müddətini ölç)

```bash
cd /c/YouTubeAI && time Projects/.venv/Scripts/python.exe Projects/build_episode.py Episodes/trademark-copyright-patent \
  --srt --cards --require-hd --out Episodes/trademark-copyright-patent/faza1_test.mp4
```
Sonra:
```bash
Projects/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'Projects'); import checks; print(checks.final_video_problems('Episodes/trademark-copyright-patent/faza1_test.mp4'))"
```
Expected: `[]`. Render müddəti > 30 dəq olarsa (spec risk §8) — `motion.KB_W, KB_H = 3840, 2160`-ə endir, `upscale_bgs.HD_W/HD_H`-ı da uyğunlaşdır, qeyd et.

- [ ] **Step 6: Kadrları çıxar, istifadəçiyə göstər**

```bash
cd /c/YouTubeAI && for t in 2 30 120 300; do ffmpeg -y -v error -ss $t -i Episodes/trademark-copyright-patent/faza1_test.mp4 -frames:v 1 Temp/f$t.png; done
```
4 PNG-ni Read tool ilə aç və köhnə `f120.png` ilə müqayisəni istifadəçiyə təqdim et. **İstifadəçi təsdiqi alınmadan Task 11-ə keçmə** (keyfiyyət düzəlişlərinin əsas məqsədi budur).

- [ ] **Step 7: Commit**

```bash
git add Projects/build_episode.py Projects/tests/test_build_episode.py
git commit -m "feat: build_episode - HD backgrounds, intro/outro cards, lower-thirds, transitions"
```

---

### Task 11: `script_gen.py --extend` + uzunluq riyaziyyatı

**Files:**
- Modify: `Projects/script_gen.py` (import-lar, `generate`, `main`; yeni funksiyalar)
- Test: `Projects/tests/test_script_gen.py`

**Interfaces:**
- Produces: `LENGTH_MARGIN = 1.05`, `words_to_add(current: int, min_seconds: float, wpm: float = WPM, margin: float = LENGTH_MARGIN) -> int`, `words_for_seconds(seconds: float, wpm: float = WPM, margin: float = 1.10) -> int`, `teaching_headings(markdown) -> list[str]`, `insert_before(markdown, anchor, block) -> str`, `extend(topic, markdown, words, domains, **llm_kw) -> tuple[str, str]`; `generate(...)` indi `tuple[str, list[str]]` qaytarır; CLI `--extend SOZ`; default `--words 2150`; `meta.json`-da `"domains"`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_script_gen.py`

```python
import pytest

import script_gen as sg

MD = """# T

## Hook

Hi.

## Section 1: One

a b c

## Section 2: Two

d e

## Common Mistakes

x

## Recap

y
"""


def test_words_to_add():
    assert sg.words_to_add(1500, 600) == 590     # ceil(600/60*199*1.05)=2090
    assert sg.words_to_add(2500, 600) == 0


def test_words_for_seconds():
    assert sg.words_for_seconds(30) == 110       # ceil(0.5*199*1.10)


def test_teaching_headings():
    assert sg.teaching_headings(MD) == ["Section 1: One", "Section 2: Two"]


def test_insert_before_common_mistakes():
    out = sg.insert_before(MD, "## Common Mistakes", "## Section 3: Three\n\nnew text")
    assert out.index("## Section 3: Three") < out.index("## Common Mistakes")
    assert "d e\n\n## Section 3: Three\n\nnew text\n\n## Common Mistakes" in out


def test_insert_before_missing_anchor():
    with pytest.raises(ValueError):
        sg.insert_before("# x", "## Common Mistakes", "b")
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_script_gen.py -q`
Expected: FAIL — `AttributeError: ... 'words_to_add'`

- [ ] **Step 3: Import və sabitlər** — `Projects/script_gen.py`-da `import argparse` blokuna `import math` əlavə et və `SHORT_RATIO` sətrindən sonra:

```python
LENGTH_MARGIN = 1.05  # TTS bosluqlarina ve tehmin xetasina ehtiyat
```

- [ ] **Step 4: Yeni funksiyalar** — `check_headings` funksiyasından sonra əlavə et:

```python
def words_to_add(current: int, min_seconds: float, wpm: float = WPM,
                 margin: float = LENGTH_MARGIN) -> int:
    """min_seconds danisiq ucun catismayan soz sayi (0 = kifayetdir)."""
    return max(0, math.ceil(min_seconds / 60.0 * wpm * margin) - current)


def words_for_seconds(seconds: float, wpm: float = WPM, margin: float = 1.10) -> int:
    return math.ceil(seconds / 60.0 * wpm * margin)


def teaching_headings(markdown: str) -> list[str]:
    return re.findall(r"^## (Section \d+: .+)$", markdown, flags=re.M)


def insert_before(markdown: str, anchor: str, block: str) -> str:
    idx = markdown.find("\n" + anchor)
    if idx < 0:
        raise ValueError(f"anchor tapilmadi: {anchor}")
    return markdown[:idx].rstrip() + "\n\n" + block.strip() + "\n" + markdown[idx:]
```

- [ ] **Step 5: `EXTEND_USER` və `extend()`** — `WRITE_USER`-dən sonra prompt, `generate`-dən sonra funksiya:

```python
EXTEND_USER = """Topic: {topic}

The video already has these teaching sections:
{existing}

Plan ONE additional teaching section that deepens the topic without repeating any of them.
Its analogy must live in an everyday domain different from all of these: {domains}.
Return JSON only:
{{"title": "short title, max 5 words", "idea": "the one core idea, one sentence",
  "domain": "the everyday world the analogy lives in, two or three words",
  "analogy": "the everyday analogy used, one sentence",
  "example": "a realistic mini-example, one sentence"}}"""
```

```python
def extend(topic: str, markdown: str, words: int, domains: list[str], **llm_kw) -> tuple[str, str]:
    """Movcud skripte Common Mistakes-den evvel yeni tedris bolmesi elave edir -> (skript, domain)."""
    existing = teaching_headings(markdown)
    sec = chat_json(SYSTEM, EXTEND_USER.format(topic=topic, existing="\n".join(existing) or "(none)",
                                               domains=", ".join(domains) or "(unknown)"),
                    max_tokens=600, **llm_kw)
    heading = f"Section {len(existing) + 1}: {str(sec.get('title', 'One More Thing')).strip()}"
    guidance = (f"Core idea: {sec.get('idea', '')}\n"
                f"Use ONLY this analogy domain: {sec.get('domain', '')}\n"
                f"The analogy: {sec.get('analogy', '')}\n"
                f"The mini-example: {sec.get('example', '')}\n"
                f"Teach the one idea, make it concrete, then hand off to the next section.")
    print(f"  [{heading}] {words} soz  <{sec.get('domain', '')}>")
    body = _write_block(topic, "\n".join(existing + [heading]), heading, words, guidance,
                        "Every other section is already written. Do not repeat their ideas or analogies.",
                        **llm_kw)
    return insert_before(markdown, "## Common Mistakes", f"## {heading}\n\n{body}"), \
        str(sec.get("domain", "")).strip()
```

- [ ] **Step 6: `generate` domains qaytarsın** — imzanı və sonunu dəyiş:

```python
def generate(topic: str, words: int, **llm_kw) -> tuple[str, list[str]]:
```
və sonuncu sətir `return "\n\n".join(parts)` →

```python
    return "\n\n".join(parts), domains
```

- [ ] **Step 7: `main` — `--extend`, default 2150, meta-da domains**

`ap.add_argument("--words", type=int, default=1850)   # ~10 deq @ 199 wpm` sətrini əvəz et:

```python
    ap.add_argument("--words", type=int, default=2150)   # ~10.8 deq @ 199 wpm
    ap.add_argument("--extend", type=int, metavar="SOZ",
                    help="movcud script.md-ye bu qeder sozluk yeni tedris bolmesi elave et")
```

`out_dir = ...` / `script_path = ...` sətirlərindən dərhal sonra (mövcudluq yoxlamasından əvvəl) əlavə et:

```python
    if a.extend:
        run_extend(a, out_dir, script_path)
        return
```

`script = generate(...)` çağırışını `script, domains = generate(...)` et və `json.dump({...})` lüğətinə `"domains": domains,` əlavə et.

`main`-dən əvvəl yeni funksiya:

```python
def run_extend(a: argparse.Namespace, out_dir: str, script_path: str) -> None:
    if not os.path.isfile(script_path):
        raise SystemExit("uzatmaq ucun script.md yoxdur: " + script_path)
    meta_path = os.path.join(out_dir, "meta.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.isfile(meta_path) else {}
    print(f"[22+] skript uzadilir: +{a.extend} soz")
    try:
        script, domain = extend(a.topic, open(script_path, encoding="utf-8").read(), a.extend,
                                meta.get("domains", []), provider=a.provider, model=a.model,
                                temperature=a.temperature)
    except (LLMError, ValueError) as e:
        raise SystemExit("uzatma xetasi: " + str(e)) from e
    n = word_count(script)
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script.rstrip() + "\n")
    meta = {**meta, "words": n, "est_minutes": round(n / WPM, 1),
            "domains": [*meta.get("domains", []), domain]}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"  {n} soz  ~{n / WPM:.1f} deq  -> {script_path}")
```

- [ ] **Step 8: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest -q`
Expected: hamısı PASS.

- [ ] **Step 9: Real `--extend` sınağı** (köhnə epizodun surətində; ~$0.005)

```bash
cd /c/YouTubeAI && mkdir -p Episodes/_extend_test && cp Episodes/trademark-copyright-patent/{script.md,meta.json} Episodes/_extend_test/ && \
Projects/.venv/Scripts/python.exe Projects/script_gen.py "Trademark vs Copyright vs Patent" --slug _extend_test --extend 300 && \
grep -n "^## " Episodes/_extend_test/script.md
```
Expected: `## Section 5: ...` `## Common Mistakes`-dən əvvəl; söz sayı ~1550 → ~1850+. Sonra `rm -rf Episodes/_extend_test`.

- [ ] **Step 10: Commit**

```bash
git add Projects/script_gen.py Projects/tests/test_script_gen.py
git commit -m "feat: script_gen --extend adds a teaching section; length math helpers"
```

---

### Task 12: `publish_pack.py` — YouTube paketi

**Files:**
- Create: `Projects/publish_pack.py`
- Test: `Projects/tests/test_publish_pack.py`

**Interfaces:**
- Consumes: `llm.chat_json`, `llm.add_provider_arg`, `timeline.INTRO_S/OUTRO_S/section_starts/display_title`, `cards.thumbnail`.
- Produces: `fmt_ts(sec) -> str`, `chapters(scenes, intro_s, total_s, min_len=10.0) -> list[tuple[float, str]]`, `fit_tags(tags, limit=500) -> list[str]`, `pick_title(titles) -> str`, `description(summary, chaps, hashtags) -> str`, `pick_thumb_bg(paths) -> str`, `pack_problems(ydir) -> list[str]`; CLI `publish_pack.py <episode_dir> [--provider P]` → `youtube/title.txt`, `title_variants.txt`, `description.txt`, `tags.txt`, `thumbnail.png`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_publish_pack.py`

```python
from PIL import Image

import publish_pack as pp

SCENES = [{"section": "Hook", "duration": 10}, {"section": "Hook", "duration": 10},
          {"section": "Section 1: A", "duration": 30}, {"section": "Section 2: B", "duration": 5},
          {"section": "Recap", "duration": 40}, {"section": "Call to Action", "duration": 20}]


def test_fmt_ts():
    assert pp.fmt_ts(0) == "00:00"
    assert pp.fmt_ts(754.2) == "12:34"
    assert pp.fmt_ts(3725) == "1:02:05"


def test_chapters_start_at_zero_and_drop_short():
    assert pp.chapters(SCENES, 4.0, 125.0) == [
        (0.0, "Hook"), (24.0, "A"), (59.0, "Recap"), (99.0, "Call to Action")]


def test_chapters_need_three():
    assert pp.chapters(SCENES[:3], 4.0, 60.0) == []


def test_fit_tags_dedupes_and_limits():
    tags = ["Trademark", "trademark", "a, b"] + ["x" * 100] * 10
    out = pp.fit_tags(tags, limit=120)
    assert out[:2] == ["Trademark", "a b"]
    assert sum(len(t) for t in out) + len(out) - 1 <= 120


def test_pick_title():
    assert pp.pick_title(["x" * 90, "Good Title"]) == "Good Title"
    assert len(pp.pick_title(["word " * 30])) <= 70


def test_description_has_chapters():
    d = pp.description("Sum.", [(0.0, "Hook"), (24.0, "A"), (59.0, "Recap")], ["eli5", "#business"])
    assert "00:00 Hook" in d and "00:24 A" in d and "#eli5 #business" in d


def test_pack_problems(tmp_path):
    (tmp_path / "title.txt").write_text("T", encoding="utf-8")
    (tmp_path / "description.txt").write_text("00:00 Hook", encoding="utf-8")
    (tmp_path / "tags.txt").write_text("a,b", encoding="utf-8")
    Image.new("RGB", (1280, 720)).save(tmp_path / "thumbnail.png")
    assert pp.pack_problems(str(tmp_path)) == []
    Image.new("RGB", (100, 100)).save(tmp_path / "thumbnail.png")
    assert pp.pack_problems(str(tmp_path))
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_publish_pack.py -q`
Expected: FAIL — `No module named 'publish_pack'`

- [ ] **Step 3: `Projects/publish_pack.py` yaz**

```python
"""FAZA F 5 - YouTube paketi: youtube\\title.txt, title_variants.txt, description.txt (chapters),
tags.txt, thumbnail.png (1280x720).
Istifade:
  Projects\\.venv\\Scripts\\python Projects\\publish_pack.py Episodes\\<slug> [--provider openai]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from PIL import Image, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cards  # noqa: E402
from llm import LLMError, add_provider_arg, chat_json  # noqa: E402
from timeline import INTRO_S, OUTRO_S, display_title, section_starts  # noqa: E402

TITLE_MAX = 70
TAGS_MAX = 500
MIN_CHAPTER_S = 10.0   # YouTube: her chapter >= 10 s, en az 3 chapter, ilki 00:00
THUMB_SIZE = (1280, 720)
SPRITE_HD = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"

SYSTEM = """You write YouTube metadata for an ELI5 Business explainer channel hosted by a cartoon owl.
Honest, specific, curiosity-driven. Never promise anything the video does not deliver.
No emojis. No ALL CAPS words. No invented statistics."""

PACK_USER = """Topic: {topic}

Chapter titles in order:
{chapters}

How the video opens (narration):
{hook}

Return JSON only:
{{"titles": ["three different title options, each at most 60 characters"],
  "summary": "two or three sentences: what the viewer will understand after watching",
  "tags": ["12 to 15 search tags, lowercase, 1-4 words each"],
  "hashtags": ["three hashtags without spaces"],
  "thumb_text": "3 to 5 punchy words for the thumbnail"}}"""


def fmt_ts(sec: float) -> str:
    s = int(sec)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def chapters(scenes: list[dict], intro_s: float, total_s: float,
             min_len: float = MIN_CHAPTER_S) -> list[tuple[float, str]]:
    """Ilk chapter 00:00 (intro Hook-a daxildir); qisa chapter novbetiye yol verir."""
    kept: list[tuple[float, str]] = []
    for k, (sec, start) in enumerate(section_starts(scenes, intro_s)):
        item = (0.0 if k == 0 else start, display_title(sec))
        if kept and item[0] - kept[-1][0] < min_len:
            if len(kept) > 1:
                kept[-1] = item
            continue
        kept.append(item)
    while len(kept) > 1 and total_s - kept[-1][0] < min_len:
        kept.pop()
    return kept if len(kept) >= 3 else []


def fit_tags(tags: list, limit: int = TAGS_MAX) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    used = 0
    for raw in tags:
        t = " ".join(str(raw).replace(",", " ").split())
        if not t or t.lower() in seen:
            continue
        cost = len(t) + (1 if out else 0)
        if used + cost > limit:
            break
        out.append(t)
        seen.add(t.lower())
        used += cost
    return out


def pick_title(titles: list) -> str:
    clean = [" ".join(str(t).split()) for t in titles if str(t).strip()]
    if not clean:
        raise ValueError("LLM basliq qaytarmadi")
    fitting = [t for t in clean if len(t) <= TITLE_MAX]
    return fitting[0] if fitting else clean[0][:TITLE_MAX].rsplit(" ", 1)[0]


def description(summary: str, chaps: list[tuple[float, str]], hashtags: list) -> str:
    lines = [summary.strip(), ""]
    if chaps:
        lines += ["Chapters:"] + [f"{fmt_ts(t)} {title}" for t, title in chaps] + [""]
    tags = " ".join(h if str(h).startswith("#") else "#" + str(h).replace(" ", "") for h in hashtags)
    if tags:
        lines.append(tags)
    return "\n".join(lines).strip() + "\n"


def pick_thumb_bg(paths: list[str]) -> str:
    """En kontrastli fon (parlaqliq standart kenarlasmasi en boyuk olan)."""
    def score(p: str) -> float:
        with Image.open(p) as im:
            g = im.convert("L")
            g.thumbnail((256, 256))
            return ImageStat.Stat(g).stddev[0]
    return max(paths, key=score)


def pack_problems(ydir: str) -> list[str]:
    names = ("title.txt", "description.txt", "tags.txt", "thumbnail.png")
    missing = [f"{n} yoxdur" for n in names if not os.path.isfile(os.path.join(ydir, n))]
    if missing:
        return missing
    read = lambda n: open(os.path.join(ydir, n), encoding="utf-8").read().strip()  # noqa: E731
    problems = []
    if not 0 < len(read("title.txt")) <= TITLE_MAX:
        problems.append(f"title uzunlugu {len(read('title.txt'))} (1..{TITLE_MAX})")
    if "00:00" not in read("description.txt"):
        problems.append("description-da 00:00 chapter yoxdur")
    if len(read("tags.txt")) > TAGS_MAX:
        problems.append(f"tags {len(read('tags.txt'))} > {TAGS_MAX} simvol")
    with Image.open(os.path.join(ydir, "thumbnail.png")) as im:
        if im.size != THUMB_SIZE:
            problems.append(f"thumbnail {im.size} != {THUMB_SIZE}")
    return problems


def write_pack(ep: str, topic: str, data: dict, chaps: list[tuple[float, str]]) -> str:
    ydir = os.path.join(ep, "youtube")
    os.makedirs(ydir, exist_ok=True)
    titles = data.get("titles") or []
    files = {"title.txt": pick_title(titles) + "\n",
             "title_variants.txt": "\n".join(" ".join(str(t).split()) for t in titles) + "\n",
             "description.txt": description(str(data.get("summary", "")), chaps, data.get("hashtags") or []),
             "tags.txt": ",".join(fit_tags(data.get("tags") or [])) + "\n"}
    for name, text in files.items():
        with open(os.path.join(ydir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    bgs = sorted(glob.glob(os.path.join(ep, "bg_hd", "sc*.png"))) or \
        sorted(glob.glob(os.path.join(ep, "bg", "sc*.png")))
    cards.thumbnail(pick_thumb_bg(bgs), os.path.join(SPRITE_HD, "confident.png"),
                    str(data.get("thumb_text") or topic), os.path.join(ydir, "thumbnail.png"))
    return ydir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    add_provider_arg(ap)
    a = ap.parse_args()
    ep = a.episode_dir
    scenes = json.load(open(os.path.join(ep, "scenes.json"), encoding="utf-8"))["scenes"]
    meta = json.load(open(os.path.join(ep, "meta.json"), encoding="utf-8"))
    total = INTRO_S + sum(float(s["duration"]) for s in scenes) + OUTRO_S
    chaps = chapters(scenes, INTRO_S, total)
    try:
        data = chat_json(SYSTEM, PACK_USER.format(topic=meta["topic"],
                                                  chapters="\n".join(t for _, t in chaps),
                                                  hook=scenes[0]["narration"][:600]),
                         max_tokens=900, provider=a.provider, model=a.model, temperature=0.7)
        ydir = write_pack(ep, meta["topic"], data, chaps)
    except (LLMError, ValueError) as e:
        raise SystemExit("publish paketi xetasi: " + str(e)) from e
    problems = pack_problems(ydir)
    print(f"[F] youtube paketi -> {ydir}  chapters: {len(chaps)}")
    if problems:
        raise SystemExit("paket problemleri: " + "; ".join(problems))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest -q`
Expected: hamısı PASS.

- [ ] **Step 5: Mövcud epizodda real işlət** (~$0.002)

Run: `cd /c/YouTubeAI && Projects/.venv/Scripts/python.exe Projects/publish_pack.py Episodes/trademark-copyright-patent && cat Episodes/trademark-copyright-patent/youtube/{title.txt,description.txt,tags.txt}`
Expected: `chapters: 8` civarı, description `00:00 Hook` ilə başlayır; thumbnail-i Read tool ilə aç.

- [ ] **Step 6: Commit**

```bash
git add Projects/publish_pack.py Projects/tests/test_publish_pack.py
git commit -m "feat: publish_pack - title, chaptered description, tags, thumbnail"
```

---

### Task 13: `state.py` + `comfy.py`

**Files:**
- Create: `Projects/state.py`, `Projects/comfy.py`
- Test: `Projects/tests/test_state_comfy.py`

**Interfaces:**
- Produces: `state.now_iso() -> str`, `state.new_state(topic, slug, stage_names) -> dict`, `state.read_state(path) -> dict | None`, `state.write_state(path, state) -> None` (atomik), `state.with_stage(state, stage, **fields) -> dict` (yeni dict, orijinal dəyişmir); `comfy.API`, `comfy.is_up(timeout=3.0) -> bool`, `comfy.start(log_path) -> subprocess.Popen`, `comfy.wait_up(timeout_s=120, poll_s=2.0, probe=is_up, sleep=time.sleep) -> bool`, `comfy.stop_process(proc, timeout_s=20)`, `comfy.ComfyGuard(log_path, probe=is_up, launcher=start)` with `.before(remaining: list) -> str | None` və `.stop()`. `remaining` elementlərinin `needs_comfy: bool` atributu var (`stages.Stage`).

- [ ] **Step 1: Failing test** — `Projects/tests/test_state_comfy.py`

```python
from types import SimpleNamespace

import comfy
import state


def test_new_state_and_with_stage_is_immutable():
    s0 = state.new_state("T", "t", ["a", "b"])
    assert s0["stages"]["a"]["status"] == "pending"
    s1 = state.with_stage(s0, "a", status="done")
    assert s1["stages"]["a"]["status"] == "done"
    assert s0["stages"]["a"]["status"] == "pending"


def test_write_read_roundtrip(tmp_path):
    p = str(tmp_path / "state.json")
    assert state.read_state(p) is None
    s = state.new_state("T", "t", ["a"])
    state.write_state(p, s)
    assert state.read_state(p) == s
    assert not (tmp_path / "state.json.tmp").exists()


def test_wait_up_polls_until_ready():
    answers = iter([False, False, True])
    slept = []
    assert comfy.wait_up(timeout_s=10, poll_s=1, probe=lambda: next(answers), sleep=slept.append)
    assert slept == [1, 1]


def test_wait_up_times_out():
    assert not comfy.wait_up(timeout_s=3, poll_s=1, probe=lambda: False, sleep=lambda s: None)


class FakeProc:
    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


def test_guard_starts_only_when_needed_and_stops_after():
    up = {"v": False}
    started = []

    def launcher(log):
        started.append(log)
        up["v"] = True
        return FakeProc()

    g = comfy.ComfyGuard("log.txt", probe=lambda: up["v"], launcher=launcher)
    need, no = SimpleNamespace(needs_comfy=True), SimpleNamespace(needs_comfy=False)
    assert g.before([no, need]) is None and started == []
    assert g.before([need, no]) is None and started == ["log.txt"]
    proc = g.proc
    assert g.before([no]) is None and proc.terminated and g.proc is None


def test_guard_leaves_external_comfy_alone():
    g = comfy.ComfyGuard("log.txt", probe=lambda: True, launcher=lambda log: 1 / 0)
    assert g.before([SimpleNamespace(needs_comfy=True)]) is None and g.proc is None
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_state_comfy.py -q`
Expected: FAIL — `No module named 'comfy'`

- [ ] **Step 3: `Projects/state.py` yaz**

```python
"""Episodes\\<slug>\\state.json - merhele statuslari. Yazilis atomikdir (tmp + os.replace);
yenileme yeni dict qaytarir. Hakim hemise fayl sistemidir - bax stages.done/verify."""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_state(topic: str, slug: str, stage_names: list[str]) -> dict:
    return {"topic": topic, "slug": slug, "created": now_iso(),
            "stages": {n: {"status": "pending", "started": None, "finished": None, "error": None}
                       for n in stage_names}}


def read_state(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_state(path: str, state: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def with_stage(state: dict, stage: str, **fields) -> dict:
    new = copy.deepcopy(state)
    new["stages"][stage] = {**new["stages"].get(stage, {}), **fields}
    return new
```

- [ ] **Step 4: `Projects/comfy.py` yaz**

```python
"""ComfyUI heyat dovru. Git Bash-dan .bat isleyir deyil - birbasa venv python ile main.py.
ComfyGuard: pipeline ComfyUI-ni ozu qaldiribsa, artiq lazim olmayanda (TTS/Whisper-den evvel)
dayandirir ki 8 GB VRAM azad olsun. Kenardan acilmis ComfyUI-ye toxunmur."""
from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request

COMFY_DIR = r"C:\YouTubeAI\ComfyUI"
COMFY_PY = r"C:\YouTubeAI\ComfyUI\.venv\Scripts\python.exe"
API = "http://127.0.0.1:8188"
START_TIMEOUT_S = 120


def is_up(timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen(f"{API}/system_stats", timeout=timeout).read()
        return True
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def start(log_path: str) -> subprocess.Popen:
    log = open(log_path, "a", encoding="utf-8")
    return subprocess.Popen([COMFY_PY, "main.py", "--listen", "127.0.0.1", "--port", "8188", "--lowvram"],
                            cwd=COMFY_DIR, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def wait_up(timeout_s: float = START_TIMEOUT_S, poll_s: float = 2.0, probe=is_up, sleep=time.sleep) -> bool:
    waited = 0.0
    while True:
        if probe():
            return True
        if waited + poll_s > timeout_s:
            return False
        sleep(poll_s)
        waited += poll_s


def stop_process(proc, timeout_s: float = 20) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()


class ComfyGuard:
    def __init__(self, log_path: str, probe=is_up, launcher=start):
        self.log_path = log_path
        self.probe = probe
        self.launcher = launcher
        self.proc = None

    def before(self, remaining: list) -> str | None:
        """Novbeti merheleden evvel cagirilir. Xeta mesaji ve ya None qaytarir."""
        if remaining and remaining[0].needs_comfy:
            if self.probe():
                return None
            self.proc = self.launcher(self.log_path)
            if not wait_up(probe=self.probe):
                return f"ComfyUI {START_TIMEOUT_S} s-de qalxmadi - bax: {self.log_path}"
        elif self.proc is not None and not any(s.needs_comfy for s in remaining):
            self.stop()
        return None

    def stop(self) -> None:
        if self.proc is not None:
            stop_process(self.proc)
            self.proc = None
```

- [ ] **Step 5: Testlər**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_state_comfy.py -q`
Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add Projects/state.py Projects/comfy.py Projects/tests/test_state_comfy.py
git commit -m "feat: atomic episode state + ComfyUI lifecycle guard"
```

---

### Task 14: `stages.py` + `pipeline.py` + `run.py`

**Files:**
- Create: `Projects/stages.py`, `Projects/pipeline.py`, `run.py`
- Test: `Projects/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `checks.duration/final_video_problems`, `script_gen.EPISODES/slugify/word_count/check_headings/words_to_add/words_for_seconds`, `publish_pack.pack_problems`, `state.*`, `comfy.ComfyGuard`.
- Produces: `stages.ROOT`, `stages.PY: dict[str,str]`, `stages.Ctx(topic, slug, ep_dir, words, music, min_seconds, provider)` + `.p(*parts)`, `stages.Stage(name, command, done, verify, needs_comfy=False)`, `stages.STAGES` (8 mərhələ: `script_gen, scene_plan, render_bgs, upscale_bgs, tts_gen, make_srt, build_episode, publish`), `stages.stage_index(name) -> int`; `pipeline.Gate(status, message="", restart_at="")`, `pipeline.run_stage(stage, ctx, force, log_dir) -> list[str]`, `pipeline.invalidate_after_script(ep_dir, slug) -> None`, `pipeline.run_pipeline(ctx, state_path, stages=STAGES, from_idx=None, runner=run_stage, gates=None, comfy=None) -> int`, `pipeline.parse_args(argv) -> Namespace`, `pipeline.main(argv=None) -> int`.

- [ ] **Step 1: Failing test** — `Projects/tests/test_pipeline.py`

```python
import os

import pipeline as pl
import stages as st
import state


def _ctx(tmp_path, **kw):
    base = dict(topic="T", slug="t", ep_dir=str(tmp_path), words=2150, music=None,
                min_seconds=600.0, provider="openai")
    base.update(kw)
    return st.Ctx(**base)


def test_stage_order():
    assert [s.name for s in st.STAGES] == ["script_gen", "scene_plan", "render_bgs", "upscale_bgs",
                                           "tts_gen", "make_srt", "build_episode", "publish"]
    assert [s.name for s in st.STAGES if s.needs_comfy] == ["render_bgs", "upscale_bgs"]


def test_commands(tmp_path):
    ctx = _ctx(tmp_path, music="m.mp3")
    cmd = st.STAGES[0].command(ctx, True)
    assert cmd[0] == st.PY["projects"] and "--words" in cmd and "2150" in cmd and cmd[-1] == "--force"
    assert st.STAGES[4].command(ctx, False)[0] == st.PY["tts"]
    assert st.STAGES[5].command(ctx, False)[0] == st.PY["whisper"]
    build = st.STAGES[6].command(ctx, False)
    assert "--cards" in build and "--require-hd" in build and build[-2:] == ["--music", "m.mp3"]


def test_parse_args_requires_topic_or_resume():
    assert pl.parse_args(["Topic"]).words == 2150
    assert pl.parse_args(["--resume", "t", "--from", "build_episode"]).from_stage == "build_episode"


def test_invalidate_after_script(tmp_path):
    for d in ("bg", "bg_hd", "audio", "cards", "youtube"):
        (tmp_path / d).mkdir()
    for f in ("scenes.json", "narration.wav", "narration.srt", "t.mp4", "script.md"):
        (tmp_path / f).write_text("x")
    pl.invalidate_after_script(str(tmp_path), "t")
    assert sorted(os.listdir(tmp_path)) == ["script.md"]


def _fake_stage(name, done):
    return st.Stage(name, lambda c, f: ["x"], lambda c: done, lambda c: [])


def test_run_pipeline_skips_done_and_records_failure(tmp_path):
    stages = [_fake_stage("a", True), _fake_stage("b", False), _fake_stage("c", False)]
    ran = []

    def runner(stage, ctx, force, log_dir):
        ran.append(stage.name)
        return ["boom"] if stage.name == "c" else []

    path = str(tmp_path / "state.json")
    rc = pl.run_pipeline(_ctx(tmp_path), path, stages=stages, runner=runner, gates={})
    s = state.read_state(path)
    assert rc == 1 and ran == ["b", "c"]
    assert [s["stages"][n]["status"] for n in "abc"] == ["done", "done", "failed"]
    assert s["stages"]["c"]["error"] == "boom"


def test_run_pipeline_from_forces_rerun(tmp_path):
    stages = [_fake_stage("a", True), _fake_stage("b", True)]
    seen = []
    rc = pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "s.json"), stages=stages, from_idx=1,
                         runner=lambda s, c, f, l: seen.append((s.name, f)) or [], gates={})
    assert rc == 0 and seen == [("b", True)]


def test_gate_restart_jumps_back(tmp_path):
    stages = [_fake_stage("a", False), _fake_stage("b", False)]
    seen = []
    calls = {"n": 0}

    def gate(ctx, log_dir, attempt):
        calls["n"] += 1
        return pl.Gate("restart", "short", "a") if attempt == 0 else pl.Gate("ok")

    rc = pl.run_pipeline(_ctx(tmp_path), str(tmp_path / "s.json"), stages=stages,
                         runner=lambda s, c, f, l: seen.append(s.name) or [], gates={"b": gate})
    assert rc == 0 and seen == ["a", "b", "a", "b"] and calls["n"] == 2
```

- [ ] **Step 2: Fail yoxla**

Run: `Projects/.venv/Scripts/python.exe -m pytest Projects/tests/test_pipeline.py -q`
Expected: FAIL — `No module named 'pipeline'`

- [ ] **Step 3: `Projects/stages.py` yaz**

```python
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


def verify_srt(ctx: Ctx) -> list[str]:
    from script_gen import word_count
    got = len(json.loads(_read(ctx.p("narration.words.json"))))
    want = word_count(_read(ctx.p("script.md")))
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
          lambda c: os.path.isfile(c.p("narration.wav")) and all_exist(numbered(c, "audio", ".wav")),
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
```

- [ ] **Step 4: `Projects/pipeline.py` yaz**

```python
"""FAZA F orchestrator: movzu -> hazir video + youtube\\ paketi.
Istifade (koku qovluqdan):
  python run.py "Movzu" [--words 2150] [--music Music\\x.mp3]
  python run.py --resume <slug> [--from build_episode]
Her merhele oz venv-i ile subprocess kimi isleyir; log: Episodes\\<slug>\\logs\\<merhele>.log.
Merhele "bitib" = fayl sistemi + yoxlama; state.json yalniz jurnaldir.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import duration  # noqa: E402
from comfy import ComfyGuard  # noqa: E402
from script_gen import EPISODES, slugify, word_count, words_for_seconds, words_to_add  # noqa: E402
from stages import PROJ, PY, ROOT, STAGES, Ctx, stage_index  # noqa: E402
from state import new_state, now_iso, read_state, with_stage, write_state  # noqa: E402

DEFAULT_WORDS = 2150
MIN_SECONDS = 600.0
MAX_EXTENSIONS = 2
INVALIDATE_DIRS = ("bg", "bg_hd", "audio", "cards", "youtube")
INVALIDATE_FILES = ("scenes.json", "narration.wav", "narration.srt", "narration.words.json",
                    "narration.shifted.srt")


@dataclass(frozen=True)
class Gate:
    status: str            # "ok" | "fail" | "restart"
    message: str = ""
    restart_at: str = ""


def _logged_call(cmd: list[str], log: str) -> int:
    with open(log, "a", encoding="utf-8") as lf:
        lf.write(f"\n[{now_iso()}] $ {' '.join(cmd)}\n")
        lf.flush()
        return subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT)


def run_stage(stage, ctx: Ctx, force: bool, log_dir: str) -> list[str]:
    log = os.path.join(log_dir, f"{stage.name}.log")
    rc = _logged_call(stage.command(ctx, force), log)
    return [f"exit {rc} - bax: {log}"] if rc else stage.verify(ctx)


def extend_script(ctx: Ctx, words: int, log_dir: str) -> list[str]:
    log = os.path.join(log_dir, "script_extend.log")
    cmd = [PY["projects"], os.path.join(PROJ, "script_gen.py"), ctx.topic, "--slug", ctx.slug,
           "--extend", str(words), "--provider", ctx.provider]
    rc = _logged_call(cmd, log)
    return [f"skript uzadilmadi (exit {rc}) - bax: {log}"] if rc else []


def invalidate_after_script(ep_dir: str, slug: str) -> None:
    """Skript deyisdi -> sehne nomreleri surusur; skriptden sonraki her sey silinir."""
    for d in INVALIDATE_DIRS:
        shutil.rmtree(os.path.join(ep_dir, d), ignore_errors=True)
    for f in (*INVALIDATE_FILES, f"{slug}.mp4"):
        p = os.path.join(ep_dir, f)
        if os.path.isfile(p):
            os.remove(p)


def word_gate(ctx: Ctx, log_dir: str, attempt: int) -> Gate:
    n = 0
    for k in range(MAX_EXTENSIONS + 1):
        with open(ctx.p("script.md"), encoding="utf-8") as f:
            n = word_count(f.read())
        need = words_to_add(n, ctx.min_seconds)
        if need == 0:
            return Gate("ok", f"skript {n} soz")
        if k == MAX_EXTENSIONS:
            break
        print(f"  skript {n} soz - {ctx.min_seconds:.0f} s ucun +{need} soz elave olunur")
        problems = extend_script(ctx, need, log_dir)
        if problems:
            return Gate("fail", problems[0])
    return Gate("fail", f"skript {n} soz - {MAX_EXTENSIONS} uzatmadan sonra da {ctx.min_seconds:.0f} s-e catmir")


def length_gate(ctx: Ctx, log_dir: str, attempt: int) -> Gate:
    secs = duration(ctx.p("narration.wav"))
    if secs >= ctx.min_seconds:
        return Gate("ok", f"narration {secs:.0f} s")
    if attempt >= MAX_EXTENSIONS:
        return Gate("fail", f"narration {secs:.0f} s < {ctx.min_seconds:.0f} s, {MAX_EXTENSIONS} cehd bitdi")
    problems = extend_script(ctx, words_for_seconds(ctx.min_seconds - secs), log_dir)
    if problems:
        return Gate("fail", problems[0])
    invalidate_after_script(ctx.ep_dir, ctx.slug)
    return Gate("restart", f"narration {secs:.0f} s qisadir - skript uzadildi, scene_plan-dan tekrar", "scene_plan")


DEFAULT_GATES = {"script_gen": word_gate, "tts_gen": length_gate}


def _save(path: str, state: dict, stage: str, **fields) -> dict:
    new = with_stage(state, stage, **fields)
    write_state(path, new)
    return new


def _step(stage, ctx, force, log_dir, runner, comfy, remaining) -> list[str]:
    if comfy is not None:
        err = comfy.before(remaining)
        if err:
            return [err]
    return runner(stage, ctx, force, log_dir)


def run_pipeline(ctx: Ctx, state_path: str, stages=STAGES, from_idx: int | None = None,
                 runner=run_stage, gates=None, comfy=None) -> int:
    gates = DEFAULT_GATES if gates is None else gates
    log_dir = ctx.p("logs")
    os.makedirs(log_dir, exist_ok=True)
    state = read_state(state_path) or new_state(ctx.topic, ctx.slug, [s.name for s in stages])
    forced = set(range(from_idx, len(stages))) if from_idx is not None else set()
    attempts: dict[str, int] = {}
    i = 0
    try:
        while i < len(stages):
            st, force = stages[i], i in forced
            forced.discard(i)
            if not force and st.done(ctx) and not st.verify(ctx):
                print(f"[{i + 1}/{len(stages)}] {st.name}: hazirdir - kecilir")
                problems = []
            else:
                print(f"[{i + 1}/{len(stages)}] {st.name} ...")
                state = _save(state_path, state, st.name, status="running", started=now_iso(), error=None)
                problems = _step(st, ctx, force, log_dir, runner, comfy, list(stages[i:]))
            gate = Gate("ok")
            if not problems and st.name in gates:
                gate = gates[st.name](ctx, log_dir, attempts.get(st.name, 0))
                attempts[st.name] = attempts.get(st.name, 0) + 1
                problems = [gate.message] if gate.status == "fail" else []
            if problems:
                _save(state_path, state, st.name, status="failed", finished=now_iso(), error="; ".join(problems))
                print(f"  XETA ({st.name}): " + "; ".join(problems))
                return 1
            state = _save(state_path, state, st.name, status="done", finished=now_iso())
            if gate.message:
                print("  " + gate.message)
            i = [s.name for s in stages].index(gate.restart_at) if gate.status == "restart" else i + 1
    finally:
        if comfy is not None:
            comfy.stop()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="FAZA F: movzu -> YouTube-a hazir video")
    ap.add_argument("topic", nargs="?")
    ap.add_argument("--slug")
    ap.add_argument("--words", type=int, default=DEFAULT_WORDS)
    ap.add_argument("--music", help="royalty-free fon musiqisi")
    ap.add_argument("--resume", metavar="SLUG")
    ap.add_argument("--from", dest="from_stage", choices=[s.name for s in STAGES])
    ap.add_argument("--min-seconds", type=float, default=MIN_SECONDS, help="yalniz test ucun asagi sal")
    ap.add_argument("--provider", default="openai")
    ap.add_argument("--motion", choices=["kenburns"], default="kenburns", help="Faza 2: ltx")
    a = ap.parse_args(argv)
    if not a.topic and not a.resume:
        ap.error("movzu ve ya --resume <slug> lazimdir")
    return a


def make_ctx(a: argparse.Namespace) -> Ctx:
    slug = a.resume or a.slug or slugify(a.topic)
    ep = os.path.join(EPISODES, slug)
    topic = a.topic or (read_state(os.path.join(ep, "state.json")) or {}).get("topic")
    meta_path = os.path.join(ep, "meta.json")
    if not topic and os.path.isfile(meta_path):     # FAZA F-den evvelki epizodlarda state.json yoxdur
        with open(meta_path, encoding="utf-8") as f:
            topic = json.load(f).get("topic")
    if not topic:
        raise SystemExit(f"movzu tapilmadi: {ep} (state.json / meta.json) - movzunu da ver")
    if a.music and not os.path.isfile(a.music):
        raise SystemExit("musiqi tapilmadi: " + a.music)
    return Ctx(topic, slug, ep, a.words, a.music and os.path.abspath(a.music), a.min_seconds, a.provider)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    ctx = make_ctx(a)
    os.makedirs(ctx.p("logs"), exist_ok=True)
    print(f"FAZA F: {ctx.topic!r} -> {ctx.ep_dir}")
    if not ctx.music:
        print("  DIQQET: --music verilmeyib - video musiqisiz olacaq")
    guard = ComfyGuard(ctx.p("logs", "comfyui.log"))
    rc = run_pipeline(ctx, ctx.p("state.json"),
                      from_idx=stage_index(a.from_stage) if a.from_stage else None, comfy=guard)
    if rc == 0:
        mp4 = ctx.p(f"{ctx.slug}.mp4")
        print(f"\nHAZIRDIR: {mp4}  ({duration(mp4) / 60:.2f} deq)\n  YouTube paketi: {ctx.p('youtube')}")
    return rc
```

- [ ] **Step 5: `run.py` yaz** (kök qovluq)

```python
"""FAZA F giris noqtesi:  python run.py "Movzu"   |   python run.py --resume <slug>
Hansi python ile cagirilsa da, ozunu Projects\\.venv ile yeniden isledir."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, "Projects", ".venv", "Scripts", "python.exe")

if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(VENV_PY):
    raise SystemExit(subprocess.call([VENV_PY, os.path.abspath(__file__), *sys.argv[1:]]))

sys.path.insert(0, os.path.join(ROOT, "Projects"))
from pipeline import main  # noqa: E402

raise SystemExit(main())
```

- [ ] **Step 6: Testlər (bütün dəst)**

Run: `Projects/.venv/Scripts/python.exe -m pytest -q`
Expected: hamısı PASS.

- [ ] **Step 7: Mövcud epizodda resume sınağı** (ComfyUI **bağlı** olsun — resume heç bir ComfyUI mərhələsini işə salmamalıdır)

Run: `cd /c/YouTubeAI && python run.py --resume trademark-copyright-patent --min-seconds 400 --from build_episode`
Expected: `script_gen ... hazirdir - kecilir` … `upscale_bgs ... kecilir`, `tts_gen` və `make_srt` keçilir, `build_episode` yenidən işləyir, `publish` işləyir; sonda `HAZIRDIR`. (`--min-seconds 400`, çünki köhnə epizod 7.97 dəq-dir.) `Episodes/trademark-copyright-patent/state.json`-da bütün mərhələlər `done`.

- [ ] **Step 8: Commit**

```bash
git add Projects/stages.py Projects/pipeline.py run.py Projects/tests/test_pipeline.py
git commit -m "feat: FAZA F orchestrator - stages, resume, length gates, run.py"
```

---

### Task 15: İnteqrasiya — yeni mini epizod (tam zəncir)

**Files:** kod dəyişikliyi yoxdur (tapılan qüsurlar öz task-ının faylında düzəldilir + test əlavə olunur).

- [ ] **Step 1: ComfyUI-ni bağla** (pipeline özü qaldırmalıdır): açıq ComfyUI prosesi varsa dayandır.

- [ ] **Step 2: Qısa epizod işlət** (~15–25 dəq; Bash `run_in_background: true`)

Run: `cd /c/YouTubeAI && python run.py "What Is Compound Interest" --slug _integ-compound --words 600 --min-seconds 120`
Qeyd: `script_gen` blok minimumlarına görə ~1000 söz yaza bilər — gözlənilən haldır.
Expected: 8 mərhələ `done`, sonda `HAZIRDIR`. `logs/comfyui.log` yaranıb (pipeline ComfyUI-ni özü qaldırıb) və TTS-dən əvvəl dayandırılıb (`tasklist | grep -i python` — ComfyUI prosesi yoxdur).

- [ ] **Step 3: Qəbul yoxlaması (A2–A4, A7, A8, A9)**

```bash
cd /c/YouTubeAI && E=Episodes/_integ-compound && \
Projects/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'Projects'); import checks, publish_pack as pp; print(checks.final_video_problems('$E/_integ-compound.mp4'), pp.pack_problems('$E/youtube'))" && \
python run.py --resume _integ-compound --min-seconds 120
```
Expected: `[] []`; ikinci `run.py` bütün 8 mərhələni `kecilir` yazır (A9) və heç nə render etmir.

- [ ] **Step 4: Tapılan qüsurlar** — hər biri üçün: əvvəl failing test, sonra düzəliş, sonra commit (`fix: ...`). Qüsur yoxdursa bu addımı "yoxdur" kimi qeyd et.

- [ ] **Step 5: Test epizodunu sil**: `rm -rf /c/YouTubeAI/Episodes/_integ-compound`

---

### Task 16: E2E — real ≥ 10 dəq epizod + istifadəçi təsdiqi

- [ ] **Step 1: Musiqi soruş** — istifadəçidən royalty-free trek yolunu soruş (`Music/` boşdur). Verilməzsə musiqisiz davam et.

- [ ] **Step 2: Tam qaçış** (Bash `run_in_background: true`; müddəti ölç)

Run: `cd /c/YouTubeAI && time python run.py "<istifadəçinin seçdiyi mövzu>" [--music Music/<trek>]`
Expected: `HAZIRDIR`, uzunluq ≥ 10.0 dəq (A1).

- [ ] **Step 3: A1–A9 cədvəli** — hər meyar üçün faktiki dəyəri yaz (ffprobe/ebur128 çıxışı, `pack_problems`, resume qaçışı). Bir meyar keçmirsə — **tamamlandı demə**; səbəbi yaz, Task 15 Step 4 kimi düzəlt.

- [ ] **Step 4: Vizual yoxlama** — `f030`, `f120`, `f300` kadrlarını çıxar (`ffmpeg -ss 30/120/300 -frames:v 1`), Read tool ilə bax, istifadəçiyə köhnə `f120.png` ilə yanaşı təqdim et. Thumbnail-i də göstər.

- [ ] **Step 5: progress.md və yaddaş** — `progress.md`: Cari vəziyyət (FAZA F Faza 1 TAMAM), ölçülmüş render müddətləri, Növbəti addım (Faza 2 LTX spec), jurnal sətri. `memory/youtube-eli5-pipeline-state.md`-i yenilə (run.py, sprites_hd, bg_hd, yeni dəyişməz qərarlar).

- [ ] **Step 6: Final commit**

```bash
git add -A && git status --short && git commit -m "docs: FAZA F phase 1 complete - progress and results"
```

---

## Spec coverage (self-review)

| Spec bölməsi | Task |
|---|---|
| §1 A1 ≥600 s | 11 (riyaziyyat), 14 (`word_gate`, `length_gate`), 16 |
| §1 A2 video format | 1, 9, 10 |
| §1 A3 48k stereo −14 LUFS | 4, 9, 1 |
| §1 A4 drift | 1, 10 |
| §1 A5 sprite böyüdülmür | 7, 9 (`Sprite.size`) |
| §1 A6 ≥3840×2160 | 6, 10 (`scene_image`), 14 (`verify` HD) |
| §1 A7 youtube paketi | 12 |
| §1 A8 dekod | 1 |
| §1 A9 resume | 13, 14, 15 |
| §2.1 orchestrator/state/atomik | 13, 14 |
| §2.2 mərhələlər + ComfyUI start/stop | 13 (`ComfyGuard`), 14 |
| §2.3 loglar, dayanma | 14 (`_logged_call`, `failed`) |
| §3.1 sprite HD, 0.42, kölgə, bob 4 px | 7, 9 |
| §3.2 fon 4x + vignette | 5, 6, 3 |
| §3.3 Ken Burns 4 növ + easing | 3 |
| §3.4 keçidlər | 3, 10 |
| §3.5 subtitr | 5, 9 (dəqiqləşdirmə #2) |
| §3.6 intro/outro/lower-third | 8, 10 (dəqiqləşdirmə #3) |
| §3.7 audio | 4, 9 |
| §4 uzunluq qaydası | 11, 14 (dəqiqləşdirmə #4) |
| §5 YouTube paketi | 12 |
| §7 test strategiyası | hər task (unit), 15 (inteqrasiya), 16 (E2E + vizual) |
| §8 risklər (render müddəti) | 10 Step 5 (ölçmə + 3840 fallback) |
