# CLAUDE.md — YouTubeAI (ELI5 Business video pipeline)

## Sessiyanın əvvəli (HƏMİŞƏ)
1. `progress.md`-ni oxu ("Cari vəziyyət", "Növbəti dəqiq addım", "Problemlər reyestri",
   **"Təkrarlanmamalı yanlış yollar"** — oradakı səhvləri bu sessiyada təkrarlama).
2. Açıq iş varsa ondan davam et; yoxdursa istifadəçinin mövzusunu gözlə.
3. `progress.md` HƏR mərhələdən sonra yenilənir (tamamlanan iş → "İcra jurnalı", ən yenisi yuxarıda).

## Tetik: mövzu = hazır video (tam avtonom)
İstifadəçi `Video: <Mövzu>` yazır və ya sadəcə mövzunu yazır → **sualsız, təsdiqsiz** dərhal:
1. Mövzu azərbaycanca verilibsə, ingiliscə başlığa çevir (məs. "What Is Profit Margin?").
2. PowerShell ilə müstəqil proses aç (Claude sessiyası bağlansa da işləsin):
   `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c "C:\YouTubeAI\Projects\.venv\Scripts\python.exe -u run.py "<Mövzu>" > C:\YouTubeAI\Episodes\_run_<slug>.log 2> C:\YouTubeAI\Episodes\_run_<slug>.log.err"'; CurrentDirectory='C:\YouTubeAI'}`
   (2026-10-08: alətdən `Start-Process` çağırış bitəndə ölür — WMI ilə aç, 20 s sonra prosesin sağ olduğunu yoxla.)
3. Loqu Monitor ilə izlə (`[N/11]` mərhələ sətirləri + error/traceback). Ölsə: `run.py --resume <slug>`.
4. Bitəndə özün yoxla (istifadəçidən soruşma):
   - **`qa/quality_gate.json` → `"passed": true`** (pipeline-ın son mərhələsi; bütün hesabatlar skriptin sha256-sı
     ilə, fail-closed) + **`qa/self_audit.md`**-də bütün xəta sinifləri "yoxlandı: OK" (`docs/error_classes.md`);
   - `script_qa.json` → `"problems": []` (B2B qərar, case, mənbə, Cold Open, Recap, redaktor); `captions_qa.json`
     → `"problems": []`; `bg_qa.json` → `generic_share` ≤ 0.10; giriş kartında hook rəqəmi görünür; chart
     səhnələrində bölmə adı başlığın üstündə (lower-third yox); altyazıda rəqəmlər "$4,000" formatında;
   - `owl_qa.json` (hamısı ok, `cards.intro/outro` ok), giriş/çıxış kartı kadrı — mövzuya uyğun bayquş, tərpənmir, bir neçə kadr + `thumbnail.png` vizual — bayquş eyni personaj, sağda, yazı/insan yox;
   - `checks.final_video_problems(mp4) == []`, müddət 10–12 dəq, −14 LUFS;
   - `math_check.json` → `"problems": []`;
   - `bg_qa.json` → `"duplicates": []`; kadrlarda uşaqsayağı görüntü (oyuncaq/cizgi fon) yoxdur;
   - musiqi dövr nöqtəsində sükut yoxdur (`silencedetect=n=-40dB:d=0.4`; ~0.4 s danışıq fasiləsi normaldır).
