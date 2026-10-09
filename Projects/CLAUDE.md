# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Bu fayl **kod arxitekturası, əmrlər və "Keyfiyyət + imkan yeniləməsi" tapşırığının (istifadəçi 2026-10-07)
> kodda harada yaşadığı** üçündür. İstifadəçi qərarları və video tetiki kökdəki `C:\YouTubeAI\CLAUDE.md`-dədir;
> canlı vəziyyət `progress.md`-dədir. Mövzudan asılı olmayan ümumi qayda yaz — konkret videoya bağlı düzəliş yox.

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

## İş qaydası (hər dəyişiklik üçün)

1. Əvvəl kök `CLAUDE.md` + `progress.md`. `docs/reference/video_yarat_v4.py` yalnız ideya mənbəyidir — icra etmə,
   pipeline-a qoşma.
2. Böyük iş fazalara bölünür, fazadan əvvəl qısa plan.
3. Hər bənd TDD: test (qırmızı) → kod → test (yaşıl) → `progress.md` reyestrinə növbəti nömrəli sətir
   **`fayl.py::test_ad` istinadı ilə** (`test_registry.py` istinadsız sətri qırır).
4. Faza sonu: bütün testlər keçir → `progress.md` "Cari vəziyyət" + "Növbəti dəqiq addım" → commit.
   Sessiya kəsilsə növbəti sessiya `progress.md`-dən qaldığı fazadan davam edir.
5. Mövcud kodu genişləndir, təkrar yaratma; həll olunmuş işi yenidən yazma.
6. Mövcud test istifadəçi qərarını qoruyur və yeni tələblə ziddiyyətdədirsə — **dayan və soruş**. Başqa hallarda
   yalnız həqiqi blokerdə soruş.
7. Yeni xəta → əvvəl `docs/error_classes.md`-dəki sinfə aiddirmi; aiddirsə həmin qapının niyə buraxdığını düzəlt
   (yalnız simptomu yox), deyilsə yeni sinif + qapı + test.

## Pozulmaz invariantlar (kodda və testdə qorunur)

| Qərar | Harada |
|---|---|
| Video 10–12 dəq | `pipeline.MIN_SECONDS/MAX_SECONDS`, `length_gate`, `quality_gate._video` |
| "Hook" sözü ekranda/səsdə yox | `test_spoken_titles.py` |
| Bölmə başlığı: foto səhnədə lower-third, chart səhnədə kicker | `common.tsx::Kicker`, `test_remotion_build.py` |
| Bayquş sabit, sağda, gpt-image-2; `Owl.tsx`/CardOwl **dəyişmir** | `test_motion_lint.py`, `test_card_owls.py`, `test_owl_keying.py` |
| Yazan gpt-4o-mini, yoxlayan gpt-4o (default `openai`) | `llm.py`, `test_llm.py` |
| Təkrar kadr yox, uşaqsayağı görünüş yox, generik foto ≤ 10% | `check_bgs.py`, `bg_dedupe.py`, `stages.GENERIC_MAX` |
| −14 LUFS; musiqi lokal Stable Audio | `_ffmpeg/audio_master.py`, `music_gen.py` |
| Animasiya ~60%, tavan `visuals.ANIM_MAX` = 0.70 | `visuals.py`, `test_visuals.py` |
| Ken Burns sabit sürət; şrift Montserrat | `test_motion_lint.py`, `Assets/fonts`, `Remotion/src/fonts.ts` |
| Yalnız B2B: ABŞ biznes sahibinin bir qərarı | plan `decision`/`answer`, `script_qa` |
| Chart/overlay-dəki hər rəqəm səhnə danışığında (fail-closed) | `visuals.py`, `data_visuals.py`, `test_visuals.py` |

## Dörd ayrı Python mühiti

