# Unique Images + Owl Intro/Outro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No repeated scene photos / owl poses, and every video opens with a topic-themed owl greeting and closes with a farewell + subscribe call.

**Architecture:** `plan.py` guarantees unique prompts (re-ask missing scenes, de-dup pass, deterministic guard) and adds intro/outro scenes (`n=0`, `n=N+1`) whose text comes from one strict-schema GPT call. Existing stages (images, owl, voice, captions, render, publish) handle them with small type checks; `images.py` adds a dHash duplicate check. Remotion gets `IntroScene`/`OutroScene` and a big owl on those scenes.

**Tech Stack:** Python 3.11 (pytest), Pillow/numpy, OpenAI gpt-4o-mini (strict json_schema) + gpt-image-2, Kokoro TTS, Remotion (TS/React).

**Spec:** `docs/superpowers/specs/2026-10-13-unique-images-intro-outro-design.md`

## Global Constraints
- Script narration is never changed; the only off-script text is the intro greeting and outro farewell.
- Photo / owl / intro-outro background are never substituted (retry, rewrite on safety rejection, else stop).
- Owl visible in every frame (bottom-right); intro/outro owl height `OWL_H_BIG = 820`.
- Intro ≥ 6.0 s, outro ≥ 10.0 s; greeting ≤ 16 words, farewell ≤ 26 words.
- dHash duplicate threshold `DUP_BITS = 8` (64-bit hash).
- Tests: `Projects\.venv\Scripts\python -m pytest -q Projects/tests`; Remotion: `cd Remotion; npx tsc --noEmit`.

---

### Task 1: Plan — no missing scenes, no duplicate prompts/poses

**Files:** Modify `Projects/plan.py`; Test `Projects/tests/test_plan.py`

**Interfaces — Produces:** `plan.DEFAULT_POSES: list[str]`, `plan.norm(s: str) -> str`, `plan.unique_guard(scenes: list[dict]) -> None` (mutates photo_prompt/owl of content scenes in place).

- [ ] Step 1: failing tests
```python
def test_missing_scenes_are_asked_again():
    calls = []
    def ask(system, user):
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        calls.append(nums)
        keep = nums if len(calls) > 1 else nums[:1]          # first call drops scenes
        return {"scenes": [{"n": n, "photo_prompt": f"photo {n}", "owl": f"pose {n}", "anim": []} for n in keep]}
    got = plan.plan_scenes(_data(3), ask=ask)["scenes"]
    assert [s["photo_prompt"] for s in got if s["type"] in ("photo", "anim")][:3] == ["photo 1", "photo 2", "photo 3"]

def test_duplicate_prompts_and_poses_are_repaired():
    def ask(system, user):
        nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
        fix = "DUPLICATE" in user
        return {"scenes": [{"n": n, "photo_prompt": f"new photo {n}" if fix else "same photo",
                            "owl": f"new pose {n}" if fix else "same pose", "anim": []} for n in nums]}
    got = [s for s in plan.plan_scenes(_data(4), ask=ask)["scenes"] if s["type"] in ("photo", "anim")]
    assert len({plan.norm(s["photo_prompt"]) for s in got}) == 4 and len({plan.norm(s["owl"]) for s in got}) == 4

def test_unique_guard_makes_leftovers_unique_from_the_scene_itself():
    scenes = [{"n": i, "type": "photo", "visual": "A phone.", "text": f"Sentence {i} here. More.",
               "photo_prompt": "x", "owl": "y"} for i in (1, 2, 3)]
    plan.unique_guard(scenes)
    assert len({plan.norm(s["photo_prompt"]) for s in scenes}) == 3
    assert len({plan.norm(s["owl"]) for s in scenes}) == 3
```
- [ ] Step 2: run → FAIL (`norm`/`unique_guard` missing, missing scenes not re-asked).
- [ ] Step 3: implement — in `plan_scenes` after batches: `missing = [s for s in scenes if s["n"] not in got]` → `_ask_batch` once more; SYSTEM gets the "different from other scenes" rule; each batch user text gets `ALREADY USED` lines (previous photo_prompts/owls); `_dedupe(...)` re-asks duplicates with `DUPLICATE of: ...` notes; `unique_guard` (photo: `photo_safe(visual) + " " + first sentence of text`; owl: next unused `DEFAULT_POSES`).
- [ ] Step 4: run full suite → PASS. Step 5: commit `feat: plan never repeats photo prompts or owl poses`.