5. **Xəta qeydi — HƏR videoda, məcburi** (istifadəçi 2026-10-04: "hər yeni videoda qarşılaşdığın xətanı qeyd et ki
   bir də təkrarlanmasın"). Run boyu rast gəlinən HƏR xəta — pipeline xətası, yanlış nəticə, retry, dayandırılmış run,
   həm də mənim alət/əmr səhvlərim (yol, sed, encoding, kilid və s.) — video təhvil verilməzdən ƏVVƏL qeyd olunur:
   - kod/nəticə xətası → `progress.md` "Problemlər reyestri"nə yeni # sətir + test (TDD) + kod düzəlişi;
   - iş üsulu/alət səhvi → `progress.md` "Təkrarlanmamalı yanlış yollar" cədvəlinə sətir (nə + düzgün yol);
   - ümumi dərs → yaddaş `youtube-repeat-mistakes.md`-yə bir sətir.
   Xəta olmayıbsa jurnalda açıq yaz: "xəta yoxdur". Qeydsiz xəta = tapşırıq bitməyib.
6. `Hazir_Videolar\<slug>\` hazır olduğunu qısa bildir (qeyd olunan xətalar daxil), `progress.md` jurnalına sətir yaz, commit et.
7. **Təsdiq + yaddaşı silmə** (istifadəçi 2026-09-29): AskUserQuestion ilə soruş — "Video təsdiqlənsin və
   pipeline-dakı yaddaşı silinsin?". Təsdiqdə: `Projects\.venv\Scripts\python Projects\forget_episode.py <slug>`
   (`Episodes\<slug>\` + həmin epizodun `_run_*.log/.err` silinir; `Hazir_Videolar\<slug>\` QALIR), sonra
   `progress.md`-dən həmin videonun jurnal/vəziyyət sətirlərini sil (reyestrdəki ümumi kod düzəlişləri qalır), commit.
   Rədd edilsə — heç nə silinmir, istifadəçinin iradını düzəlt. Test: `Projects/tests/test_forget_episode.py`.
Bir neçə mövzu → ardıcıl (paralel yox: gpt-image limiti 5 şəkil/dəq). Yalnız həqiqi blokerdə soruş
(OpenAI balansı bitib, model yüklənmir, sirr lazımdır).

## Dəyişməz istifadəçi qərarları
- Video **10–12 dəq** (2026-09-30; əvvəl 8–10), heç vaxt 12 dəqiqədən uzun deyil. Test: `test_pipeline.py::test_parse_args_requires_topic_or_resume`.
- İlk saniyələrdə **"Hook" yazısı/sözü olmur** (nə ekranda, nə səsdə); giriş kartındakı mövzu başlığı və
  bölmə başlıqları (lower-third) qalır (2026-09-28). Test: `Projects/tests/test_spoken_titles.py`.
- **Təkrar kadr QƏTİ olmur** (2026-09-28): bir epizodda eyni obyekt/fon iki dəfə yox. `check_bgs` CLIP ilə
  (`bg_dedupe.py`, hədd 0.88) yoxlayır, sonrakı təkrarı yenidən çəkir; qalarsa mərhələ keçmir.
  Test: `Projects/tests/test_no_repeats.py`.
- **Uşaq videosu kimi görünmür** (2026-09-28, seçim A): fonlar realist fotoqrafiya (Pixar/3D yox), oyuncaq/
  konfet/karusel yox; ssenari 25–45 yaş yetkinlər üçün; uşaq musiqisi yox. Bayquş dəyişmir.
  Test: `Projects/tests/test_adult_look.py`.
- **Hesab səhvi QƏTİ olmur** (2026-09-30): ssenaridəki hər rəqəmli cümlə `math_check.py` ilə yoxlanır
  (gpt-4o 3 baxış + Python hesabı); `math_check.json` olmadan `script_gen` mərhələsi keçmir. YouTube
  metadata-da rəqəm/hesab yoxdur. Test: `Projects/tests/test_number_accuracy.py`.
  **2026-10-02 (#40, "birdəfəlik"):** son hökm `number_audit.py`-dir — skriptdəki HƏR rəqəm ayrıca, fail-closed:
  3 baxışdan ≥2-si onu "verilmiş" və ya Python-da düzgün hesablanmış saymasa → fokuslu 2-ci baxış → abzas yenidən
  yazılır (bayraqsız rəqəmlər dəyişə bilməz) → yenə keçməsə cümlə rəqəmsiz yazılır/silinir. Yoxlanmamış hesab
  videoya düşmür. Test: `Projects/tests/test_number_audit.py`.
- **Analitik animasiyalar** (2026-10-03): səhnələrin ~60%-i Remotion chart/diaqram (`visuals.py` + `Remotion/src/visuals/`),
  qalanı foto. **Hibrid (istifadəçi 2026-10-07):** generik foto animasiyaya yalnız `ANIM_MAX` = 70% tavanına qədər
  keçir; tavandan sonra case biznesinin literal kadrı ilə yenidən çəkilir, generik <10% qapısı qalır.
  Test: `test_visuals.py::test_animation_room_respects_the_70_percent_cap`. Chart-dakı HƏR rəqəm səhnə danışığında deyilməlidir (fail-closed). Giriş/çıxış kartı səhnə fotosunu
  təkrar etmir. Thumbnail fonu ayrıca (gpt-image-2 high + hakim). **LLM modelləri (istifadəçi 2026-10-08, əvvəlki "gpt-4o-mini" qərarını əvəz edir):** şəkil yaratma
  **gpt-image-2 QALIR**; qalan BÜTÜN LLM mərhələləri **Gemini**: yazan `gemini-3.8-flash` (kodda rol adı "gpt-4o-mini"/None),
  yoxlayan `gemini-3.1-pro-preview` (rol adı "gpt-4o") — `llm.GEMINI_ROLES`. Geri qayıtmaq: `.env` `LLM_PROVIDER=openai`.
  Mənbə axtarışı (`research.web_search`) hələ OpenAI web_search-dədir (növbəti addım: Google Search). Test: `test_llm.py`.
  Test: `test_visuals.py`, `test_thumbnail.py`.
- **Məzmun standartı — HƏR yeni videoda** (istifadəçi 2026-10-05, 12 addım; reyestr #54–#60):
  1) yalnız B2B — hər video ABŞ biznes sahibinin bir konkret qərarına cavab verir (plan: `decision`/`answer`);
  2) terif/analogiya düzgündür, vəd olunan suala cavab verilir (`script_qa.review_loop`, gpt-4o redaktor);
  3) ən azı 1 **yoxlanmış** rəsmi/tədqiqat mənbəyi (`research.py`: URL yüklənir, rəqəm + cümlə səhifədə, hakim
  "statistika + aidiyyət"; tapılmasa script_gen dayanır, uydurma yox), description-da link;
  4) ilk 3 saniyədə konkret rəqəm — `## Cold Open` cümləsi (ilk 9 sözdə rəqəm) giriş kartında səslənir/görünür;
  5) bir ABŞ case (sahibi adı ilə) Hook-dan son bölməyə qədər hər bölmədə — başqa biznes misalı YOX, analogiya
  yalnız bir cümləlik rəqəmsiz gündəlik təsvir (redaktor `single_case`, 2026-10-07); 6) təkrar yox — hər rəqəm
  skriptdə ən çox 2 dəfə deyilir, qərar rəqəmi də (`repeated_figures`, 2026-10-07), Recap yalnız nəticələr
  (rəqəm/ad/misal yox); 7) hər rəqəm chart və ya data kartında (`stats`), generik bullet (keypoints) yox;
  8) fonlar case biznesinin literal kadrları, generik/metafor ≤ 10% (`bg_qa.json generic_share`);
  9) chart səhnəsində bölmə adı lower-third deyil, başlığın üstündə kicker; 10) −14 LUFS + rəqəmlər TTS-ə
  ingiliscə sözlə (`speech.to_speech`), whisper hər rəqəmi eşitməlidir; 11) altyazı ssenaridən
  (`captions.py`, "$4,000"); 12) ABŞ nümunələri (şəhər/ştat, USD, IRS/SBA).
  Test: `test_script_story.py`, `test_research.py`, `test_speech.py`, `test_captions.py`, `test_literal_frames.py`,
  `test_visuals.py`, `test_remotion_build.py`.
