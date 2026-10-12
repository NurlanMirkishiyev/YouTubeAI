# Analitik animasiyalar + təkrarsız kadrlar + thumbnail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Səhnələrin ~60%-i mövzuya uyğun analitik Remotion animasiyası olsun (şəkil sayı ~53 → ~21),
heç bir şəkil videoda iki dəfə görünməsin, thumbnail ayrıca və keyfiyyətli çəkilsin.

**Architecture:** `scene_plan` əvvəlcə `visuals.plan_visuals` ilə hər səhnəyə `visual` (chart spec) və ya
`null` (foto) təyin edir; yalnız foto səhnələrinə fon promptu/şəkli lazımdır. Chart spec-dəki hər rəqəm
deterministik olaraq həmin səhnənin danışığına bağlanır (`math_check.find_numbers`) — bağlanmasa chart rəqəmsiz
`keypoints`-ə, o da alınmasa fotoya düşür. Remotion `AnalyticsScene` spec-i tünd "data studio" fonunda spring
animasiyası ilə çəkir; elementlər rəqəmin səsləndirildiyi kadrda açılır (`reveal` — whisper söz vaxtı).
İntro/outro kartı səhnə fotosunu təkrar istifadə etmir (dizayn fonu). Thumbnail: gpt-image-2 **high** ilə ayrıca fon.

**Tech Stack:** Python 3.12 (pytest), Remotion 4 (React/TS), OpenAI gpt-4o-mini (dəyişmir — istifadəçi 2026-10-03), gpt-4o vision, gpt-image-2.

**İstifadəçi qərarları (2026-10-03):** model dəyişmir; animasiya payı ~60%; plan təsdiqləndi.

## Global Constraints
- Video 10–12 dəq; −14 LUFS; bayquş sağda sabit; "Hook" yoxdur; uşaqsayağı görünüş yoxdur.
- Hesab səhvi QƏTİ olmur: chart-dakı hər rəqəm səhnə danışığında olmalıdır (fail-closed).
- Təkrar kadr QƏTİ olmur: videoda hər foto bir dəfə (intro/outro kartı da səhnə fotosunu işlətmir).
- Hər problem: `progress.md` reyestri (#45–#48) + test + kod. Testlər: `Projects\.venv\Scripts\python -m pytest -q Projects/tests`.

---

### Task 1: `visuals.py` — chart spec validasiyası və seçim (#45)
**Files:** Create `Projects/visuals.py`, Test `Projects/tests/test_visuals.py`
**Produces:**
- `KINDS = ("bars","line","compare","ring","equation","flow","timeline","counter","keypoints")`
- `ANIM_SHARE = 0.6`
- `grounded_values(narration) -> set[float]` (find_numbers + `%`)
- `validate_visual(v: dict, narration: str) -> dict | None` — sxem + rəqəm bağlılığı + mətn uzunluğu; normallaşdırılmış spec
- `to_keypoints(v: dict, narration: str) -> dict | None` — rəqəmsiz ehtiyat
- `choose_animated(scores: list[float], share: float) -> set[int]` — 0-əsaslı indekslər, ən yüksək bal; ilk səhnə foto, ardıcıl 4+ animasiya yox
- `plan_visuals(scenes, topic, **llm_kw) -> list[dict | None]` — LLM (hissə-hissə) + validasiya
Testlər: rəqəmi danışıqda olmayan bars rədd → keypoints; ring 0–100; label-də rəqəm; payın 60% olması; boş LLM cavabı → hamısı foto deyil, xəta yox.

### Task 2: `scene_plan` inteqrasiyası — yalnız foto səhnələrinə fon (#45)
**Files:** Modify `Projects/scene_plan.py` (`plan`, `main`), `Projects/stages.py` (`verify_scenes`, `numbered` → foto səhnələri), Test `test_scene_plan.py`, `test_visuals.py`
- `plan(..., photo: set[int] | None)` — təkrar/ehtiyat hesabı yalnız foto səhnələrində; animasiya səhnəsində `bg_prompt=""`, `visual={...}`
- `stages.photo_numbers(ctx)`; `verify_scenes`: hər səhnədə ya `bg_prompt`, ya `visual`

### Task 3: foto mərhələləri animasiya səhnələrini ötür (#45)
**Files:** `render_bgs.py` (todo/prune/missing), `check_bgs.py` (pending), `remotion_build.prepare_public`/`episode_props`
- animasiya səhnəsinin köhnə `bg/scNN.png`, `bg_hd/scNN.png` silinir (dedupe-ə düşməsin)
Testlər: `test_render_bgs.py`, `test_remotion_build.py`

### Task 4: intro/outro kartı səhnə fotosunu təkrar etmir (#46)
**Files:** `remotion_build.episode_props` (`introBg/outroBg` = `null`), `Cards.tsx` (dizayn fonu `StudioBackdrop`)
Test: `test_no_repeats.py::test_cards_do_not_reuse_scene_photos`

### Task 5: Remotion `AnalyticsScene` + 9 komponent (#45)
**Files:** Create `Remotion/src/visuals/*.tsx` (`Studio.tsx`, `Bars.tsx`, `Line.tsx`, `Compare.tsx`, `Ring.tsx`,
`Equation.tsx`, `Flow.tsx`, `Timeline.tsx`, `Counter.tsx`, `Keypoints.tsx`, `index.tsx`), Modify `types.ts`, `Episode.tsx`
- chart sol ~62% sahədə (bayquş sağda, altyazı aşağıda), elementlər `reveal[i]` kadrında spring ilə
- yoxlama: `npx tsc --noEmit` + `remotion still` ilə hər növün kadrı vizual

### Task 6: reveal vaxtları (python) (#45)
**Files:** `remotion_build.py` — `reveal_frames(visual, words, start_s, frames) -> list[int]`
- elementin rəqəmi/etiketi danışıqda səsləndiyi an; tapılmasa bərabər paylanır
Test: `test_remotion_build.py`

### Task 7: Thumbnail keyfiyyəti (#47)
**Files:** `publish_pack.py`, `cards.py` (`thumbnail`), Test `test_publish_pack.py`, `test_cards.py`
- LLM `thumb_scene` (yazısız fon konsepti) → gpt-image-2 **high** 1536x1024, 2 variant; gpt-4o vision ən yaxşısını seçir (yazı/insan yoxdursa)
- dizayn: sol tərəfdə tünd gradient, 2 sətir yazı, açar söz `ACCENT` sarı, qalın kontur + kölgə; bayquş = `owl/intro.png` (mövzu əşyalı), yoxdursa sprite
- fon alınmasa → ən kontrastlı foto (köhnə yol), pipeline dayanmır

### Task 8: Dedupe namizəd həddi (#48)
**Files:** `bg_dedupe.py` `DUP_SIM` 0.85 → 0.80 (hakim təsdiqi qalır); Test `test_no_repeats.py`

### Task 9: E2E + sənədlər
- `CLAUDE.md` / `progress.md` (reyestr #45–#48, jurnal), bir test mövzusu ilə tam run, vizual yoxlama, commit
