# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Bu fayl **kod arxitekturası və əmrlər** üçündür. İstifadəçi qərarları, video tetiki və iş qaydaları kökdəki
> `C:\YouTubeAI\CLAUDE.md`-dədir; canlı vəziyyət `progress.md`-dədir. Burada onlar təkrarlanmır.

## Əmrlər (repo kökündən, `C:\YouTubeAI`)

```powershell
Projects\.venv\Scripts\python -m pytest -q Projects/tests                         # bütün testlər
Projects\.venv\Scripts\python -m pytest -q Projects/tests/test_visuals.py         # bir fayl
Projects\.venv\Scripts\python -m pytest -q "Projects/tests/test_visuals.py::test_number_not_in_narration_is_rejected"
python run.py "What Is Cash Flow?"                 # tam pipeline (özünü Projects\.venv-ə keçirir)
python run.py --resume <slug>                      # yarımçıq epizod: bitmiş mərhələlər fayllara görə keçilir
python run.py --resume <slug> --from render_owls   # həmin mərhələdən sonrakıların hamısını məcburi yenidən
Projects\.venv\Scripts\python Projects\quality_gate.py --write-catalog              # docs/error_classes.md-ni yenidən yaz
cd Remotion; npx tsc --noEmit                      # Remotion tip yoxlaması
cd Remotion; npm run studio                        # Remotion önizləmə
```

Uzun run-u Claude sessiyasından **WMI ilə** açın (kök CLAUDE.md addım 2) — `Start-Process` alət çağırışı ilə ölür.
Lint/formatter konfiqurasiyası yoxdur.

## Dörd ayrı Python mühiti

Mərhələlər öz venv-ləri ilə alt-proses kimi işləyir (`stages.PY`): `Projects\.venv` (əsas pipeline, testlər),
`TTS\.venv` (Kokoro, `tts_gen.py`), `Whisper\.venv` (`Whisper/make_srt.py`), `MusicGen\.venv` (Stable Audio Open,
`music_gen.py`). Bir modulu import edəndə hansı venv-də işlədiyini yoxlayın — `Projects\.venv`-də torch/kokoro yoxdur.
`upscale_bgs` ComfyUI (port 8188, `run_comfyui.bat`) tələb edir (`needs_comfy=True`; pipeline özü açır).

## Arxitektura

**Orkestr:** `run.py` → `Projects/pipeline.py::main` → `stages.STAGES` (13 `Stage`, ardıcıl). Hər `Stage` =
`command` (alt-proses əmri) + `done` (fayl sistemində nəticə varmı → resume bunun üzərində qurulub) + `verify`
(problem siyahısı; boş deyilsə mərhələ uğursuz). Vəziyyət `Episodes/<slug>/state.json` (`state.py`), mərhələ loqları
`Episodes/<slug>/logs/`. Uğursuz mərhələ 30 s sonra 2 dəfə təkrarlanır (OpenAI balansı bitibsə yox).

Mərhələlər: `script_gen → scene_plan → render_bgs → check_bgs → render_owls → upscale_bgs → tts_gen → make_srt →
captions → music_gen → build_episode → publish → quality_gate`. Sonda `pipeline.deliver()` paketi
`Hazir_Videolar/<slug>/`-a yazır (mp4 hardlink).

**Qapılar (`pipeline.DEFAULT_GATES`):** `word_gate` (script_gen-dən sonra söz sayı) və `length_gate` (tts_gen-dən
sonra danışıq saniyəsi) skripti uzadır/qısaldır və `restart` ilə `scene_plan`-a qaytarır. Skript dəyişəndə
`invalidate_after_script` sonrakı bütün artefaktları silir (səhnə nömrələri sürüşür).

