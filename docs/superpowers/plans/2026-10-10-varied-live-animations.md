# Varied Live Animations + Case Model Sanity + Real-Data E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Every video gets visually varied, "live" analytical animations in the spirit of
`docs/reference/video_yarat_v4.py`, and no two animations are the same. In E2E №2, `compare` was 33 of 47.
Also:
- the case model no longer produces contradictory numbers (script_gen failed on the first attempt 3 times);
- the real-data chart is proven by a full E2E.

**Root cause (animations):**
- `visuals.USER` has one example, and it is `compare` with `value: null`.
- `SYSTEM` says "If the narration has no numbers, use compare, timeline or equation".
- There is no limit on kinds; a kind may repeat back to back.

**Architecture:**
- **Python decides which kind a scene gets.** `visuals.diversify` applies a per-video share cap per kind, a ban on
  the same kind twice in a row, and ≥ 8 distinct kinds; a scene over the quota is asked again with
  `avoid=[...]`. This keeps the choice testable.
- **Remotion draws the new "live" kinds.** New files `Remotion/src/visuals/Live.tsx` and `Live2.tsx`.
- **Reference ideas carried over:**
  - a line that draws itself in time with the spoken figure;
  - a moving glowing dot and a large live value that counts in the top corner;
  - colour changes when the line falls (green → red);
  - an event label that pops up at its own point;
  - a counter that scales up while it counts;
  - a map where dots light up one by one.
- **Not carried over** (Projects/CLAUDE.md list): the invented newspaper card, the fixed CHART_PATH, the black
  card with silence, the fixed seed.

**Tech Stack:** Python 3 + pytest; Remotion 4.0.529 (React/TS); the existing `motion.ts` tokens (spring, bezier,
no linear easing).

## Global Constraints
- Every number on a chart is said in that scene (fail-closed, `visuals._said`). The new kinds follow this too.
- No bullet lists (`keypoints` is banned). No generic flow steps.
- The owl is static, stays on the right, and is never covered. Chart AREA, kicker, captions, layout are unchanged.
- The animation share stays ~60% with a cap of 70% (`ANIM_MAX`). Table/threshold are forced in the decision
  section.
- Motion tokens (`motion.ts`): entry 300–600 ms, spring/bezier, no linear easing (lint test).
- Videos are 10–12 min, −14 LUFS. Code comments are in ASCII-transliterated Azerbaijani. Every task follows TDD
  and adds a registry row with a test reference.

---

### Task 1: Diversity gate (#133)
**Files:** `Projects/visuals.py`, `Projects/quality_gate.py`; test `Projects/tests/test_visual_variety.py`
- `KIND_SHARE_MAX = 0.20`: one kind is at most 20% of the animated scenes. Forced decision/data visuals are exempt.
- `NO_REPEAT`: the same kind never appears in two consecutive animated scenes.
- `MIN_KINDS = 8` distinct kinds.
- `diversify(specs, scenes, ask)`: scenes over the quota are asked again with "avoid: compare, ..." (≤ 2 rounds).
  If they still do not pass, the scene becomes a photo (fail-safe).
- In the prompt: the single `compare` example is replaced by one example per kind. The numberless rule becomes
  "rotate through: balance, timeline, flow, versus, ..., never the same kind twice in a row".
- `quality_gate` gets a `visual_variety` check (from `scenes.json`).
- Tests:
  - `test_one_kind_never_exceeds_its_share`
  - `test_same_kind_is_never_back_to_back`
  - `test_over_quota_scene_is_asked_again_with_kinds_to_avoid`
  - `test_quality_gate_fails_a_monotonous_video`

### Task 2: "Live" chart upgrade — line/timeseries/counter (#134)
**Files:** `Remotion/src/visuals/Charts.tsx`, `DataViz.tsx`; test `Projects/tests/test_remotion_wiring.py`
- `line` and `timeseries`:
  - the line draws itself in time with the spoken points;
  - a glowing "head" dot moves along it;
  - a large live value top-right counts along (as in the reference);
  - a falling segment turns red;
  - an event label pops up at its point.
- `counter`: a scale pop from 75% → 100% while counting (reference `counter_events`).
- Tests: the static source shows that the live-head/value components exist and are wired.
  `npx tsc --noEmit` is clean. A `renderStill` probe of 3 frames per kind is viewed by eye.

### Task 3: New kinds — 6 (#135)
**Files:** `Projects/visuals.py` (KINDS, `_build`, `LIMITS`, `SYSTEM`), `Projects/motion.py` (VARIANTS),
new `Remotion/src/visuals/Live.tsx` (`Waterfall`, `Gauge`, `DotGrid`) and `Live2.tsx` (`Balance`, `Funnel`,
`Versus`), `AnalyticsScene.tsx`, `types.ts`.
Tests: `test_visuals.py` (each kind: spoken numbers pass, unspoken ones are rejected), `test_motion.py` (≥ 3
variants per kind), `test_remotion_wiring.py` (every KIND has a Remotion component).

| kind | What it shows | Numbers |
|---|---|---|
| `waterfall` | revenue → −costs → profit, bars step down | every step said; the arithmetic is checked in Python |
| `gauge` | a needle sweeps to the value; the target zone is coloured | value (+ optional target) said |
| `dotgrid` | 100 dots, X% light up (the reference map idea) | a percentage said |
| `balance` | a scale tips toward the heavier side | numberless or two said values |
| `funnel` | visitors → buyers → repeat buyers, narrowing | 3–4 said counts, decreasing |
| `versus` | two hero numbers collide with a scale pop, the winner glows | two said values or null |

### Task 4: Case model contradiction (#136)
**Files:** `Projects/case_model.py`, `Projects/script_qa.py`; test `Projects/tests/test_case_model.py`
- First **reproduce it**: run only `outline` 5 times for "Should You Raise Your Menu Prices?" (cheap, no script)
  and save the plans/model_results that came out wrong.
  - Probe symptom: "profit −$1,000 → −$16,000" when the price was raised.
  - Expected root cause: the model expression has a sign error or a missing variable, and the starting result is a
    loss.
- Fix as a deterministic `plan_problems` rule, applied at plan level before the script is written:
  - an owner who is already at a loss before the decision is not a valid case (`before` profit must be > 0);
  - the model's direction must not contradict the plan's `answer`.
  - On a violation, the outline is requested again. Exact rules are set after the reproduction.
- Tests: from the reproduced real plan JSON (fixture), e.g.
  `test_case_that_starts_at_a_loss_is_rejected_before_the_script`.

### Task 5: Full E2E — real data + new animations (#127–#136 checked together)
- The user gives a topic, or the recommended "Should You Raise Your Menu Prices?" (restaurant price series) is
  used. Run per CLAUDE.md steps 2–7.
- Extra checks:
  - timeseries is in `scenes.json`, and the frame shows real points;
  - `visual_variety` passed;
  - frames of every new kind are viewed;
  - no kind > 20%, none back to back;
  - `data_visuals` passed.