Mərhələlər öz venv-ləri ilə alt-proses kimi işləyir (`stages.PY`): `Projects\.venv` (əsas pipeline, testlər),
`TTS\.venv` (Kokoro, `tts_gen.py`), `Whisper\.venv` (`Whisper/make_srt.py`), `MusicGen\.venv` (Stable Audio Open,
`music_gen.py`). `Projects\.venv`-də torch/kokoro yoxdur. `upscale_bgs` ComfyUI (port 8188, `run_comfyui.bat`)
tələb edir (`needs_comfy=True`; pipeline özü açır).

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
(plan + `model_result`), `scenes.json` (`visual` açarı olan səhnə Remotion chart-ıdır, olmayan foto —
`stages.photo_numbers`), `bg/`, `bg_hd/`, `owl/`, `music.wav`, `*_qa.json`, `<slug>.mp4`, `youtube/`, `qa/`.
Faylı oxuyub-yazan kod diskdən təzə oxuyub yalnız öz açarını yazır (reyestr #5).

**LLM qatı:** bütün çağırışlar `llm.py` (`chat`, `chat_json`, `generate_image`, `edit_image`); provider
`--provider` / `.env LLM_PROVIDER` (default `openai`; Gemini yalnız istifadəçi istəyəndə).

## Keyfiyyət tapşırığının 6 fazası → kod

**Faza 1 — Məzmun dəqiqliyi**
- Plan sxemində `model` (`variables`, `before`, `after`, `threshold`); ifadələr yalnız dəyişən adı, rəqəm,
  `+ − × ÷ ( )`. `case_model.py` təhlükəsiz ast hesabı (eval yox) → before/after/delta, threshold, `insight` →
  `meta.json plan.model_result`; hesablanmayan/dövri ifadə → plan yenidən.
- `script_gen` bölmələrə `model_result`-ı "use exactly these figures" kimi ötürür; `script_qa` deterministik
  (fail-closed): qərar rəqəmi `model_result`-da, case kəmiyyəti `variables`-ə uyğun, naive yoxlama (hər dəyişəni
  neytrallaşdır → skript naive nəticəyə uyğundursa "dəyişən buraxılıb"); `settle_script` deterministik düzəlişlər.
- Cold open `insight`-dan, rəqəm ilk 9 sözdə və `model_result`-da.
- Uydurma rəqəm: OUTLINE nümunələri rəqəmsiz; `number_audit.py`-də "given" yalnız `variables`, mənbə figure-ü, il,
  sıra nömrəsi, vahid sabiti.
- `research.py`: il ≥ cari − 3 üstündür; köhnə mənbə abzasda və description-da ili ilə.
- Tək case, analogiya rəqəmsiz bir cümlə, hər rəqəm ≤ 2 dəfə, Recap-də rəqəm/ad/misal yox.

**Faza 2 — Data vizualları** (`visuals.KINDS`, `data_visuals.py`, `decision_visuals.py`, `Remotion/src/visuals/`)
- `table` + `threshold` LLM-siz `model_result`-dan, qərar bölməsinə məcburi (`DataViz.tsx::Table/Threshold`).
- `timeseries` (interpolasiya → ekranda "illustrative"; eniş ayrı rəng) və `usmap` (seed = slug hash; sayğac bayquş
  və altyazı zonasından kənar) — `DataViz.tsx::Timeseries/USMap`; sabit kodlanmış data yox.
- Chart 0-cı kadrdan skelet (dəyər yerində "—"), "yalnız başlıq" kadr payı ≤ 3%.
- Generik flow/timeline addımı (Analyze/Evaluate/Review…) rədd; addım case adı/obyekti/dəyişəni/rəqəmi daşıyır;
  videoda flow ≤ 1.
- Foto səhnəsində danışılan pul/faiz rəqəmi `captions.words.json` vaxtında count-up overlay
  (`NumberOverlay.tsx`, ≤ 2.5 s, səhnədə ≤ 1).

**Faza 3 — Motion + səs** (`Remotion/src/motion.ts`, `Projects/motion.py`, `Projects/sfx.py`)
- Tokenlər: giriş 300–600 ms, çıxış 200–400 ms, stagger 60–120 ms, spring soft/snappy/bouncy, bezier. Chart/kart/
  overlay-də xətti animasiya və hardcoded müddət yox (lint testi); `common.tsx` `useIn/rise/Count` tokenlərdən oxuyur.
- Hər növ üçün ≥ 3 giriş variantı; typewriter qara ekran/sükut əlavə etmir, səhnə müddətini dəyişmir.
- Keçidlər quraşdırılmış `@remotion/transitions`-dan, bölmə/adi dəsti ayrı, eyni keçid ardıcıl 2 dəfə yox.
- Seed = slug hash; epizoda bir theme (clean/dynamic/editorial); `Episodes/_motion_history.json` — son 3 epizodla
  oxşarlıq > 50% → theme dəyişir. QA: `qa/motion_sheet.png` (`remotion_build.motion_sheet`, renderStill).
- Vurğu: rəqəm səslənəndə ≤ 400 ms pulse; 20 s-də ≤ 1 böyük effekt; saniyədə ≤ 3 flash.
- SFX (whoosh/pop/tick/boom, ffmpeg lavfi; `Projects/sfx/`-də istifadəçi faylı varsa o): 10 s-də ≤ 2, nitqdən
  ≥ 18 dB aşağı, söz ortasında yox; `audio_master`-də nitq+musiqi ilə qarışır, **sonra** iki keçidli −14 LUFS.
- Altyazıda rəqəm sözləri accent rəngdə; format ("$4,000", 44 simvol, fon qutusu) dəyişmir.

**Faza 4 — Publish** (`publish_pack.py`)
- `youtube/midrolls.txt`: bölmə keçidindən 1 s əvvəl 3–4 nöqtə, aralarında ≥ 2 dəq, ilk 60 s-də yox.
- Description-a `.env` `LEAD_MAGNET_URL` / `AFFILIATE_LINKS` (boşdursa yazılmır).
- `youtube/upload_checklist.txt` (Not made for kids, bütün reklam formatları, mid-roll əllə, 3 başlıq + thumbnail
  A/B, ABŞ vaxtı); hər ikisi `Hazir_Videolar\<slug>\` paketində.

**Faza 5 — Default ON + qapılar**
- `config.py`: `CASE_MODEL`, `SFX`, `NUMBER_OVERLAY`, `TYPEWRITER`, `MOTION_VARIANTS` = `True`; `REQUIRED_KINDS`
  `KINDS`-də. Video başına əl ilə açılmır; söndürmək yalnız istifadəçi qərarı (`test_defaults.py`).
- `quality_gate.py` vahid, fail-closed qapı: hər hesabat mövcud, `qa_stamp` sha256 skriptə uyğun, `problems: []`;
  əlavə: SFX hadisəsi > 0, foto pul/faiz rəqəmlərinin ≥ 80%-də overlay, qərar mövzusunda table + threshold,
  cold open-da typewriter, motion oxşarlığı ≤ 50%. `deliver()`/publish yalnız qapı keçəndə.
  Çıxış: `qa/quality_gate.json` + `qa/self_audit.md` (kataloqdakı hər sinif "yoxlandı / nəticə").
- `quality_gate.ERROR_CLASSES` → `docs/error_classes.md` (generasiya, əl ilə redaktə yox).

**Faza 6 — Hazırlıq meyarı:** bütün testlər + iki fərqli yeni B2B E2E (biri qiymət/xərc → table+threshold,
biri zaman/coğrafiya → timeseries/usmap); hər ikisində quality_gate keçir, self_audit təmiz, motion_sheet-lər
fərqli, 10–12 dəq, −14 LUFS, paket tam (mp4, thumbnail, youtube.txt, srt, script, midrolls, upload_checklist).

## Reference skriptdən KÖÇÜRÜLMƏYƏCƏKLƏR

ffmpeg zoompan; whisper altyazısı (altyazı ssenaridəndir); −16 LUFS; sabit `CHART_PATH` və hardcoded etiketlər;
uydurma nəşr adlı qəzet kartı; qara fəsil kartı + sükut; sabit random seed; Windows şriftləri; kadrdan thumbnail;
mətnli outro kartı.

## Testlərə xas qaydalar

- Testlər şəbəkəyə/GPU-ya çıxmır: LLM və alt-proseslər (`runner`, `sleep`, `video`) parametr kimi əvəz olunur —
  yeni kodda da bu inyeksiya üslubunu saxlayın. Sintetik testlər (məs. customers=40, price 50→55 → threshold 27).
- Kod şərhləri və mesajlar ASCII-transliterasiyalı azərbaycancadır (`yoxdur`, `kecilir`) — Windows konsol
  kodlaması üçün; bu üslubu saxlayın.