**Epizod qovluğu = mərhələlər arası müqavilə** (`Episodes/<slug>/`): `script.md`, `research.json`, `meta.json`
(case model), `scenes.json` (səhnələr; `visual` açarı olan səhnə Remotion chart-ıdır, olmayan foto — `stages.photo_numbers`),
`bg/`, `bg_hd/`, `owl/`, `music.wav`, `*_qa.json` hesabatları, `<slug>.mp4`, `youtube/`, `qa/`.
Faylı oxuyub-yazan kod həmişə diskdən təzə oxuyub yalnız öz açarını yazır (reyestr #5) — `scenes.json`-u
yaddaşdakı köhnə nüsxə ilə üstdən yazmayın.

**QA möhürü:** bütün QA hesabatları `qa_stamp.write` ilə skriptin sha256-sı daxil yazılır; `quality_gate.py` möhürü
uyğun gəlməyən (köhnə) hesabatı rədd edir (fail-closed) və `qa/quality_gate.json` + `qa/self_audit.md` yazır.
Xəta sinifləri `quality_gate.ERROR_CLASSES`-dədir; `docs/error_classes.md` ondan generasiya olunur (əl ilə redaktə yox).

**Ssenari zənciri:** `script_gen.py` → `research.py` (mənbə URL-i yüklənib rəqəm səhifədə yoxlanır) →
`case_model.py` (deterministik qərar hesabı) → `script_qa.py` (gpt-4o redaktor + `settle_script` deterministik
düzəlişlər) → `math_check.py` / `number_audit.py` (hər rəqəm ayrıca, fail-closed).

**Vizual zəncir:** `scene_plan.py` (səhnə bölgüsü, foto promptları, `clean_bg_prompt` söz filtrləri, bayquş pozu) +
`visuals.py` / `data_visuals.py` / `decision_visuals.py` (chart spec-ləri, `visuals.KINDS`; chart-dakı hər rəqəm
danışıqda olmalıdır) → `render_bgs.py` (gpt-image-2, 5 şəkil/dəq limiter) → `check_bgs.py` (gpt-4o hakim +
`bg_dedupe.py` CLIP təkrar yoxlaması, yenidən çəkmə) → `render_owls.py` (magenta fon + `key_out`).

**Render:** `remotion_build.py` epizodu Remotion props-una çevirir (`timeline.py`, `layout.py`, `motion.py` hərəkət
planı, `sfx.py`) və `Remotion/` layihəsini render edir; səs master-i `_ffmpeg/audio_master.py` (−14 LUFS).
Remotion tərəfi: `Remotion/src/Episode.tsx` (kompozisiya), `visuals/` (chart/diaqram/xəritə), `Owl.tsx`
(hərəkətsiz — `test_motion_lint.py` bunu yoxlayır).

**LLM qatı:** bütün çağırışlar `llm.py` (`chat`, `chat_json`, `generate_image`, `edit_image`) üzərindən; provider
`--provider` / `.env LLM_PROVIDER` (default `openai`). Açarlar `.env`-də (`.env.example`).

**Feature bayraqları:** `config.py` (`CASE_MODEL`, `SFX`, `NUMBER_OVERLAY`, `TYPEWRITER`, `MOTION_VARIANTS`) —
hamısı `True`, `test_defaults.py` bunu qoruyur.

## Testlərə xas qaydalar

- `test_registry.py`: `progress.md` "Problemlər reyestri"nin **hər sətri** mövcud testə (`fayl.py::test_ad`)
  istinad etməlidir — yeni reyestr sətri yazanda test adını dəqiq verin, yoxsa test suite qırılır.
- Testlər şəbəkəyə/GPU-ya çıxmır: LLM və alt-proseslər (`runner`, `sleep`, `video`) parametr kimi əvəz olunur —
  yeni kodda da bu inyeksiya üslubunu saxlayın.
- Kod şərhləri və mesajlar ASCII-transliterasiyalı azərbaycancadır (`yoxdur`, `kecilir`) — Windows konsol kodlaması
  üçün; bu üslubu saxlayın.