### Task 2: Images — perceptual duplicate check

**Files:** Modify `Projects/images.py`; Test `Projects/tests/test_images.py`

**Interfaces — Produces:** `images.dhash(data: bytes) -> int`, `images.DUP_BITS = 8`, `images.VARY = " Different composition, camera angle and setting."`; photo types `images.PHOTO_TYPES = ("photo", "intro", "outro")`.

- [ ] Step 1: failing tests
```python
def test_near_duplicate_photo_is_redrawn_with_a_different_composition(tmp_path):
    ep = _ep(tmp_path, ["photo", "photo"])
    seen = []
    def gen(p):
        seen.append(p)
        return _png() if "Different composition" not in p else _png_color("red")
    images.render_photos(ep, gen=gen, workers=1, limiter=None, rewrite=None)
    assert any("Different composition" in p for p in seen)

def test_intro_and_outro_backgrounds_are_drawn(tmp_path):
    ep = _ep(tmp_path, ["intro", "photo", "outro"])
    images.render_photos(ep, gen=lambda p: _png_color(p[:2]), workers=1, limiter=None, rewrite=None)
    assert all((tmp_path / "img" / f"sc{n:02d}.png").exists() for n in (1, 2, 3))
```
(`_png_color(c)` = solid/gradient PNG distinct per input — add to the test file.)
- [ ] Step 2: FAIL. Step 3: implement — `_one` draws, computes dHash, compares to a shared lock-protected dict of existing hashes (pre-filled from `img/*.png`); distance ≤ `DUP_BITS` → raise `ValueError("dublikat")` and next attempt prompt gets `VARY`; `todo` uses `PHOTO_TYPES`. `pipeline._all("img", ..., photo_only=True)` uses `images.PHOTO_TYPES`.
- [ ] Step 4: PASS. Step 5: commit `feat: redraw near-duplicate photos; intro/outro backgrounds`.

### Task 3: Plan — intro/outro bookends

**Files:** Modify `Projects/plan.py`; Test `Projects/tests/test_plan.py`

**Interfaces — Produces:** `plan.BOOKEND_SCHEMA`, `plan.bookends(title: str, texts: list[str], ask) -> dict` with keys `greeting, farewell, bg_prompt, owl_intro, owl_outro`; `plan_scenes` output: first scene `{"n": 0, "type": "intro", ...}`, last `{"n": N+1, "type": "outro", ...}`.

- [ ] Step 1: failing tests
```python
def _ask_all(system, user):
    if "INTRO" in system:
        return {"greeting": "Hi friends! Today: how free apps make money.", "farewell": "Thanks for watching! Subscribe for more.",
                "bg_prompt": "Phones on a desk", "owl_intro": "waving hello", "owl_outro": "waving goodbye"}
    nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
    return {"scenes": [{"n": n, "photo_prompt": f"p{n}", "owl": f"o{n}", "anim": []} for n in nums]}

def test_intro_and_outro_wrap_the_content_scenes():
    got = plan.plan_scenes(_data(5), ask=_ask_all)["scenes"]
    assert got[0]["type"] == "intro" and got[0]["n"] == 0 and "Hi friends" in got[0]["text"]
    assert got[-1]["type"] == "outro" and got[-1]["n"] == 6 and "Subscribe" in got[-1]["text"]
    content = got[1:-1]
    assert [s["type"] for s in content] == plan.assign_types(5)

def test_overlong_greeting_is_cut_at_a_sentence():
    long = "Hello there friend. " + "word " * 30
    def ask(system, user):
        return {"greeting": long, "farewell": "Bye. Subscribe!", "bg_prompt": "b", "owl_intro": "w", "owl_outro": "w"}
    b = plan.bookends("T", ["x"], ask)
    assert len(b["greeting"].split()) <= plan.GREETING_MAX
```
- [ ] Step 2: FAIL. Step 3: implement `bookends` (strict schema, one retry on >limit, then `_cap` at sentence boundary / word limit; errors: balance re-raise, else one retry then raise) and wrap scenes in `plan_scenes` (skip if `data["scenes"]` already starts with intro — idempotent). `main` prints intro/outro.
- [ ] Step 4: PASS (update existing tests that index `got[0]` to content scenes). Step 5: commit `feat: owl intro greeting and outro farewell scenes`.