- **Keyfiyyət + imkan yeniləməsi — BÜTÜN videolarda default AÇIQ** (istifadəçi 2026-10-07, 6 faza; reyestr #73–#91):
  case modeli + deterministik qərar hesabı (`config.CASE_MODEL`), data vizualları (table/threshold/timeseries/usmap
  `visuals.KINDS`-də), motion variantları (`MOTION_VARIANTS`), SFX (`SFX`), foto rəqəm overlay-i (`NUMBER_OVERLAY`),
  cold open typewriter (`TYPEWRITER`), mid-roll + upload checklist. Söndürmək YALNIZ istifadəçi qərarı ilə.
  Test: `test_defaults.py`, `test_case_model.py`, `test_decision_visuals.py`, `test_data_visuals.py`, `test_motion.py`,
  `test_sfx.py`, `test_publish_pack.py`, `test_quality_gate.py`, `test_registry.py` (reyestrin hər sətri testə bağlı).
  Yeni xəta → əvvəl `docs/error_classes.md`-dəki sinfə aiddirmi yoxla; aiddirsə qapının niyə buraxdığını düzəlt.
- Bayquş sabit (animasiya yox) — **giriş/çıxış kartında da** (2026-09-30): orada hər mövzuya ayrıca yaradılmış
  `owl/intro.png` (açılış) və `owl/outro.png` (qapanış, sağollaşır), eyni mövzu əşyası ilə. Test: `test_card_owls.py`.
- Bayquş modeli **gpt-image-2** (istifadəçi 2026-09-30; başqa modelə keçmə). Şəffaf fon vermir → magenta fonda çəkilir,
  `render_owls.key_out` lokal silir. Test: `test_owl_keying.py`.
- Bayquş həmişə sağda; hər səhnədə mətnə uyğun ChatGPT bayquşu, görünüşü
  (dəyirmi eynək, göy kostyum, sarı qalstuk) dəyişməz.
- Musiqi: AI, lokal (Stable Audio Open), pulsuz, istinadsız. Stability Community License aktivdir (2026-09-28).
  Pullu musiqi/səs xidməti təklif etmə.
- Yeni problem tapılanda: `progress.md` reyestrinə sətir + test (TDD) + kod düzəlişi — əl ilə həll yox.

## Texniki
- Testlər: `Projects\.venv\Scripts\python -m pytest -q Projects/tests` (repo kökündən).
- Açarlar `.env`-də — commit etmə. HF yükləməsi: `HF_HUB_DISABLE_XET=1`.
- Cavab dili: azərbaycanca, qısa.