### Task 4: Voice min duration, render props, publish description

**Files:** Modify `Projects/voice.py`, `Projects/render.py`, `Projects/publish.py`; Tests `test_render.py`, `test_publish.py`, new `test_voice.py`

**Interfaces — Produces:** `voice.MIN_S = {"intro": 6.0, "outro": 10.0}`, `voice.pad_to(wav: np.ndarray, sr: int, seconds: float) -> np.ndarray`.

- [ ] Step 1: failing tests
```python
def test_pad_to_extends_short_bookends_with_silence():
    import numpy as np, voice
    w = voice.pad_to(np.ones(10, dtype=np.float32), 10, 3.0)
    assert len(w) == 30 and w[-1] == 0
    assert len(voice.pad_to(np.ones(50, dtype=np.float32), 10, 3.0)) == 50

def test_intro_outro_props_carry_their_background():
    data = {"scenes": [{"n": 0, "type": "intro", "section": "", "section_start": False, "anim": None, "duration": 6.0},
                       {"n": 1, "type": "outro", "section": "", "section_start": False, "anim": None, "duration": 10.0}]}
    p = render.props(data, [])
    assert p["scenes"][0]["img"] == "img/sc00.jpg" and p["scenes"][1]["img"] == "img/sc01.jpg"

def test_description_skips_the_intro_greeting():
    data = {"title": "T", "slug": "s", "scenes": [
        {"n": 0, "type": "intro", "section": "", "section_start": False, "text": "Hi!", "duration": 6},
        {"n": 1, "type": "photo", "section": "A", "section_start": True, "text": "Real start.", "duration": 5}]}
    t = publish.youtube_text(data)
    assert "Real start." in t and "Hi!" not in t
```
(`voice.py` imports kokoro lazily inside `main`, so importing it in the main venv works; numpy/soundfile exist there.)
- [ ] Step 2: FAIL. Step 3: implement (voice: pad when `s["type"] in MIN_S`; render: img for `images.PHOTO_TYPES`; publish: description from first scene whose type not intro/outro). Step 4: PASS. Step 5: commit `feat: bookend durations, props and description`.

### Task 5: Remotion IntroScene / OutroScene / big owl

**Files:** Create `Remotion/src/IntroScene.tsx`, `Remotion/src/OutroScene.tsx`; Modify `Remotion/src/types.ts`, `Episode.tsx`, `OwlLayer.tsx`, `theme.ts`; Test `Projects/tests/test_integration.py` (types parse) + `npx tsc --noEmit`.

**Interfaces — Consumes:** props scene `type: 'intro'|'outro'`, `img`. **Produces:** `IntroScene({src, title})`, `OutroScene({src})`; `Props.title: string`.

- [ ] Step 1: failing test — integration test asserts `props["title"]` and `_ts_keys("Props")` includes `title`; render.props adds `"title": data.get("title", "")`.
- [ ] Step 2: FAIL. Step 3: implement:
  - `types.ts`: `type: 'photo'|'anim'|'intro'|'outro'`; `Props` adds `title: string`.
  - `IntroScene`: blurred/darkened bg Img, "ELI5 BUSINESS" pill, title words spring up one by one, yellow underline grows; content area `paddingRight: SAFE_RIGHT + 200`.
  - `OutroScene`: same bg, red SUBSCRIBE pill springs in at 0.3 s, at 1.2 s "click" (scale 0.92) → grey "SUBSCRIBED ✓", bell 🔔 swings; "Thanks for watching!" line.
  - `Episode.SceneView`: route intro/outro; SectionTitle skipped for them.
  - `OwlLayer`: height `OWL_H_BIG` when scene type intro/outro (`theme.ts` exports it).
- [ ] Step 4: pytest + tsc PASS. Step 5: commit `feat: Remotion intro and outro scenes`.

### Task 6: Rules + E2E mini-run
- [ ] `CLAUDE.md` Prinsiplər: intro/outro exception; `progress.md` updated.
- [ ] Mini script (3 short sections) → `python run.py <mini>`; check intro/outro stills, owl in every frame, durations ≥ 6 s / ≥ 10 s, LUFS, no duplicate prompts in scenes.json.
- [ ] Commit `docs: intro/outro rule exception`.
