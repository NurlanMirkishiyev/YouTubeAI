# progress.md — YouTubeAI icra jurnalı

> **Bu fayl nə üçündür:** hər dəfə işə davam edəndə Claude əvvəlcə bu faylı oxuyur və
> son icranın harada dayandığını bilir. **Hər mərhələ tamamlananda bu fayl yenilənir.**
> Qayda: "Cari vəziyyət" və "Növbəti dəqiq addım" bölmələri həmişə aktual olmalıdır;
> tamamlanan iş "İcra jurnalı"na bir sətir kimi əlavə edilir (ən yenisi yuxarıda).

**Layihə:** `C:\YouTubeAI` — həftədə 2 ədəd 10–12 dəq "ELI5 Business" YouTube videosu üçün lokal pipeline
**Master plan:** `plan.md` (addım 01–36)
**Son yenilənmə:** 2026-10-06

---

## Cari vəziyyət

| Faza | Vəziyyət |
|---|---|
| FAZA A–E (addım 01–28) | **TAMAM** — ilk epizod çıxdı və oynadılır |
| FAZA F / Faza 1 (automation + keyfiyyət) | **TAMAM** (2026-09-25) — Task 0–16, E2E işlədi, fonlarda yazı problemi həll edildi |
| FAZA G (5 şikayət + Remotion) | **TAMAM** (2026-09-26) — `what-is-business-automation` 15.59 dəq HAZIRDIR |
| Avtomatik keyfiyyət (check_bgs) | **TAMAM** (2026-09-26) — əl ilə fon yoxlaması artıq lazım deyil |
| Şəkillər ChatGPT ilə (gpt-image-2) + təmizlik | **TAMAM** (2026-09-26) — SDXL silindi, LTX plandan çıxarıldı |
| Video 8–10 dəq + E2E `what-is-cash-flow` | **TAMAM** (2026-09-27) — kredit əlavə edildi, paket hazırdır |
| Musiqi + sabit personaj (FAZA H) | **TAMAM** (2026-09-27) — `Music\*.mp3` avtomatik, bayquş hərəkətsiz, poz səhnəyə uyğun |
| Səhnə bayquşu + AI musiqi (FAZA I) | **TAMAM** (2026-09-27) — E2E `what-is-profit-margin` 8.92 dəq HAZIRDIR, 52/52 bayquş ilk cəhddə keçdi |

**İstifadə:** iş masasında **"ELI5 Yeni Video"** qısayolu = `Yeni_Video.bat` (iki klik → mövzu yaz; `resume` yazsan
yarımçıq epizod davam edir) və ya `python run.py "Mövzu"` (istənilən python; özünü `Projects\.venv`-ə keçirir) →
`Episodes\<slug>\<slug>.mp4` + `Episodes\<slug>\youtube\`. Yarımçıq qalsa: `python run.py --resume <slug>`.
**Bütün hazır videolar:** `C:\YouTubeAI\Hazir_Videolar\<slug>\` — **hər mövzunun öz qovluğu** (istifadəçi 2026-09-27):
`<slug>.mp4` (hardlink, əlavə yer tutmur) + `thumbnail.png` + `youtube.txt` (başlıq/description/tags) +
`subtitles.srt` + `script.md` — pipeline sonda `deliver()` ilə avtomatik yazır. İş masasında qovluq qısayolu YOXDUR
(istifadəçi sildi, lazım deyil); yalnız "ELI5 Yeni Video" qısayolu var.
Musiqi (FAZA I-dən): `music_gen` mərhələsi hər epizoda öz AI musiqisini yaradır (Stable Audio Open, lokal GPU,
pulsuz, istinadsız) → `Episodes\<slug>\music.wav` (~3.8 dəq, video boyu dövr edir); description-da kredit yoxdur.
`--music <fayl>` versən o istifadə olunur. `Music\*.mp3` və `credits.json` artıq istifadə olunmur (silinməyib).

**Ölçülmüş (2026-09-23):** fon upscale 15 s/fon · sprite HD 8 ədəd 71 s · 8.14 dəq epizodun montajı ~7 dəq ·
köhnə epizodun FAZA F versiyası (`faza1_test.mp4`) bütün A2/A3/A4/A8 yoxlamalarından keçdi.

**İlk epizod (2026-09-26 istifadəçi qərarı ilə silindi):** `trademark-copyright-patent`
1550 söz · 29 səhnə · 7.97 dəq · 1920×1080@30 · H.264 High / yuv420p / L4.1 · AAC 24 kHz mono · 137 MB
Tam dekod testi xətasız. Oynadılması istifadəçi tərəfindən təsdiqlənib.

---

## Problemlər reyestri — hamısı avtomatlaşdırılıb (2026-09-26)

Qayda: istifadəçi yalnız mövzu verir. Aşağıdakı hər problem əvvəl ən azı bir dəfə baş verib və indi
**kodda** həll olunub (əl ilə addım yoxdur). Yeni problem tapılanda bura sətir + test + kod düzəlişi əlavə et.

| # | Problem (nə vaxt) | Kök səbəb | Avtomatik həll (commit) |
|---|---|---|---|
| 1 | Fonda mənasız yazı (hər epizod) | SDXL yazı çəkə bilmir; obyektin adı yazını gətirir | `clean_bg_prompt` söz filtri + **`check_bgs` vision hakimi** yenidən çəkir (`f7ce99b`, `795a665`). Test: `test_scene_plan.py::test_clean_bg_prompt_drops_text_bearing_items`, `test_check_bgs.py::test_verdict_counts_only_checks_answered_true` |
| 2 | Fonda insan / insan əli (ep2 sc35, ep3 sc02/sc48) | İnsan ismi promptda; negativ prompt kömək etmir | `HUMAN` filtri (athlete, hands, … əlavə) + `check_bgs` (`27fc2d4`, `795a665`). Test: `test_scene_plan.py::test_clean_bg_prompt_drops_human_nouns_but_keeps_robots`, `test_scene_plan.py::test_clean_bg_prompt_drops_athletes_and_hands` |
| 3 | Boş/mənasız, kazino, deformasiya fonlar (ep3 sc09/27/97) | LLM zəif metafora seçir | `check_bgs`: no_subject / off_topic / deformed → yeni prompt. Test: `test_check_bgs.py::test_verdict_tolerates_malformed_judge_output`, `test_check_bgs.py::test_next_prompt_passes_judge_fix_through_word_filters` |
| 4 | Yenidən çəkmə eyni şəkli verirdi (ep3) | Sabit seed (`BASE_SEED + n`) | hər cəhddə yeni seed, `scenes.json`-da `seed` (`795a665`). Bugünkü ekvivalent (gpt-image-də seed yoxdur): təkrar cəhd heç vaxt eyni girişlə çəkilmir. Test: `test_no_repeats.py::test_next_prompt_never_returns_the_same_fallback_twice`, `test_check_bgs.py::test_next_prompt_uses_unused_fallback_on_last_attempt_or_empty_fix` |
| 5 | Prompt düzəlişi itdi (ep3) | `render_bgs` sonda köhnə `scenes.json`-u üstdən yazırdı | `save_bg_paths` faylı təzədən oxuyur, yalnız `bg` yazır (`795a665`). Test: `test_check_bgs.py::test_render_save_keeps_prompts_edited_on_disk_meanwhile`, `test_check_bgs.py::test_apply_changes_rereads_file_and_keeps_other_edits` |
| 6 | Pis fon 3 dəfə də pisdirsə pipeline ilişə bilərdi | — | 3 raunddan sonra istifadə olunmamış `FALLBACK_POOL` fonu. Test: `test_check_bgs.py::test_next_prompt_uses_unused_fallback_on_last_attempt_or_empty_fix` |
| 7 | Hakim 84/97 yaxşı fonu "insan" dedi | gpt-4o-mini + tək "ok?" sualı + narration-dakı "you" | gpt-4o, ayrı bəli/xeyr yoxlamaları, "yalnız şəklə bax" (`795a665`). Test: `test_check_bgs.py::test_verdict_counts_only_checks_answered_true` |
| 8 | Animasiya dona-dona | ffmpeg zoompan tam piksel | Remotion sub-pixel (`0cfa5cb`). Test: `test_pipeline.py::test_build_stage_renders_with_remotion` |
| 9 | Fon hər kəsişdə dayanırdı | Ken Burns `inOut` easing | sabit sürət (`425128e`). Test: `test_motion_lint.py::test_ken_burns_keeps_a_constant_speed` |
| 10 | Remotion pipeline-a qoşulmamışdı | `_build_cmd` köhnə skripti çağırırdı | `test_build_stage_renders_with_remotion` (`d30f12c`). Test: `test_pipeline.py::test_build_stage_renders_with_remotion` |
| 11 | Render sessiya bağlananda öldü | Proses Claude sessiyasına bağlı idi | Claude pipeline-ı **`Start-Process` ilə müstəqil** açır; ölsə `--resume` qaldığı yerdən. Test: `test_pipeline.py::test_run_pipeline_skips_done_and_records_failure` |
| 12 | Video açılmırdı (yuv444p) | `-pix_fmt` verilməmişdi | spec-ə kodlama + `final_video_problems` yoxlaması. Test: `test_checks.py::test_yuv444_is_reported` |
| 13 | Video 10 dəq-dən qısa | LLM söz hədəfini tutmur | bölmə-bölmə yazı + TTS saniyə qapısı. Test: `test_script_gen.py::test_words_to_add`, `test_script_gen.py::test_words_for_seconds` |
| 14 | Hakim API limitinə (429) düşən fonu yoxlamadan keçirdi (ep3 sc89) | 1–4 s backoff TPM limitinə azdır | xətalı fonlar 30 s gözləyib ardıcıl yenidən yoxlanır (`3cee56c`). Test: `test_check_bgs.py::test_judge_all_rejudges_scenes_that_hit_api_errors` |
| 15 | Mərhələ bir dəfəlik xəta ilə bütün videonu dayandırırdı | retry yox idi | uğursuz mərhələ 30 s sonra 2 dəfə yenidən cəhd edilir (`547950f`). Test: `test_pipeline.py::test_run_pipeline_retries_a_stage_after_transient_failure` |
| 16 | "smart kitchen scale/oven" ekranında rəqəm/yazı (ep3 sc16/sc23) | ekranlı cihaz | `digital …`, `smart <cihaz>` yazı daşıyan sayılır, "smart robot" qalır (`547950f`). Test: `test_scene_plan.py::test_clean_bg_prompt_drops_digital_and_smart_devices_but_keeps_smart_robots` |
| 17 | gpt-image 97 şəkildən 55-ni 429 ilə itirdi (ep4) | hesab limiti dəqiqədə 5 şəkil | sürüşən pəncərə limiter + API-nin dediyi qədər gözləmə (`63e3379`). Test: `test_render_bgs.py::test_rate_limiter_allows_at_most_n_starts_per_window`, `test_render_bgs.py::test_retry_waits_as_long_as_the_api_asks_on_429` |
| 18 | Video 16 dəq çıxırdı; istifadəçi: **8–10 dəq, 10-dan uzun olmasın** | söz hədəfi xalis 199 wpm ilə, max qaydası yox idi | effektiv 150 söz/dəq, default 1230 söz, skript və TTS qapıları həm uzadır həm qısaldır (`--shorten`), final video > 600 s → xəta. Test: `test_pipeline.py::test_verify_video_rejects_a_video_longer_than_max`, `test_script_gen.py::test_words_to_cut_for_max_length` |
| 19 | Səhnə sayı azalanda köhnə `bg/sc53..95` qalırdı (ep4) | `render_bgs` artıq faylları silmirdi | `prune_extra` (`def75af`). Test: `test_render_bgs.py::test_prune_removes_backgrounds_beyond_the_scene_count` |
| 20 | 52 səhnədə 7 sikkə bankası (ep4) | subyektlər mücərrəd adlanırdı, yalnız son 8 səhnəyə baxılırdı | promptun əsas ismi (`hero`) müqayisə olunur, epizodda eyni isim ≤ 2 dəfə, LLM-ə əsas isimlər də "istifadə olunub" kimi verilir. Test: `test_scene_plan.py::test_hero_noun_is_the_head_of_the_first_noun_phrase`, `test_scene_plan.py::test_avoid_list_names_the_real_objects_not_only_abstract_subjects` |
| 21 | ChatGPT öz-özünə küçük/pişik/dovşan çəkirdi (ep4, 7 fon) | "Pixar-style" personaj gətirir | şəkil promptunda "no animals or cartoon characters (robots are fine)". Test: `test_render_bgs.py::test_prompt_forbids_extra_animal_characters` |
| 22 | Ehtiyat fon özü 3-cü "jar" oldu (ep4) | fallback seçimi istifadə olunmuş isimlərə baxmırdı | `pick_fallbacks` (`d2cc036`). Test: `test_scene_plan.py::test_fallbacks_skip_heroes_already_in_the_episode` |
| 23 | OpenAI krediti bitdi → publish 4×3 dəfə boş təkrar, istifadəçi JSON gördü (ep4) | `insufficient_quota` 429 ilə gəlir | dərhal "OpenAI BALANSI BITIB …" xətası, mərhələ təkrarlanmır, konsolda loqun son sətri görünür. Test: `test_llm.py::test_exhausted_credits_stop_immediately_with_a_clear_message`, `test_pipeline.py::test_failed_stage_shows_the_last_log_line_and_quota_errors_are_not_retried` |
| 24 | Video musiqisiz çıxırdı | `Music\` boş, bat yalnız `--music` ilə ötürürdü | 4 CC BY trek + `pipeline.default_music` + `publish_pack.music_credit`. Test: `test_pipeline.py::test_make_ctx_uses_the_episodes_own_ai_music`, `test_publish_pack.py::test_music_credit_for_cc_by_track` |
| 25 | Personaj tərpənirdi, bölmə dəyişəndə sağ↔sol tullanırdı; istifadəçi: **"sabit dayansın, tərpənməsin, şəkli səhnəyə uyğunlaşsın"** | `Owl.tsx` nəfəs/yellənmə/danışıq/spring + `assign_positions` növbəsi; `vary_poses` pozu zorla dəyişirdi | `Owl.tsx` hərəkətsiz, poz fon keçidinin ortasında ani dəyişir; bayquş həmişə sağda; `fit_poses` LLM seçimini saxlayır; sol-kompozisiyalı köhnə fonlar güzgülənir (`flip`). Test: `test_motion_lint.py::test_owl_components_are_unchanged_and_still`, `test_scene_plan.py::test_owl_stays_on_one_side_for_the_whole_episode`, `test_scene_plan.py::test_poses_follow_the_scene_even_when_repeated`, `test_remotion_build.py::test_left_composed_backgrounds_are_mirrored_so_the_owl_stays_right` |
| 26 | AI musiqi: kliplər sonda sükut, 7 dB səviyyə fərqi (proba); dövr nöqtəsində videoda 1.25 s sükut (ep5 228 s) | model klipi 0.8–2.4 s sükut / ~4 s reverb quyruğu (−21→−50 dB) ilə bitirir | hər klip: baş −50 dB, son **−35 dB** ilə kəsilir, −18 LUFS; yekun trek 0.4 s fade-out (`58b0db5` + bu commit). Test: `test_music_gen.py::test_clip_edge_silence_is_trimmed`, `test_music_gen.py::test_reverb_tail_is_cut_harder_so_the_loop_seam_has_no_hole`, `test_music_gen.py::test_every_clip_is_loudness_normalized_before_crossfade` |
| 27 | Altyazıda qiymət bölünürdü: `$39 .99`, `$9 .99` (ep6), köhnələrdə `t -shirt`, `0 .67` | Whisper `" $39"` + `".99"` verir, `compact_words` hər tokeni ayrı söz sayırdı | boşluqsuz başlayan token əvvəlki sözə birləşir (`test_subword_tokens_are_merged_into_previous_word`). Test: `test_remotion_build.py::test_subword_tokens_are_merged_into_previous_word` |
| 28 | İlk saniyələrdə yuxarı solda **"Hook"** yazısı + səsdə "Hook." (subtitrdə "Huggy."); istifadəçi: **"hook yazısı olmasın, digər başlıqlar qalsın"** | `spoken_titles` regex-ində `\b` əvəzinə backspace (0x08) yazılmışdı → Hook heç vaxt tanınmırdı | funksiya `timeline.py`-yə köçdü (test edilə bilir), regex `hook\b`; `test_spoken_titles.py`. Test: `test_spoken_titles.py::test_hook_section_gets_no_title_but_other_sections_do`, `test_spoken_titles.py::test_no_backspace_characters_in_source` |
| 29 | **Təkrar kadrlar** (pricing: 55 səhnədən 10-u eyni ehtiyat fon, 6 peçenye, 3 donuz qumbarası, 2 eyni sikkə); istifadəçi: **"təkrar kadrlar olmasın, qəti"** | ehtiyat hovuz bitəndə hər dəfə `FALLBACK_BG`; eyni obyekt 2 dəfə icazəli idi; son addım yalnız yan-yana təkrarı əvəz edirdi; söz yoxlaması "stack of cookies"/"single cookie" fərqini tutmurdu | `MAX_SAME_HERO=1`, bütün təkrarlar əvəz olunur, hovuz 44 ayrı obyekt və təkrarsız (bitərsə xəta), `next_prompt` epizoddakı obyekti təkrarlamır, **CLIP şəkil yoxlaması** (`bg_dedupe.py`, 0.88) sonrakı təkrarı yenidən çəkir, qalarsa `check_bgs` keçmir (`test_no_repeats.py`). Test: `test_no_repeats.py::test_same_hero_anywhere_in_the_episode_is_a_repeat`, `test_no_repeats.py::test_pick_fallbacks_refuses_to_reuse_when_the_pool_runs_out`, `test_no_repeats.py::test_duplicates_keep_the_first_scene_and_redo_the_later_ones`, `test_no_repeats.py::test_check_bgs_stage_fails_while_duplicates_remain` |
| 30 | **Video uşaq videosu kimi görünürdü** (karusel, oyuncaq fabrik/qatar, peçenye, "Pixar" fon, "kids educational" musiqi, "10 yaşlı uşaq" ssenari) | promptlar uşaq auditoriyası üçün yazılmışdı | seçim A: realist foto fon, yetkin (25–45) ssenari və səhnə direktoru, `CHILDISH` söz filtri, hakimdə `childish` yoxlaması, uşaq musiqi stilləri çıxarıldı (`test_adult_look.py`). Test: `test_adult_look.py::test_background_style_is_realistic_photography`, `test_adult_look.py::test_judge_rejects_childish_images`, `test_adult_look.py::test_script_is_written_for_adults`, `test_adult_look.py::test_music_has_no_kids_styles` |
| 31 | check_bgs yanlış "təkrar kadr" ilə 2 dəfə düşdü: saniyəölçən / kompas / qum saatı (pricing E2E-2, 2026-09-29); eyni vaxtda iki qol saatı (0.878) tutulmadı | CLIP realist fotoda mövzu/kompozisiya oxşarlığını ölçür: fərqli obyektlər 0.897–0.918, eyni sikkə 0.884 — tək hədd ayırmır | CLIP yalnız namizəd (`DUP_SIM` 0.85), hər cütü gpt-4o iki şəklə baxıb təsdiqləyir (`confirm_duplicates`, `same_scene`); cavab yoxdursa təkrar sayılır (`test_no_repeats.py`). Test: `test_no_repeats.py::test_clip_pairs_that_the_judge_calls_different_are_not_duplicates`, `test_no_repeats.py::test_judge_error_on_a_pair_counts_as_duplicate`, `test_no_repeats.py::test_clip_threshold_is_a_candidate_filter_below_real_repeats` |
| 32 | 56 fondan 22-si mövzudan kənar ehtiyat fonla bitdi (mayak, yelkənli), hər biri 3 dəfə boşuna çəkildi; resume/retry qəbul olunmuş fonları yenidən çəkirdi (pricing E2E-2) | hakim dar mövzuda yazılı/təkrar obyekt təklif edirdi (qiymət etiketi, menyu, kassa) → rədd → dərhal hovuz → hovuz fonu yenə "mismatch"; `tries` hər run-da sıfırlanırdı | hakim 3 variant verir + istifadə olunmuş obyektlər siyahısı; hamısı rədd olunsa **səbəblə** ikinci təklif (`choose_prompt`, `suggest_again`); "X with a price label" → yalnız əlavə kəsilir (`cut_text_clause`); QA-da artıq seçilmiş hovuz fonu yalnız "mismatch" üçün yenidən çəkilmir, ilk dəfə isə bir şans alır (`needs_redo`); cəhd sayı `bg_qa.json`-dan bərpa (`load_tries`). Ölçü: 10 pis səhnədən hovuza 9 → 0. Test: `test_check_bgs.py::test_choose_prompt_asks_again_with_reasons_when_every_option_is_rejected`, `test_check_bgs.py::test_verdict_reads_several_fix_options`, `test_check_bgs.py::test_attempts_survive_a_resume_while_the_prompt_is_unchanged`, `test_check_bgs.py::test_pool_fallback_is_not_redrawn_only_for_being_off_topic`, `test_scene_plan.py::test_text_bearing_with_clause_is_cut_and_the_object_kept` |
| 33 | #32 düzəlişindən sonra hakim 429 aldı (gpt-4o TPM 30k), 429 alan fonlar **yoxlanmadan** keçdi (pricing E2E-3) | istifadə olunmuş obyekt siyahısı hər hakim sorğusuna qoşulurdu: 535 → ~1980 token × 56 paralel | siyahı yalnız `suggest_again`-də (rədd olunanlar, ardıcıl); `judge_text` < 400 simvol, `max_tokens` 300 (ölçü: in=596). Test: `test_check_bgs.py::test_judge_text_stays_small_without_the_used_object_list` |
| 34 | **Videoda hesab səhvi** (payment-fees: "100 yemək/həftə → $20 qənaət… bir ayda **eight hundred dollars**", düzgün ~$80); istifadəçi: **qəti düzəlsin, bütün videolarda** | ssenarini LLM yazır, heç bir mərhələ hesabı yoxlamırdı | `math_check.py`: rəqəmli HƏR cümlə deterministik tapılır → gpt-4o 3 müstəqil baxışla ifadəyə çevirir → iddia mətndən, nəticə Python-da (`ast`) hesablanır, operandlar mətndə olmalıdır → səhv yalnız çoxluq eyni düzgün dəyəri tapanda; yalnız həmin cümlə yenidən yazılır, düzgün dəyər yoxdursa rədd. `script_gen` yazanda/uzadanda/qısaldanda işləyir; `math_check.json` (skriptin sha256-si) olmadan `verify_script` keçmir. Real ssenaridə: 31 cümlə, 1 səhv düzəldi, 0 yalançı həyəcan (`test_number_accuracy.py`). Test: `test_number_accuracy.py::test_real_bug_monthly_total_is_caught`, `test_number_accuracy.py::test_report_is_bound_to_exact_script_text`, `test_number_accuracy.py::test_verify_script_stage_fails_without_math_report` |
| 35 | Giriş/çıxış kartında bayquş **yenə titrəyirdi**; kartlarda mövzudan asılı olmayan ümumi sprite; istifadəçi: **sabit dayansın, hər mövzuya uyğun açılış/qapanış bayquşu olsun** | `Cards.tsx` `CardOwl`: 7 px sinus `bob` + spring ilə aşağıdan gəlmə (#25 yalnız səhnə bayquşunu `Owl.tsx`-də düzəltmişdi) | `CardOwl` sabit (yalnız 8 kadr fade); `render_owls.run_cards` hər epizoda `owl/intro.png` (qolunu açıb 'başlayaq', əşyanı göstərir) + `owl/outro.png` (gözlər yumulu əl yelləyir, baş əyir); mövzu əşyası `choose_prop` ilə əvvəlcədən seçilir (ekran/yazı/personaj yox), ikisində eyni; hakimdən keçməsə köhnə sprite; en ≤ 470 px (başlığı örtmür). Render sübutu: bayquş bölgəsi kadrlar arası fərq ≤ 11 (fon zoom-u) (`test_card_owls.py`). Test: `test_card_owls.py::test_card_owl_does_not_move`, `test_card_owls.py::test_card_actions_are_topic_specific_opening_and_closing` |
| 36 | OpenAI `gpt-image-2` şəffaf fonu rədd edir (HTTP 400) → **bütün səhnə bayquşları səssizcə köhnə sprite-a düşərdi**, mərhələ yenə keçərdi | `_draw` hər LLMError-u 'bu səhnədə sprite' kimi udurdu; `render_owls` verify `[]` idi | bayquş modeli **gpt-image-2 qalır** (istifadəçi): bircins magenta (#FF00FF) fonda çəkilir, `key_out` fonu lokal silir (bütün şəkildə — şüşədən görünən fon da; yarımşəffaf kənarda fon rəngi çıxarılır, magenta qalığı 0 piksel); fon magenta/bircins deyilsə şəkil yenidən çəkilir; 'not supported for this model' xətası mərhələni dayandırır; `verify_owls`: səhnə bayquşlarının ≥ 80%-i + intro/outro kartı olmalıdır. Test: `test_owl_keying.py::test_owl_uses_gpt_image_2_on_a_solid_magenta_background`, `test_card_owls.py::test_model_rejecting_transparency_stops_the_stage_instead_of_silent_sprites`, `test_card_owls.py::test_owl_stage_fails_when_most_scene_owls_fell_back_or_cards_missing` |
| 37 | İstifadəçi: video **10–12 dəq** olsun (əvvəl 8–10) | — | `MIN_SECONDS=600`, `MAX_SECONDS=720`, `DEFAULT_WORDS=1530` (ölçülmüş 1230 söz → 8.85 dəq), outline '~11 minute'; söz/TTS qapıları və final video yoxlaması yeni aralıqla işləyir. Test: `test_pipeline.py::test_parse_args_requires_topic_or_resume`, `test_pipeline.py::test_verify_video_rejects_a_video_longer_than_max` |
| 38 | `scene_plan` 3 dəfə çökdü: "ehtiyat fon çatmır: 43 lazım, 39 var" (why-9-99, 2026-10-01); qiymət mövzusunda LLM hər səhnəyə "price tag $9.99" yazır → 65-dən 57-si boş fona düşürdü; "$10" rəqəmləri filtrdən keçirdi; gpt-4o artikl yazmır → hamısı atılırdı; ehtiyat fonlar mövzudan kənar (mayak) | LLM qadağaya əməl etmir + filtr boşluqları (`$`/rəqəm, labels, sticker, logo, form, card, review…; "two …", "close-up of", "side by side"); generik hovuz mövzusuzdur | `TEXT_BEARING` `$`/rəqəm + çap olunan şeylər, qiymət bəndi kəsilir, ilk hissəyə artikl, `hero` düzəlişi; SYSTEM/RETRY-də "no price tags/digits"; **`topic_pool`**: qalan səhnələr əvvəlcə mövzuya aid təkrarsız fonlar, generik hovuz yalnız sonda. Test: `test_price_topic.py`. Əlavə: hovuzdan "leather messenger bag" çıxarıldı (briefcase ilə eyni kadr, check_bgs [55,58]). Test: `test_price_topic.py::test_prices_and_digits_never_reach_the_background_prompt`, `test_price_topic.py::test_printed_things_are_dropped`, `test_price_topic.py::test_prompt_without_article_keeps_its_subject`, `test_price_topic.py::test_llm_is_told_no_price_tags`, `test_price_topic.py::test_fallback_pool_has_no_look_alike_bags` |
| 39 | `make_srt` qapısı 3 dəfə düşdü: "whisper 1776 söz, skript 1646 söz" (why-9-99, 2026-10-01) — səs düzgün idi | Whisper `$9.99` → "9 dollars and 99 cents" (5 söz), `$10` → "10 dollars" (2); skript sayğacı 1 sayırdı | `stages.spoken_words`: qiymətlər tələffüz kimi sayılır (1762 vs 1776 = 0.8%). Test: `test_price_topic.py::test_srt_gate_counts_prices_as_spoken` |

| 40 | **Videoda yenə kobud hesab səhvi** (why-9-99): "three clients a month at $50 an hour … instead of earning **$600** … you'd pull in **$649.97** for four clients" — saat sayı yoxdur, rəqəmlər uyğunsuz; `math_check` [] verdi. İstifadəçi: **"birdəfəlik həll et"** | (1) fail-open: səhv yalnız 3 baxışın çoxluğu EYNİ düzgün dəyəri tapanda sayılırdı — baxışlar fərqli ifadə verdi (`49.99*4` / `3*50` / "hesab deyil") → susdu; (2) natamam hesab (giriş yoxdur) halı ümumiyyətlə tanınmırdı; (3) `4`, `12`, `3`… sabitləri istənilən uydurma ifadəni "əsaslandırırdı"; (4) generator gizli girişlə nəticə yazırdı | **`number_audit.py` — son hökm, fail-closed:** HƏR rəqəm deterministik işarələnir (hərfli marker `⟦A⟧`, sorğuda ≤ 26 — rəqəmli/ikihərfli markeri gpt-4o qarışdırırdı); rol: given / result (ifadə, operandlar rəqəmdən ƏVVƏL deyilməli) / missing; rəqəm yalnız ≥2/3 təsdiqlə keçir; şübhəli rəqəmə fokuslu 2-ci baxış (əvvəlki bölmələr + başlıq kontekstdə; başlıqdakı/əvvəl deyilmiş ≥13 rəqəmin təkrarı ok); keçməsə abzas yenidən yazılır — **bayraqsız rəqəmlər dəyişə bilməz** (real: `$9.99`→`$10` pozulması bloklandı); raundlardan sonra cümlə rəqəmsiz yazılır, olmasa silinir. Sabitlər yalnız vahid sözləri ilə (4 = həftə+ay, 12 = ay+il…). 1-ci qat (`math_check`) yalnız düzəliş ön-keçididir. Generator: "hər girişi nəticədən əvvəl de, gizli kəmiyyət yox, 49.99-u vurma". Real ölçü: why-9-99 3/3 tutuldu və düzəldi (yalnız həmin abzas dəyişdi), payment-fees köhnə $800 səhvi 3/3, yalançı həyəcan 6 run-da 1 (nəticəsi yalnız abzas yoxlaması). Test: `test_number_audit.py` (20) — `test_number_audit.py::test_real_bug_disagreeing_passes_flag_both_results`, `test_number_audit.py::test_hours_cannot_be_smuggled_in_as_a_constant`, `test_number_audit.py::test_number_audit_is_the_final_authority` |
| 41 | `math_check` gpt-4o TPM 429-a 81 dəfə düşdü, 4 dəfə 3-cü cəhdə çatdı (1 cəhd qalmışdı) | backoff 1-2-4 s, API "try again in 2.27s" deyirdi | 429-da API-nin dediyi müddət + 1 s, 8 cəhd (`llm.retry_after`, `RATE_RETRIES`). Test: `test_llm.py` — `test_llm.py::test_rate_limit_waits_as_long_as_the_api_says`, `test_llm.py::test_retry_after_parses_milliseconds` |
| 42 | Çıxış kartı bayquşu mövzu əşyası (qiymət etiketi) əvəzinə kitab tutdu, hakim keçirdi; yenidən çəkiləndə "price tag with a dollar amount" 3 dəfə `text` ilə yıxıldı (why-9-99, 2026-10-03) | referans sprite kitab tutur, outro "tucked under the other arm" → model kitabı köçürür; kart hakimi əşyanı yoxlamırdı; LLM əşyası yazı nəzərdə tuturdu | kart pozunda əşya "instead of the book" + "(blank, with no writing or numbers)"; kart hakiminə `missing_prop` (`judge_system(prop)`); `test_card_owls.py` (3 test). Test: `test_card_owls.py::test_card_prop_replaces_the_reference_book`, `test_card_owls.py::test_card_judge_rejects_owl_without_the_topic_prop`, `test_card_owls.py::test_card_prop_is_drawn_blank_so_judge_does_not_reject_it_for_text` |
| 43 | `make_srt` qapısı yalan yerə yıxıldı: whisper 1659, skript 1776 söz (why-9-99, 2026-10-03) | #39 whisper-in qiyməti "9 dollars and 99 cents" yazdığını fərz edirdi; bu dəfə `$9 .99` (2 token) yazdı — format işdən-işə dəyişir | `whisper_word_count` whisper sözlərini skript formasına (`$9.99`, `$10`) gətirir, skript qiyməti 1 söz sayır; `test_price_topic.py::test_srt_gate_counts_prices_as_spoken` hər iki format |
| 44 | Videoda 587 s-də 0.67 s tam sükut (why-9-99, 2026-10-03) | Stable Audio klipin ORTASINDA ~1 s pauza verdi (music.wav 142 s, −40 dB); #26 yalnız klip uclarını kəsirdi; danışıq pauzası ilə üst-üstə düşdü | `music_gen.build_track`: yekun trekdə daxili boşluq (`silencedetect −40 dB/0.4 s`, son fade sayılmır) varsa yeni seed ilə yenidən (3 cəhd), alınmasa ən az sükutlu qalır; `test_music_gen.py` (3 test). Test: `test_music_gen.py::test_internal_music_gaps_are_found_but_end_fade_is_ignored`, `test_music_gen.py::test_track_with_a_gap_is_regenerated_with_a_new_seed`, `test_music_gen.py::test_hopeless_gaps_keep_the_least_silent_try` |
| 45 | İstifadəçi (2026-10-03): **hər səhnədə mövzuya uyğun, məntiqli analitik Remotion animasiyası; şəkil sayı azalsın** — seçim: ~60% animasiya | hər səhnə yalnız foto + Ken Burns idi (~53 şəkil) | `visuals.py`: LLM hər səhnəyə chart spec (bars/line/compare/ring/equation/flow/timeline/counter/keypoints) + bal verir; **chart-dakı hər rəqəm (dəyər və etiket) həmin səhnənin danışığında deyilməlidir**, ring yalnız deyilmiş faiz, equation hesabı Python-da yoxlanır — keçməsə rəqəmsiz `keypoints`, o da olmasa foto (fail-closed); `choose_animated`: ~60%, ilk səhnə foto, ardıcıl ≤3 animasiya. `scene_plan` fonu yalnız foto səhnələrinə planlayır; `render_bgs`/`check_bgs`/`upscale_bgs`/`prepare_public` animasiya səhnəsini ötürür (köhnə fotosu silinir). Remotion `visuals/` (StudioBackdrop + 9 komponent), `reveal_frames`: element rəqəmi/etiketi səslənəndə açılır. Test: `test_visuals.py` — `test_visuals.py::test_number_not_in_narration_is_rejected`, `test_visuals.py::test_equation_arithmetic_is_checked`, `test_visuals.py::test_choose_animated_takes_share_and_keeps_first_scene_photo`, `test_visuals.py::test_reveal_follows_the_spoken_numbers` |
| 46 | Giriş kartı 1-ci, çıxış kartı son səhnənin fotosunu **təkrar** göstərirdi | `episode_props` `introBg/outroBg` = səhnə fonu | kartlar Remotion dizayn fonu (`StudioBackdrop`) ilə; `test_no_repeats.py::test_cards_do_not_reuse_scene_photos` |
| 47 | İstifadəçi: **thumbnail daha keyfiyyətli olsun** (why-9-99: qiymət mövzusunda qəhvə qovurma maşını fonu, tək rəngli yazı, ümumi sprite) | fon səhnə fotolarının "ən kontrastlısı" idi | `thumbnail.py`: LLM `thumb_scene` → gpt-image-2 **high** 2 variant → gpt-4o hakimi (yazı/insan yox, ən cəlbedici); `cards.thumbnail`: sol tünd keçid, avtomatik ölçülü 2–3 sətir, açar söz (`thumb_highlight`) sarı, kontur + kölgə, brend nişanı, mövzu əşyalı `owl/intro.png` işıq halesi ilə; alınmasa köhnə yol. Model dəyişmədi (istifadəçi). Test: `test_thumbnail.py` — `test_thumbnail.py::test_make_background_returns_judged_best`, `test_thumbnail.py::test_highlight_word_is_drawn_in_accent_colour`, `test_thumbnail.py::test_write_pack_uses_generated_background_and_topic_owl` |
| 49 | E2E break-even (2026-10-04): chart-da `".."` maddələri, 40 animasiyanın 22-si keypoints, "Common Mistakes" başlığı 5 dəfə; "$4" ekranda "4"; `%`/dollar regex-ində `\b` əvəzinə 0x08 (ring faiz yoxlaması səssizcə zəif idi) | LLM promptdakı `["..",".."]` nümunəsini köçürdü; seçimdə növ/başlıq nəzarəti yox idi; vahidi LLM verirdi | mətn ≥3 hərf, nümunə real; keypoints ≤30%, eyni başlıq bir dəfə; vahid hər elementə danışıqdan (`unit_of`), +/− düsturda ortaq vahid; mənbədə 0x08 tutan test (`test_spoken_titles.py`). Test: `test_visuals.py::test_placeholder_text_is_rejected`, `test_visuals.py::test_titles_never_repeat`, `test_visuals.py::test_each_item_gets_its_unit_from_the_narration`, `test_visuals.py::test_addition_and_subtraction_share_one_unit`, `test_spoken_titles.py::test_no_backspace_characters_in_source` |
| 50 | Ssenaridə "$9.99 vs $10 … saving money, even if it's just **a dollar**" (fərq 1 sentdir) audit-dən keçdi (why-9-99, 2026-10-04, run `scene_plan`-da dayandırıldı) | (1) `find_numbers` "a dollar"/"a cent"-i rəqəm saymırdı; "nine ninety-nine" = 108 oxunurdu; (2) `judge`: 1 baxış Python-da səhvi sübut etdi (`10 - 9.99`), 2 "given" səsi onu örtdü; (3) prompt təsadüfi qənaəti "result" saymırdı; düzəlişdən sonra: düzgün dəyər 0.0001 (iddiada "cent" olmadan /100), ".99 prices" və əvəzlik "the one" yalançı həyəcan verdi | "a dollar/a cent" = 1/0.01, "nine ninety-nine" = 9.99; **hesabla təkzib olunmuş rəqəm səs çoxluğu ilə keçmir**; EXTRACT/FOCUS promptunda "just a dollar → 10 − 9.99"; /100 yalnız iddiada "cent" olanda; ".99" sonluq etiketi və "the/that/which one" (ardınca vahid yoxdursa) işarələnmir. Real ölçü: köhnə ssenaridə əvvəl 0/1, sonra 4/4 run-da yalnız "a dollar" (0.01). Test: `test_number_accuracy.py` (4), `test_number_audit.py` (5) — `test_number_accuracy.py::test_parse_number_reads_spoken_and_digit_forms`, `test_number_audit.py::test_one_pass_proving_a_number_wrong_beats_two_given_votes`, `test_number_audit.py::test_dollar_gap_fix_value_is_not_divided_into_cents`, `test_number_audit.py::test_pronoun_one_is_not_a_number_but_one_cent_is` |
| 51 | Planda counter "Cents Add Up" = **1** (vahidsiz, etiket "Price difference"); danışıq: "One common mistake … a price difference of one cent" (why-9-99, 2026-10-04; `render_bgs` 10/38-də dayandırıldı, `--from scene_plan`) | `visuals.grounded_values` cümlə əvvəlindəki "One" (= bir səhv) sözünü 1 kimi "deyilmiş" sayırdı | tək "one" sözü chart rəqəmini əsaslandırmır (0.01 "one cent"-dən keçir, vahid `$`). Test: `test_visuals.py::test_bare_word_one_does_not_ground_a_chart_number` |
| 52 | Animasiya payı 44% → yenidən planda 37% (hədəf ~60%) (why-9-99, 2026-10-04; `render_bgs` dayandırıldı) | mücərrəd mövzuda LLM 68 səhnədən 33-ə keypoints verdi, limit (12) qalanını atdı; keçərli qeyri-keypoints cəmi 12; son chunk-da LLM 64–68-i qaytarmadı | `plan_visuals`: buraxılan səhnələr bir dəfə yenidən soruşulur (`_ask_all`); pay çatmasa seçilməmiş keypoints/keçməyən səhnələr "Do NOT use keypoints" ilə yenidən soruşulur, yalnız keçərli qeyri-keypoints spec qəbul olunur. Real ölçü: 25/68 → 41/68 (60%). Test: `test_visuals.py` (2) — `test_visuals.py::test_plan_visuals_asks_again_without_keypoints_when_share_is_short`, `test_visuals.py::test_plan_visuals_re_asks_scenes_the_llm_skipped` |
| 53 | Hazır videoda "Price Difference Impact" (sc53) chart-ı 13.7 s-lik səhnənin 11 s-i boş idi (yalnız başlıq) (why-9-99, 2026-10-05, son vizual yoxlamada tapıldı) | `reveal_frames`: ilk element ("Cents") danışıqda yalnız sonda səslənir ("those cents add up"), qalanlar ondan sonra sıralanır | ilk element ən gec səhnənin 35%-ində açılır (`FIRST_REVEAL_MAX`); video `--from build_episode` ilə yenidən render. Test: `test_visuals.py::test_first_element_never_waits_until_the_end_of_the_scene` |
| 54 | İstifadəçi (2026-10-05, addım 10–11): rəqəmlər düzgün ingilis tələffüzü ilə; altyazı ssenaridən, "$4,000" formatı. Köhnə videoda altyazı whisper-in idi ("$9 .99", "Marketing Strategy Retailers are…") | TTS mətni xam gedirdi ("$9.99", "1994-2020" Kokoro-nun öz oxunuşu); SRT whisper transkripsiyası idi | `speech.py`: `to_speech` (pul/faiz/il/aralıq/ordinal → ingilis sözləri, `tts_gen.synth`), `to_display` ("four thousand dollars" → "$4,000"); `captions.py` mərhələsi (make_srt-dən sonra): hər seslenen hissənin pəncərəsində ssenari sözləri whisper vaxtlarına uyğunlaşdırılır → `captions.words.json` (Remotion), `captions.srt` (təhvil); ssenaridəki hər rəqəm həmin pəncərədə whisper-də eşidilməlidir, yoxsa mərhələ keçmir. Test: `test_speech.py`, `test_captions.py` — `test_speech.py::test_numbers_are_spelled_for_the_voice`, `test_speech.py::test_tts_sends_every_text_through_the_number_normaliser`, `test_captions.py::test_srt_uses_display_numbers`, `test_captions.py::test_mispronounced_number_is_reported` |
| 55 | İstifadəçi (addım 9): bölmə etiketi slayd başlığının üstünə düşür (why-9-99 276 s: "Marketing Strategy" lower-third + chart başlığı üst-üstə) | lower-third (y 60–150) chart başlığı ilə (y 175) eyni sol küncdə | chart səhnəsində lower-third yox, bölmə adı başlığın üstündə kiçik sarı `Kicker` (y 100); `episode_props` `lowerThird`/`kicker`. Test: `test_remotion_build.py` — `test_remotion_build.py::test_chart_scene_gets_section_as_kicker_not_a_lower_third` |
| 56 | İstifadəçi (addım 4): ilk 3 saniyədə konkret rəqəm və ya paradoks | giriş kartı yalnız mövzu başlığını oxuyurdu | ssenaridə `## Cold Open` (≤16 söz, rəqəm ilk 9 sözdə — `cold_open_problems`, olmasa yenidən yazılır); giriş kartı onu səsləndirir və başlığın altında göstərir (`IntroCard hook`); səhnələrə düşmür. Test: `test_script_story.py`, `test_speech.py` — `test_script_story.py::test_cold_open_has_a_number_within_the_first_three_seconds`, `test_script_story.py::test_cold_open_is_spoken_on_the_intro_card_not_as_a_scene`, `test_speech.py::test_intro_card_speaks_the_cold_open_or_falls_back_to_the_topic`, `test_remotion_build.py::test_intro_card_shows_the_hook_line` |
| 57 | İstifadəçi (addım 7): hər rəqəm qrafik/kartla, generik bullet-lər olmasın | rəqəmli səhnə foto ola bilərdi, chart rəqəmlərin bir hissəsini göstərirdi; keypoints = bullet | `keypoints` ləğv; yeni `stats` (data kartları, Remotion `Stats`); rəqəmli səhnə həmişə animasiya, chart bütün rəqəmləri göstərmirsə "Show EVERY figure" ilə yenidən soruşulur, sonra deterministik `stats_fallback`. Test: `test_visuals.py` (5 yeni) — `test_visuals.py::test_generic_bullets_are_not_accepted_any_more`, `test_visuals.py::test_scene_with_figures_is_always_animated_even_beyond_the_share`, `test_visuals.py::test_stats_fallback_puts_every_figure_on_a_card`, `test_visuals.py::test_llm_is_asked_again_when_a_figure_is_missing_from_its_chart` |
| 58 | İstifadəçi (addım 3): hər videoda ən azı 1 tədqiqat/rəsmi mənbə | ssenari mənbəsiz idi (uydurma statistika qadağan idi) | `research.py`: gpt-4o web_search namizədləri → domen .gov/.edu/tədqiqat → URL yüklənir (HTML/PDF) → rəqəm + iddia sözləri olan cümlə SƏHİFƏDƏN götürülür (≤350 simvol) → gpt-4o hakimi "statistika + qərara aid". Probe: mini 12 namizəddən 0 (404 URL, parafraz, Beige Book anekdotu, bls/census 403) → gpt-4o axtarış. Skriptdə mənbə adı + rəqəm eyni abzasda, description-da link. Tapılmasa script_gen dayanır. Test: `test_research.py` (19) — `test_research.py::test_verified_source_passes_and_quote_comes_from_the_page`, `test_research.py::test_figure_not_on_page_fails`, `test_research.py::test_only_official_or_research_domains`, `test_research.py::test_script_must_cite_the_source_with_its_figure`, `test_publish_pack.py::test_description_names_the_verified_source` |
| 59 | İstifadəçi (addım 1,2,5,6,12): yalnız B2B qərar, anlayış yoxlaması, bir case, təkrar yox / Recap yalnız nəticələr, ABŞ | plan yalnız 4 bölmə + analogiya idi, auditoriya "işçilər/freelancer", case yox | plan: `decision`/`answer`/ABŞ `case`/`cold_open`/`fact_need`; `script_qa.py`: deterministik (sual-qərar, ABŞ ştatı, case sahibi Hook + hər bölmədə, Recap-da rəqəm/ad yox, mənbə) + gpt-4o redaktor (terif, analogiya, qərara cavab, təkrar, Recap) → problemli bölmə yenidən yazılır; `script_qa.json` (sha) olmadan `script_gen` keçmir. Test: `test_script_story.py` (17) — `test_script_story.py::test_plan_must_name_a_business_decision_question`, `test_script_story.py::test_case_must_be_in_the_united_states`, `test_script_story.py::test_case_owner_must_run_through_every_teaching_section`, `test_script_story.py::test_recap_states_only_conclusions`, `test_script_story.py::test_verify_script_stage_requires_quality_report` |
| 60 | İstifadəçi (addım 8): kadrlar mövzuya uyğun, generik/metafor < 10% | art director "physical metaphor" istəyirdi (donuz qumbarası, qum saatı), ehtiyat hovuz generik | scene_plan: LITERAL qayda + case biznesi qeydi (`case_note`), RETRY_NOTE metaforsuz; hakimə `generic` yoxlaması (yenidən çəkilir); `bg_qa.json generic_share` (hakim + hovuz fonu) > 10% → check_bgs keçmir. Test: `test_literal_frames.py` — `test_literal_frames.py::test_judge_flags_generic_or_metaphor_pictures`, `test_literal_frames.py::test_stage_fails_when_more_than_ten_percent_of_photos_are_generic`, `test_literal_frames.py::test_art_director_asks_for_literal_business_pictures_not_metaphors` |
| 61 | E2E raise-your-prices (2026-10-05) run 1–2: redaktor "OK" dedi, amma cavab qeyri-müəyyən ("Aim for a balance…"), "$2,000 per project" 4 bölmədə, case iki dəfə yenidən tanıdıldı; uzatma bölməsi qərardan SONRA düşüb ziddiyyət yaratdı ($3.30 vs $3.10); mənbə təhrif olundu ("61% raised prices" → "…without losing their customer base"); `story_fixes` "Section 3: Testing" başlığını ":" ilə kəsib "Section 3" edirdi | redaktor meyarları yumşaq; plan cavabı yoxlanmırdı; `extend` "Common Mistakes"-dən əvvələ yazırdı; başlıqda ":" | `plan_problems` (sual-qərar, ABŞ, **şərtli cavab + rəqəm**) — pozulsa outline səbəblə yenidən (3); `repeated_figures` (eyni rəqəm > 2 bölmə → orta bölmələr yenidən, qərar/cavab rəqəmi istisna); redaktora `consistent`, `source_faithful`, sərt `answers_decision`/`repeats`; bölmə qaydası "case-i yenidən tanıtma"; `extend` son (qərar) bölməsindən əvvəl + `renumber_sections`; başlıq real başlıqla tutuşdurulur. Test: `test_script_story.py` (+9) — `test_script_story.py::test_answer_must_be_a_concrete_conditional_rule`, `test_script_story.py::test_same_figure_in_more_than_two_sections_is_a_repeat`, `test_script_story.py::test_review_checks_story_consistency_and_source_faithfulness`, `test_script_story.py::test_extension_goes_before_the_decision_section_and_sections_are_renumbered`, `test_script_story.py::test_owner_fix_targets_the_full_section_heading`, `test_script_story.py::test_outline_and_sections_ask_for_a_concrete_rule_and_no_reintroductions` |
| 62 | Keyfiyyət qapısında düşən `script.md` qalırdı → pipeline retry (`--force`-suz) "artıq mövcuddur" ilə boşuna yıxılardı | retry eyni əmri `--force`-suz təkrarlayır | `needs_regeneration`: `script_qa.json`/`math_check.json` təmiz deyilsə skript yenidən yazılır. Run 3-də 2 retry məhz bununla keçdi. Test: `test_failed_script_is_regenerated_on_stage_retry` — `test_script_story.py::test_failed_script_is_regenerated_on_stage_retry` |
| 63 | Rəqəm auditi "losing $250 for each client" cümləsini səhv saydı (750 − 1000 = −250) | itki/fərq müsbət deyilir, yoxlama işarəni müqayisə edirdi | `-` olan ifadədə mənfi nəticənin modulu da qəbul (`_check_one`). Test: `test_loss_stated_as_positive_amount_matches_negative_difference` — `test_number_accuracy.py::test_loss_stated_as_positive_amount_matches_negative_difference` |
| 64 | E2E raise-your-prices run 3 (2026-10-05): OpenAI balansı bitəndə `check_bgs` → `render_bgs` "UGURSUZ ... BALANSI BITIB", amma pipeline traceback alıb 2 dəfə boşuna retry etdi | `render_bgs` adi `SystemExit("N fon cekilmedi")`, `rerender` `check=True` → "BALANSI BITIB" pipeline-ın `NO_RETRY`-na çatmırdı | `render_bgs.exit_code` balans xətasında `EXIT_NO_BALANCE`(3); `check_bgs.rerender` onu "OpenAI BALANSI BITIB" `SystemExit`-ə çevirir → retry yox. Test: `test_check_bgs.py` (+3) — `test_check_bgs.py::test_rerender_turns_balance_exit_into_no_retry_message`, `test_check_bgs.py::test_render_bgs_exit_code_for_balance_errors`, `test_check_bgs.py::test_rerender_other_failure_still_raises` |
| 65 | Run 3 raund 1: 26 fotodan 18-i pis, əksəri `generic`; yeni təkliflər case-dən qopdu (agentlik videosunda "un kisələri çörəkxanada", "qlobus", "liman konteynerləri") | hakim və `suggest_again` yalnız səhnə danışığını görürdü, case biznesini (`meta.json plan.case`) yox — agentliyin öz otağı "generic" sayılırdı, təkliflər təsadüfi biznesdən gəlirdi | `case_note` hakimə (`judge_text`) və `suggest_again`-ə ötürülür; "generic" tərifi: case biznesinin real yeri/aləti generik DEYİL; təkliflər yalnız case biznesindən. Test: `test_check_bgs.py` (+3) — `test_check_bgs.py::test_judge_text_carries_the_case_business`, `test_check_bgs.py::test_suggest_again_sends_the_case_business`, `test_check_bgs.py::test_generic_rule_keeps_the_case_business_own_places` |
| 66 | Run 4 (2026-10-06): `check_bgs` `AttributeError: 'NoneType' object has no attribute 'strip'` ilə çökdü | gpt-4o şəkli rədd edəndə `content: null` (+`refusal`) qaytarır; `llm.chat` `None.strip()` edirdi, hakimin `except LLMError`-u tutmurdu | `llm.chat`: content sətir deyilsə `LLMError("bos cavab (refusal) …")` → hakim yenidən soruşur, proses yıxılmır. Test: `test_llm.py::test_chat_null_content_is_an_llm_error_not_a_crash` |
| 67 | Run 5 (2026-10-06): case-aware hakimlə də raund 2-də 20-dən 18 foto pis (`generic`) — abstrakt cümlələr ("xərc strukturu", "qərar aydındır", "price elasticity") üçün digital agentlikdə literal obyekt yoxdur → ofis kreslosu/lampa/abstrakt tablo | foto abstrakt məzmunu literal göstərə bilmir; yenidən çəkmə yalnız başqa generik obyekt verir, sonda generik hovuz → `generic_share` > 10% | `check_bgs.to_animate`: bir dəfə yenidən çəkilib hələ `generic` qalan foto yenidən çəkilmir → `visuals.animate_abstract` (flow/compare/timeline, bullet-siz, başlıq təkrarsız, rəqəm qaydası) → `scenes.json visual`; son cəhddən sonra qalan generik/hovuz da animasiyaya; animasiya alınmasa foto qalır və pay qapısı fail-closed. Test: `test_check_bgs.py` (+3), `test_visuals.py` (+3) — `test_check_bgs.py::test_scene_still_generic_after_a_redraw_is_animated`, `test_check_bgs.py::test_apply_visuals_marks_scenes_animated`, `test_check_bgs.py::test_animated_scenes_leave_the_generic_report`, `test_visuals.py::test_animate_abstract_returns_valid_bullet_free_specs` |
| 68 | Run 6 (2026-10-06): uzunluq qapısı skript ~10.9 dəq dedi, TTS 725 s (12.1 dəq) → qısaltma + `scene_plan`-dan təkrar (bütün fon/bayquş yenidən) | `word_gate` skript sözlərini sayırdı; `to_speech` rəqəmləri sözə açır (+~6%: 1534 → 1633 söz), run 3-də uzatma da lazımsız işə düşmüşdü | `pipeline.spoken_words` (başlıqsız mətn → `to_speech` → söz sayı) uzunluq qapısında. Test: `test_pipeline.py` (+2) — `test_pipeline.py::test_length_gate_counts_spoken_words_with_numbers_expanded`, `test_pipeline.py::test_word_gate_uses_spoken_words` |
| 69 | Run 6 qısaltmadan sonra `scene_plan`: 25 fotodan ~8-i generik hovuzdan (gear mechanism, stopwatch, briefcase, port konteynerləri, anbar, konveyer) — digital agentlik case-i ilə əlaqəsiz | tekrar/yazı filtri promptu silir → `photo_repeats` hovuza düşür; hovuz tərifə görə generikdir, check_bgs onu 2 raund boşuna yenidən çəkib sonra animasiyaya çevirirdi (#67) | `scene_plan.animate_pool_scenes`: hovuz fonu alan foto səhnə planda `animate_abstract` ilə animasiya olur; alınmasa foto qalır (check_bgs #67 tutur). Test: `test_literal_frames.py::test_scene_given_a_generic_pool_photo_is_animated_at_plan_time` |
| 70 | raise-your-prices yekun kadrları (2026-10-06): data kartlarında qırıq yazılar — "15% Prices by", "$1,150 She'll still be", "Up more", "Would leave", "Employer small busines"; yenidən adlandırmada LLM "fewer than 10 would leave" → "Clients likely to stay" (ekranda YANLIŞ fakt), "61% of firms raised prices" → "Price Increase" verdi | `stats_fallback` yazını regex-lə rəqəmin ətrafından kəsirdi (22 simvolda söz ortasından); LLM stats kartları da yoxlanmırdı; adın mənası yoxlanmırdı | `label_ok` (əvəzlik/qısaltma/köməkçi sözlə bitən yazı yox, yiyəlik "Lisa's" olar); bütün stats kartları `name_cards` ilə adlanır (limit promptda, rəqəm "15%"/"$1,150" kimi, rədd səbəbi ilə 3 cəhd) + `labels_faithful` mənaca yoxlama (pay ≠ dəyişiklik; xətada fail-closed → "Key figure"); regex yazısı söz sərhədində kəsilir. Test: `test_visuals.py` (+10) — `test_visuals.py::test_fragment_labels_are_rejected`, `test_visuals.py::test_any_stats_card_with_fragment_labels_is_renamed`, `test_visuals.py::test_card_label_that_contradicts_the_narration_is_rejected`, `test_visuals.py::test_label_limits_are_told_to_the_namer_and_regex_labels_cut_on_word_boundary` |
| 71 | İstifadəçi 2026-10-07 (bənd 5/6 sərtləşdi): raise-your-prices-də köməkçi başqa biznes nümunələri (aşpaz, yük daşıma) bütöv səhnələr tutdu; "$1,150" bir bölmədə 3 dəfə deyildi | outline promptu analogiya üçün açıq-aşkar BİZNES sahələri təklif edirdi ("commercial kitchen, trucking route…"), EXTEND "realistic mini-example" istəyirdi; `repeated_figures` bölmə sayırdı və qərar rəqəmini istisna edirdi | prompt: yalnız case, analogiya = rəqəmsiz bir cümləlik gündəlik təsvir, başqa biznes YOX, hər rəqəm ≤ 2 dəfə; redaktor `single_case` açarı; `repeated_figures` hər deyilişi sayır (qərar rəqəmi də), ortadakı deyilişlərin bölməsi yenidən yazılır. Test: `test_script_story.py` (+4, 1 dəyişdi) — `test_script_story.py::test_analogies_are_everyday_images_never_another_business`, `test_script_story.py::test_reviewer_flags_examples_from_other_businesses`, `test_script_story.py::test_same_figure_three_times_in_one_section_is_a_repeat`, `test_script_story.py::test_decision_figure_is_limited_to_two_mentions_too` |
| 72 | İstifadəçi 2026-10-07 (hibrid): #67/#69 ilə animasiya payı ~84%-ə çıxdı ("~60%" qərarı pozulurdu) | generik foto həmişə animasiyaya keçirdi, tavan yox idi | `visuals.ANIM_MAX` = 0.70, `animation_room`; `check_bgs.animate` və `scene_plan.animate_pool_scenes` yalnız tavana qədər çevirir, qalanı case kadrı ilə yenidən çəkilir; generik <10% qapısı qalır (RİSK: literal kadr alınmasa mərhələ dayanır — növbəti E2E-də yoxla). Test: `test_visuals.py`, `test_check_bgs.py`, `test_literal_frames.py` (+3) — `test_visuals.py::test_animation_room_respects_the_70_percent_cap`, `test_check_bgs.py::test_generic_photos_beyond_the_cap_stay_photos`, `test_literal_frames.py::test_plan_time_pool_animation_respects_the_cap` |
| 73 | Faza 1.1 (istifadəçi 2026-10-07): qərar nəticəsi case-in dəyişənini buraxırdı ("40 customers × $5 = $200 extra" — gedən müştərilər unudulur), case rəqəmləri ssenaridə uyğunsuz ("out of 100 customers") | ssenari rəqəmlərini LLM sərbəst yazırdı, deterministik case modeli yox idi | `case_model.py`: plan `model` (variables/before/after/threshold), ast hesab (eval yox; yalnız ad, rəqəm, + − × ÷, ceil/floor/round/min/max), dövri istinad/naməlum ad → plan yenidən; `plan.model_result` (before/after/delta/threshold/insight/units) meta.json-a; `case_problems`: (a) qərar bölməsi rəqəmi modeldə, (b) "N <case ismi>" modelə uyğun, (c) naive (dəyişən 0/1 ilə neytrallaşdırılır) → "dəyişən buraxılıb"; ssenariyə "use exactly these figures". Test: `test_case_model.py::test_naive_calculation_that_drops_a_variable_is_caught`, `test_case_model.py::test_case_quantity_that_contradicts_the_model_is_caught`, `test_script_story.py::test_story_checks_include_the_case_model` |
| 74 | Real probe (2026-10-07, 7 mövzu): gpt-4o-mini modeli sxemi səhv oxudu ("result_name"), nümunəni köçürdü (lizinq mövzusunda qiymət modeli), naməlum ad/prefiks/özünə istinad, vahidsiz dəyişən, nəticəni giriş kimi yazdı, cavab threshold-dan fərqli rəqəm dedi (80 vs 250), mənfi threshold; retry-da eyni səhvi 5 dəfə təkrarladı | mini cəbri və sxemi etibarlı qurmur; bütün planı yenidən yazanda düzəlişi tətbiq etmir | prompt: konkret domen nümunəsi yox, sxem nəsrlə; `names_hint` redd mesajında; vahid addan (`infer_unit`); `after`-də özünə istinad = before dəyəri, bloklarda `before_x/after_x`, threshold-da prefikssiz ad (giriş dəyişəni üstün); nəticə adlı dəyişən rədd; cavab hesablanmış threshold ilə ayrıca yazılır (`answer_from_model`); threshold ≤ 0 → model xətası; **gpt-4o model yoxlaması** (`review_model`, yalnız obyektiv xətalar) + yalnız model JSON-un təmiri (`repair_model`, yoxlama qatı gpt-4o, number_audit kimi). Probe: son 6 mövzunun hamısı keçdi. Test: `test_script_story.py::test_rejected_model_is_repaired_without_replanning`, `test_script_story.py::test_answer_must_state_the_model_threshold`, `test_case_model.py::test_missing_unit_is_inferred_from_the_name` |
| 75 | Faza 1.2: Cold Open case-dən asılı olmayan LLM cümləsi idi | — | Cold Open = `model_result.insight` (biri düşür, digəri qalxır; rəqəm ilk 9 sözdə); `cold_open_problems(line, allowed)` modeldə olmayan rəqəmi tutur. Test: `test_script_story.py::test_cold_open_is_built_from_the_model_insight`, `test_script_story.py::test_cold_open_figure_must_be_in_the_model` |
| 76 | Faza 1.3: uydurma rəqəm ("costs rose more than 9%") "given" kimi keçirdi; OUTLINE promptunda rəqəmli nümunə cavablar (5%, 1 in 10, $9.99) köçürülürdü | `number_audit` "given" rolunu yoxlamırdı | OUTLINE nümunələri rəqəmsiz; `plan_problems`: cavabdakı hər rəqəm modeldə + threshold deyilir; `number_audit.given_allowed`: "given" yalnız model/mənbə/il/sıra (≤12, vahidsiz)/vahid sabiti, əks halda fail-closed (`allowed_givens` meta.json + research.json). Test: `test_number_audit.py::test_given_number_outside_the_model_is_caught`, `test_script_story.py::test_answer_figures_must_come_from_the_model`, `test_script_story.py::test_outline_prompt_has_no_numeric_example_answers` |
| 77 | Faza 1.4: mənbənin ili yoxlanmırdı | — | `research.by_recency` (il ≥ cari − 3 üstün), axtarış promptunda "last 3 years"; köhnə mənbə abzasında il deyilməlidir (`citation_problems`); description-da il (`source_line`). Test: `test_research.py::test_recent_source_is_preferred_over_an_old_one`, `test_research.py::test_old_source_must_be_named_with_its_year`, `test_research.py::test_description_names_the_source_year` |
| 78 | Faza 1.5: tək case qaydalarının deterministik boşluqları — plan analogiyasında rəqəm, Recap-da misal ("for example") yoxlanmırdı | yalnız gpt-4o redaktoru baxırdı | `plan_problems`: analogiyada rəqəm → plan yenidən; `story_problems`: Recap-da misal sözləri. Mövcud: rəqəm ≤ 2 (`test_script_story.py::test_same_figure_three_times_in_one_section_is_a_repeat`), başqa biznes (`test_script_story.py::test_reviewer_flags_examples_from_other_businesses`). Test: `test_script_story.py::test_plan_analogy_with_a_number_is_rejected`, `test_script_story.py::test_recap_with_an_example_is_rejected` |
| 79 | Real skript probu (2026-10-07, raise-prices): model rəqəmləri hər bölmədə təkrarlandı → təkrar düzəlişi **qərar bölməsindən** rəqəmləri sildi → redaktor 3 raund "qərara cavab verilmir"; case biznesi rəqəmlə təsvir olundu ("20 seats"); bir bölmə bir raundda 8 dəfə ayrı-ayrı yenidən yazıldı; `number_audit` modelin düzgün "$7,500 → $8,100" cümləsini "giriş yoxdur" deyə sildi; "150 − 15 = 135" modeldə sayılmadı; `--temperature` review/repair-də iki dəfə ötürüldü (TypeError) | rəqəmlərin bölmələrə bölgüsü yox idi; `repeated_figures` son deyilişi saxlayırdı (qərar deyil); audit model nəticəsini tanımırdı | Hook başlanğıc dəyişənləri deyir (`hook_figures`), orta bölmələr rəqəmsiz, qərar bölməsi əvvəl/sonra + threshold; `repeated_figures` ilk deyiliş + qərar bölməsini saxlayır; biznes/case_step rəqəmsiz; düzəlişlər bölmə üzrə birləşir; `number_audit` `trusted` (model + mənbə) rəqəmini rolundan asılı olmayaraq keçirir; say dəyişənlərinin fərqi törəmədir; review/repair kwargs təmizlənir. Test: `test_script_story.py::test_repeat_fix_never_strips_the_decision_section`, `test_script_story.py::test_figures_are_allocated_to_sections`, `test_script_story.py::test_fixes_for_one_section_are_merged_into_one_rewrite`, `test_number_audit.py::test_model_result_passes_even_when_its_inputs_are_not_in_the_paragraph`, `test_case_model.py::test_difference_of_count_variables_is_a_derived_figure`, `test_script_story.py::test_model_review_and_repair_accept_the_cli_llm_kwargs` |
| 80 | Real probe: model təmiri üçün LLM-ə gedən rədd səbəbləri azərbaycanca idi ("threshold musbet deyil … dustur sehvdir", "namelum ad") → 15 cəhd eyni xəta; köhnə plan geri ötürüləndə mini eyni modeli təkrarladı; gpt-4o yoxlayıcı threshold-u `after`-ə qoydurdu (dövri) və `before_/after_` qaydasını bilmədən "undefined" dedi | LLM-ə gedən mesaj yalnız loq üçün yazılmışdı | `CaseModelError` mesajları ingiliscə; threshold adı blokda → aydın izah; model xətasından sonra təzə cəhd (köhnə plan ötürülmür); yoxlayıcıya ad qaydası + "threshold-u before/after-ə qoyma"; mənfi pul `-$50`. Probe: 5 mövzudan 4-ü ilk cəhddə. Test: `test_case_model.py::test_model_errors_reach_the_llm_in_english`, `test_script_story.py::test_after_a_model_failure_the_next_attempt_starts_fresh`, `test_case_model.py::test_threshold_name_inside_a_block_gets_a_clear_message`, `test_case_model.py::test_negative_money_is_formatted_with_the_sign_first` |
| 81 | Faza 2.1: qərar bölməsində data vizualı LLM-in seçiminə qalırdı | — | `decision_visuals.py`: `table` (əvvəl/sonra/fərq, yalnız deyilən xanalar) və `threshold` (break-even əyrisi — dəyişən dəyişdikcə nəticənin əvvəlki səviyyəni kəsdiyi nöqtə; tapılmasa həddi + bugünkü dəyər gauge) model_result-dan, LLM-siz; qərar bölməsinə məcburi (`plan_visuals(plan=)`); ssenari qərar bölməsində bir cümlədə əvvəl/sonra cütü + threshold deməlidir (`case_problems` + düzəliş). Remotion `DataViz.tsx` (Table, Threshold). Test: `test_decision_visuals.py::test_decision_visuals_are_forced_into_the_decision_section`, `test_decision_visuals.py::test_threshold_curve_when_a_variable_crosses_the_baseline`, `test_decision_visuals.py::test_script_decision_section_must_state_a_before_after_pair_and_the_threshold` |
| 82 | Faza 2.2–2.4: zaman və coğrafiya datası üçün vizual yox idi | — | `data_visuals.py`: `timeseries` (danışıqdan nöqtələr; < 4 nöqtə → xətti interpolasiya + ekranda "illustrative"; eniş seqmenti qırmızı; hadisə etiketi öz nöqtəsində) və `usmap` (reference ABŞ konturu, nöqtələr seed = slug sha256, sayğac `layout.MAP_COUNTER` bayquş/altyazı zonasından kənar); LLM promptunda; `layout.py` zonaları Remotion `AREA` ilə eyni. Test: `test_data_visuals.py::test_sparse_timeseries_is_interpolated_and_marked_illustrative`, `test_data_visuals.py::test_usmap_dots_are_seeded_by_the_slug`, `test_data_visuals.py::test_map_counter_and_box_avoid_owl_and_captions`, `test_data_visuals.py::test_python_layout_matches_the_remotion_area` |
| 83 | Faza 2.5: chart ilk saniyələrdə boş idi (yalnız başlıq); #53 yalnız ilk reveal-i 35%-ə sıxırdı | elementlər açılana qədər opacity 0 | skelet: hər element 0-cı kadrdan `GHOST` (0.28) kontur, rəqəm yerində "—", öz sözündə tam açılır; `FIRST_REVEAL_MAX` ləğv, `REVEAL_MIN` = 0; `chart_empty_share` (ilk 2 s, ≤ 3%). Test: `test_remotion_build.py::test_chart_scenes_render_a_skeleton_from_the_first_frame`, `test_remotion_build.py::test_first_reveal_is_not_clamped_any_more`, `test_visuals.py::test_first_element_never_waits_until_the_end_of_the_scene` |
| 84 | Faza 2.6: generik flow kartları ("Analyze Changes → Forecast Actions → Evaluate Options") | LLM ümumi fel + isim yazırdı | `case_context` + `step_ok`: flow/timeline addımı case sahibi/obyekti/model dəyişəni və ya rəqəm daşımalıdır; videoda flow ≤ 1 (`choose_animated`, `animate_abstract`); check_bgs/scene_plan planı ötürür. Test: `test_data_visuals.py::test_generic_flow_steps_are_rejected`, `test_data_visuals.py::test_at_most_one_flow_per_video`, `test_data_visuals.py::test_animate_abstract_obeys_the_card_rules` |
| 85 | Faza 2.7: foto səhnəsində deyilən pul/faiz rəqəmi ekranda görünmürdü | — | `remotion_build.number_overlay`: captions sözünün vaxtında count-up (≤ 2.5 s, səhnədə ≤ 1, yalnız foto səhnəsi), `layout.OVERLAY_BOX` bayquş/altyazı zonasından kənar; Remotion `NumberOverlay.tsx`. Test: `test_remotion_build.py::test_photo_scene_gets_a_count_up_overlay_at_the_spoken_figure`, `test_remotion_build.py::test_at_most_one_overlay_per_scene_and_never_on_chart_scenes`, `test_remotion_build.py::test_overlay_box_avoids_the_owl_and_the_captions` |
| 86 | Faza 3.1–3.6 (istifadəçi 2026-10-07): hər videoda eyni animasiya/keçid (slide/fade), xətti easing, 4 Ken Burns hərəkəti, bir fon | motion seçimi yox idi; Remotion sabit dəyərlərlə işləyirdi | `motion.py`: seed = slug sha256 → epizoda bir theme (clean/dynamic/editorial), hər növə ≥3 giriş variantı (typewriter daxil; cold open həmişə typewriter, müddət dəyişmir), bölmə/adi keçid dəstləri (ardıcıl təkrar yox), 9 Ken Burns hərəkəti (sabit sürət), 4 backdrop; `_motion_history.json` son 3 epizodla oxşarlıq > 50% → theme dəyişir. Remotion: `motion.ts` tokenləri (300–600/200–400/60–120 ms, spring presetləri, bezier), `Episode.tsx` planı oynadır (`TRANSITION_PRESETS` → quraşdırılmış @remotion/transitions 4.0.529: fade/wipe/slide/pushCut/iris/flip/clockWipe, `springTiming`), `VariantCtx`/`TitleVariantCtx`, editorial-da `FilmLook` (rəng, vinyet, dənə); seçim Python-dadır (test + tarixçə üçün), Remotion `random()` yox. Test: `test_motion.py::test_same_seed_same_plan_different_seed_different_plan`, `test_motion.py::test_no_transition_repeats_back_to_back_and_sets_are_separate`, `test_motion.py::test_history_similarity_above_half_changes_the_theme`, `test_motion_lint.py::test_no_linear_interpolation_in_charts_cards_and_overlays`, `test_motion_lint.py::test_owl_components_are_unchanged_and_still`, `test_remotion_wiring.py::test_every_planned_transition_has_a_remotion_presentation`, `test_remotion_wiring.py::test_every_ken_burns_motion_is_implemented`, `test_remotion_wiring.py::test_episode_plays_the_motion_plan` |
| 87 | Faza 3.7–3.9: rəqəm səslənəndə vurğu yox idi; SFX qatı yox idi; altyazıda rəqəm yalnız aktiv olanda sarı idi | — | `motion.emphasis` (≤ 400 ms, saniyədə ≤ 3, 20 s-də ≤ 1 böyük) → `Effects.tsx EmphasisLayer` (kənar parıltısı, bayquşu örtmür); `sfx.py` (whoosh/pop/tick/boom lavfi, `Projects/sfx/` istifadəçi faylı üstün, 10 s-də ≤ 2, nitqdən ≥ 18 dB aşağı, söz ortasına düşmür) `audio_master`-də loudnorm-dan ƏVVƏL qarışır; `compact_words` rəqəm sözlərini `num` ilə işarələyir, `Captions.tsx` onları accent rəngdə saxlayır. Test: `test_motion.py::test_emphasis_pulses_are_short_and_never_flash_more_than_three_per_second`, `test_motion.py::test_big_effects_are_at_most_one_per_twenty_seconds`, `test_sfx.py::test_density_is_at_most_two_per_ten_seconds`, `test_sfx.py::test_sfx_never_lands_in_the_middle_of_a_word`, `test_sfx.py::test_master_mixes_sfx_before_loudnorm_to_minus_14`, `test_remotion_wiring.py::test_caption_words_mark_spoken_figures`, `test_remotion_wiring.py::test_captions_keep_figures_in_accent_colour` |
| 88 | Faza 3 renderStill probu (2026-10-08): table səhnəsində bayquş "CHANGE" sütununu (`+$110`) örtdü | bayquşun eni (`height × aspect`) məhdudlaşdırılmırdı; lövhə/əşya tutan geniş bayquş (aspect > 1) x≈1180-dən başlayır, chart AREA isə x 1310-a qədərdir | `remotion_build.fit_chart_owls`: chart səhnəsində bayquş sol kənarı AREA + 20 px-dən sağda qalana qədər kiçildilir (ayrıca `<poz>~chart` açarı, eyni şəkil; Owl.tsx dəyişmir, foto səhnəsi toxunulmur); `layout.OWL_MARGIN_X` theme.ts ilə eyni. Test: `test_remotion_build.py::test_wide_owl_on_a_chart_scene_stays_right_of_the_chart_area`, `test_remotion_build.py::test_narrow_owl_on_a_chart_scene_keeps_its_size`, `test_remotion_build.py::test_layout_owl_margin_matches_remotion_theme` |
| 89 | Faza 4 (istifadəçi 2026-10-07, RPM): mid-roll nöqtələri, lead magnet/affiliate bloku və yükləmə checklist-i yox idi | — | `publish_pack.midrolls`: bölmə keçidindən 1 s əvvəl, ilk 60 s-də yox, aralarında ≥ 2 dəq, 3–4 nöqtə (çox namizəddə video boyu bərabər) → `youtube/midrolls.txt`; `config.py` (`LEAD_MAGNET_URL`, `AFFILIATE_LINKS` `.env`-dən) → `monetization_block` (boşdursa yazılmır, affiliate açıqlaması FTC); `youtube/upload_checklist.txt` (Not made for kids, bütün reklam formatları, mid-roll əllə, 3 başlıq + thumbnail A/B, ABŞ vaxtı ET); `pack_problems` hər ikisini və 3–4 mid-roll-u tələb edir; `deliver` onları `Hazir_Videolar\<slug>\`-ə köçürür (fail-closed). Test: `test_publish_pack.py::test_midrolls_skip_the_first_minute_and_stay_two_minutes_apart`, `test_publish_pack.py::test_midrolls_sit_one_second_before_a_section_change`, `test_publish_pack.py::test_description_adds_lead_magnet_and_affiliate_blocks_from_config`, `test_publish_pack.py::test_empty_config_writes_no_monetization_block`, `test_publish_pack.py::test_upload_checklist_has_every_required_step`, `test_publish_pack.py::test_pack_problems_require_midrolls_and_checklist`, `test_pipeline.py::test_deliver_fails_without_the_rpm_files` |
| 90 | Faza 5.1–5.7 (istifadəçi 2026-10-07): imkanlar video başına açıla/unudula bilərdi; hesabatlar ayrı-ayrı mərhələlərdə yoxlanırdı, skript dəyişəndə köhnə hesabat keçə bilərdi; reyestr sətirlərinin 65-i testə bağlı deyildi; xəta sinifləri kataloqu yox idi | vahid qapı və bayraq mərkəzi yox idi; yalnız script_qa/math_check sha daşıyırdı | `config.py` bayraqları (CASE_MODEL, SFX, NUMBER_OVERLAY, TYPEWRITER, MOTION_VARIANTS = True; REQUIRED_KINDS) kodda istifadə olunur; `qa_stamp` — captions/bg/owl/motion/sfx hesabatları skriptin sha256-sı ilə; `quality_gate.py` pipeline-ın son mərhələsi (13 yoxlama + SFX > 0, overlay ≥ 80%, qərarda table+threshold, typewriter, oxşarlıq ≤ 50%; fail-closed) → `qa/quality_gate.json` + `qa/self_audit.md`; deliver yalnız qapı keçəndə; `docs/error_classes.md` koddan (`ERROR_CLASSES`) yaradılır; reyestrin 89 sətri testə bağlandı (#4 bugünkü ekvivalentlə). Test: `test_defaults.py::test_every_feature_flag_is_on_by_default`, `test_defaults.py::test_number_overlay_flag_drives_the_build`, `test_quality_gate.py::test_missing_report_fails_closed`, `test_quality_gate.py::test_report_from_an_older_script_is_stale`, `test_quality_gate.py::test_photo_figures_need_overlays`, `test_quality_gate.py::test_decision_topic_needs_table_and_threshold`, `test_quality_gate.py::test_quality_gate_is_the_last_pipeline_stage`, `test_quality_gate.py::test_error_class_catalog_doc_is_generated_from_the_code`, `test_registry.py::test_every_registry_row_references_a_test`, `test_registry.py::test_every_reference_points_to_an_existing_test` |
| 91 | Faza 5.5 xəta sinfi "real şəxs haqqında mənbəsiz hüquqi iddia" heç bir qapıda yox idi | — | `script_qa.legal_claim_problems` (story_problems-də): hüquqi ittiham sözü (sued, fined, fraud, convicted…) olan cümlədə case sahibi/biznesi/yeri və dövlət qurumundan (IRS, SBA…) başqa xüsusi ad → problem. Test: `test_script_story.py::test_unsourced_legal_claim_about_a_real_company_is_caught`, `test_script_story.py::test_story_checks_include_legal_claims` |
| 92 | E2E (2026-10-08, hire-first-employee): `script_gen` "menbe kohnedir (2022) - il deyilmelidir" ilə dayandı | köhnə mənbə problemi "mənbə yoxdur" düzəliş şablonunu alırdı (`According to {cite_as}, {claim}` — il yox), LLM yenə ilsiz yazırdı | `story_fixes`: "menbe kohnedir" üçün ayrıca təlimat — sitat cümləsində ili açıq de ("in 2022"), rəqəm və mənbə adı dəyişmir. Test: `test_research.py::test_old_source_fix_tells_the_writer_to_say_the_year` |
| 93 | E2E (2026-10-08, hire-first-employee, retry 2): #92-dən sonra `script_gen` "menbe tehrif olunub" ilə dayandı (gpt-4o redaktor 3 raund) | #92 skriptdə ili tələb edir, redaktorun `VERIFIED FACT`-ində il yox idi → "in 2022" mənbəyə əlavə iddia sayıldı (ili çıxaranda/fakta əlavə edəndə `source_faithful: true` — real probe). İki yoxlama bir-birinə zidd idi | `_review_user`: fakt sətrində "{cite_as}, {year} report"; #92 təlimatı da "{cite_as}'s {year} report" (il nəşr ilidir, data ili yox). Test: `test_script_story.py::test_reviewer_sees_the_source_year` |
| 94 | E2E (2026-10-08, hire-first-employee): `script_gen` "$450 - deyisen buraxilib", "evvel/sonra cutu deyilmir" ilə dayandı | model zərər verir (həftəlik −$150 → −$450); skript düzgün olaraq "a loss of $450" deyir, amma `allowed_numbers` və cüt yoxlaması yalnız işarəli dəyəri tanıyırdı → 450 təsadüfən "dəyişən buraxılmış" naive nəticə ilə üst-üstə düşdü | `allowed_numbers`: mənfi before/after dəyərlərinin modulu da icazəlidir; `_decision_section_problems`: cüt modulla müqayisə olunur. Test: `test_case_model.py::test_a_loss_said_without_its_sign_is_a_model_value`, `test_case_model.py::test_loss_pair_without_signs_counts_as_the_before_after_pair` |
| 95 | E2E (2026-10-08, hire-first-employee): skript qərar həddini (40 müştəri) heç demədi, deterministik qapı keçdi, gpt-4o "qərar cavablanmır" ilə dayandı | `_decision_section_problems` həddi ×100 formada da axtarırdı (faiz üçün) — "$4,000" = 40×100 "hədd deyilib" sayıldı, yazıçıya düzəliş getmədi | ×100 yalnız %/share və ya |raw| < 1 hədd üçün. Test: `test_case_model.py::test_count_threshold_is_not_matched_by_a_hundredfold_money_figure` |
| 96 | E2E (2026-10-08, hire-first-employee): case modeli `weekly_profit = weekly_sales` (xərcsiz mənfəət) gpt-4o hakimdən keçdi → skript "profit $3,200 after expenses", redaktor "ziddiyyət" | modeldə mənfəətin xərc çıxmasını yoxlayan deterministik qayda yox idi | `evaluate`: adında "profit" olan nəticə çıxma (−) və ya başqa profit-ə istinad etmirsə `CaseModelError` (LLM-ə ingiliscə: "subtract the costs"). Test: `test_case_model.py::test_profit_must_subtract_costs` |
| 97 | E2E (2026-10-08, hire-first-employee): 4 cəhddə qərar bölməsində rəqəm 3 dəfə (150, $1,750, $800) — "tekrarlanir" düzəlişi 2 raundda keçmədi | qərar bölməsi həddi deməlidir (hədd = əvvəl deyilmiş rəqəm), təlimat isə "do not restate" deyirdi (+ 'the current price' nümunəsi hərfən köçürüldü) → yazıcı hər iki deyilişi saxladı | problem mətni bölmənin kvotasını daşıyır ("bu bolmede N qalir"); N=1 → "Say $800 exactly once in this section (in the decision rule)", nümunə neytral ('that amount'). Test: `test_script_story.py::test_repeat_fix_says_how_many_mentions_the_section_keeps` |
| 98 | E2E (2026-10-08, hire-first-employee): redaktor "hekayə ziddiyyətlidir" — Sarah 80 müştəri ilə "həddi (60) keçib", amma işə götürəndə zərər artır | case modelinin həddi müştəri sayı ilə ölçülürdü, delta isə müştəri sayından asılı deyildi (işçinin xərci sabit) — hədd qərarla bağlı deyil; gpt-4o hakimi buraxdı | `case_model.threshold_link_problem`: həddin mənasındakı say dəyişəni (+10%) dəyişəndə delta dəyişmirsə plan rədd (LLM-ə ingiliscə: "model in 'after' what changes with …"); `plan_problems`-də çağırılır. Test: `test_case_model.py::test_threshold_counted_in_a_variable_must_move_the_decision`, `test_script_story.py::test_plan_rejects_a_threshold_unlinked_to_the_decision`, `test_case_model.py::test_threshold_link_accepts_any_variable_of_the_same_noun`, `test_case_model.py::test_plan_prompt_says_what_an_added_cost_brings` (real probe: eyni isimli bir neçə dəyişən — biri deltanı tərpədirsə kifayət; plan təlimatı: "profit = revenue minus costs", xərc əlavə edən qərarda after onun gətirdiyini də modelləyir) |
| 99 | E2E (2026-10-08, hire-first-employee): #96-dan sonra LLM `weekly_profit = weekly_revenue - 0` yazdı — qayda yalnız "-" simvoluna baxırdı | mətn yoxlaması aldadıla bilirdi | `_subtracts_a_cost` (AST): ya başqa profit-ə istinad, ya da çıxılan tərəfdə DƏYİŞƏN olmalıdır. Test: `test_case_model.py::test_profit_minus_zero_is_still_without_costs` |
| 100 | E2E (2026-10-08): "$20 per customer" (= weekly_revenue / weekly_customers, modelin öz düsturunda) "case modelində yoxdur" sayıldı | `allowed_numbers` düsturların ara ifadələrini bilmirdi | `evaluate` → `result["intermediates"]`: before/after/threshold düsturlarının yalnız giriş dəyişənlərindən ibarət hər alt-ifadəsi; `allowed_numbers` onları qəbul edir. Test: `test_case_model.py::test_intermediate_of_a_model_formula_is_an_allowed_figure` |
| 101 | E2E (2026-10-08): "Say $3,000 exactly once in this section" 2 raundda icra olunmadı (gpt-4o-mini) — qərar bölməsində 2 deyiliş qaldı | ümumi təlimat hansı cümlənin dəyişəcəyini demirdi | repeat düzəlişi rəqəmin çıxarılacağı cümlələri SİTAT gətirir, saxlanacaq (qərar qaydası, son deyiliş) cümləni ayrıca göstərir. Test: `test_script_story.py::test_repeat_fix_quotes_the_sentence_to_change` |
| 102 | E2E (2026-10-08, hire-first-employee): gpt-4o-mini 10+ cəhddə məntiqli case modeli qura bilmədi (xərcsiz mənfəət, qərarla bağlı olmayan hədd, `x − 0`, təlimata əməl etməmək); gpt-4o hakimi də buraxırdı | yazan modelin mühakimə zəifliyi | **İstifadəçi qərarı:** şəkil xaric bütün LLM-lər Gemini — `llm.PROVIDERS["gemini"]` (OpenAI-uyğun endpoint), rol xəritəsi `GEMINI_ROLES` (yazan 3.8 Flash, yoxlayan 3.1 Pro), `THINK_ROOM` (düşünmə tokenləri JSON-u kəsməsin), xərc gizli düşünmə tokenləri ilə, `default_provider` (`LLM_PROVIDER`), pipeline default + bayquş hakimi Pro. Real probe: JSON + vision işləyir. Test: `test_llm.py::test_gemini_maps_the_writer_and_checker_roles`, `test_llm.py::test_gemini_gets_room_for_thinking_tokens`, `test_llm.py::test_gemini_cost_counts_hidden_thinking_tokens`, `test_llm.py::test_default_provider_is_openai_unless_env_says_otherwise`, `test_pipeline.py::test_pipeline_default_provider_follows_llm_default`, `test_render_owls.py::test_owl_judge_uses_the_checker_model_on_gemini` |
| 103 | E2E (2026-10-08, hire-first-employee, ilk Gemini cəhdi): case modeli ilk dəfə məntiqli, amma Gemini Pro redaktor "ziddiyyət" + "təkrar" dedi | redaktor promptu bizim qaydalarla zidd idi: Cold Open tizerindəki rəqəmi "təqdim olunmamış" saydı, qərar bölməsindəki 2-ci deyilişi "təkrar" saydı (qayda: rəqəm ≤ 2); Flash model etiketlərini hərfən köçürdü ("monthly revenue before of $12,000"); insight qrammatikası "costs rises" | `REVIEW_SYSTEM`: Cold Open tizerdir (ziddiyyət deyil), 2-ci deyiliş təkrar deyil; qərar təlimatı: etiketləri/before-after sözlərini köçürmə; `case_model._verb` cəm isimlə razılaşma. Test: `test_script_story.py::test_reviewer_rules_match_the_cold_open_and_two_mentions_rules`, `test_script_story.py::test_decision_guidance_forbids_copying_model_labels`, `test_case_model.py::test_insight_verb_agrees_with_a_plural_label` |
| 104 | E2E (2026-10-08, Gemini 2-ci cəhd): bölmələr cümlənin ortasında kəsildi ("which begins the moment you"), redaktor "ends abruptly"; bölmə 60 s, $0.036 | Gemini Flash nəsr yazanda ~8000 token düşünürdü → `out` = max_tokens + THINK_ROOM limitinə çatdı, mətn kəsildi; `chat()` `finish_reason`-a baxmırdı (real probe: out=9384 = limit) | `finish_reason == "length"` → `LLMError` (kəsik mətn səssiz keçmir); Gemini-də JSON olmayan (nəsr) sorğu `reasoning_effort: low`, JSON (plan/hakim) tam düşünür. Probe: bölmə 7 s, $0.003, tam cümlə. Test: `test_llm.py::test_a_truncated_answer_is_an_error_not_silent_text`, `test_llm.py::test_gemini_prose_thinks_little_json_thinks_fully` |
| 105 | E2E (2026-10-08, hire-first-employee): 14 uğursuz cəhdin 7-si eyni xəta — "qərar bölməsində rəqəm 3 dəfə" (150, $1,750, $800, $3,000, $6,000, $500…) | qərar bölməsi əvvəl/sonra cütü + həddi MÜTLƏQ deyir, həmin rəqəmlər Hook-da artıq var; düzəlişi LLM edirdi, gpt-4o-mini sitatlı təlimata da əməl etmirdi → dövr sabitləşmirdi (arxitektura xətası) | `script_qa.settle_repeats`: LLM raundlarından sonra artıq deyiliş DETERMİNİSTİK düzəlir — yeni rəqəmsiz cümlə silinir, qalanında rəqəm "that amount"; son deyilişlər (qərar qaydası) qalır; `script_gen.quality_gate` rəqəm auditindən ƏVVƏL çağırır (audit sha möhürü pozulmasın). Test: `test_script_story.py::test_settle_repeats_drops_a_pure_restatement_and_keeps_the_decision_sentence`, `test_script_story.py::test_settle_repeats_replaces_the_number_when_the_sentence_has_new_facts`, `test_script_story.py::test_quality_gate_settles_repeats_the_llm_left` |
| 106 | E2E (2026-10-08): gpt-4o-mini xərc əlavə edən qərarda ("hire") case modelini 5 cəhddə gpt-4o hakimindən keçirə bilmədi ("plan qaydalara uygun gelmedi") | mini-yə işləyən model strukturu göstərilmirdi | `MODEL_EXAMPLE` (iş sayı, qiymət, material, sabit xərc, əlavə iş, işçi xərci; hədd = işçi xərci / iş marjası) — plan və model təmiri promptlarına "structure only" nümunə kimi; nümunənin özü bütün deterministik qaydalardan keçir. İstifadəçi qərarı: Gemini-dən imtina, default yenə OpenAI. Test: `test_case_model.py::test_model_example_for_added_cost_decisions_passes_every_rule`, `test_script_story.py::test_plan_and_repair_prompts_carry_the_model_example` |
| 107 | E2E (2026-10-09, GPT, #105/#106-dan sonra): redaktor + audit keçdi, yalnız "əvvəl/sonra cütü eyni cümlədə deyil" qaldı ($2,500 və $500 ayrı cümlələrdə) — 2 cəhd ardıcıl | cüt cümləsi LLM-ə buraxılırdı; rəqəm auditi abzası yenidən yaza bilir | `script_qa.settle_decision_pair`: cüt yoxdursa modeldən "<owner>'s <profit> goes from X to Y." sonra-dəyərli cümlədən sonra əlavə olunur; `quality_gate` auditdən sonra yenidən yoxlayır, dəyişərsə audit təkrar (sha). Test: `test_script_story.py::test_settle_decision_pair_states_before_and_after_in_one_sentence`, `test_script_story.py::test_quality_gate_reaudits_when_the_number_audit_splits_the_pair` |
| 108 | E2E real probe (2026-10-09): `settle_repeats` say-rəqəmi "that amount" ilə əvəz edirdi → "those that amount extra clients", "$800 divided by $200 equals that amount" | əvəzləmə vahidi nəzərə almırdı | `_refer_back`: təyinedicidən sonra say silinir ("those extra tables"), pul/% → "that amount", say → "that many". Test: `test_script_story.py::test_settle_repeats_keeps_count_sentences_grammatical` |
| 109 | İstifadəçi 2026-10-09: "qəti şəkildə həll et" — 21 cəhdin son problemlərinin hamısı deterministik siniflərdir (modeldə olmayan rəqəm, dəyişən buraxılıb, cüt, eşik, təkrar, köhnə mənbə ili) | hər sinif LLM düzəlişinə buraxılırdı (arxitektura xətası, #105-in ümumiləşməsi) | `script_qa.settle_script` (sabit nöqtəyə qədər): il əlavə, modeldən kənar rəqəmli cümlə silinir, cüt/eşik modeldən yazılır, təkrar həll olunur; `quality_gate` auditdən əvvəl və sonra çağırır. Test: `test_script_story.py::test_settle_script_clears_every_deterministic_case_problem`, `test_script_story.py::test_settle_script_says_the_year_of_an_old_source` |
| 110 | E2E (2026-10-09, hire-first-employee): `check_bgs` 13 təsdiqlənmiş təkrar cütlə + generik 11% ilə dayandı | (a) tək case biznesində bütöv "yer" kadrları ("bakery kitchen with ovens" / "A photo of a bakery kitchen" / "cozy bakery") hero-da fərqli sayılırdı ("kitchen"/"photo"/"bakery"), CLIP+hakim isə eyni yer dedi; (b) təkrar kadr birbaşa `FALLBACK_POOL`-a (generik metafor) gedirdi → 16-sı "mismatch/generic", generik payı qalxdı, raund büdcəsi bitdi | `scene_plan.hero`: "photo/interior … of X" → X, bütöv yer → `PLACE` (epizodda 1 dəfə); `check_bgs.duplicate_prompt`: təkrar üçün case biznesinin yeni obyekti istənir, hovuz yalnız son çarə. Test: `test_no_repeats.py::test_place_shots_of_the_case_business_share_one_hero`, `test_no_repeats.py::test_photo_of_prefix_is_not_the_hero`, `test_no_repeats.py::test_duplicate_redraw_asks_for_a_new_case_object_not_the_generic_pool`, `test_no_repeats.py::test_duplicate_redraw_falls_back_to_the_pool_only_without_a_fresh_suggestion` |
| 111 | E2E (2026-10-09, hire-first-employee, #110-dan sonra): `check_bgs` 1-ci cəhddə 6 təkrar cüt qaldı (17/56 eyni oxlov) | `hero()` "-ing" sözündə kəsirdi: "A wooden rolling pin" → hero "wooden", oxlov kadrı təzəlik yoxlamasından keçirdi | `scene_plan._ING_NOUNS`: mürəkkəb isim təyinləri ("rolling pin", "baking sheet") kəsilmir. Test: `test_no_repeats.py::test_ing_compound_noun_keeps_its_head` |
| — | Müşahidə (2026-10-06): `test_pipeline.py::test_run_pipeline_from_forces_rerun` tam suite-də 1 dəfə düşdü, sonra 7 dəfə keçdi | kök səbəb TAPILMADI (ehtimal: Windows-da `state.json` fayl kilidi — təsdiqlənməyib) | açıq; təkrar düşsə çıxışı saxla və araşdır |
| 48 | İstifadəçi: yenə "eyni/təkrar şəkillər" | (#46-dan əlavə) CLIP namizəd pəncərəsi dar ola bilərdi — ölçülməyib | `DUP_SIM` 0.85 → 0.80 (hakim təsdiqi qalır); foto sayı ~60% azaldığı üçün təkrar ehtimalı da azalır. Test: `test_no_repeats.py::test_clip_candidate_threshold_is_wide_enough_for_same_kind_objects` |

**Açıq qalan:** yoxdur.

---

## Keyfiyyət + imkan yeniləməsi (istifadəçi 2026-10-07, 6 faza) — İCRADADIR
Tapşırıq mətni: istifadəçinin 2026-10-07 mesajı ("ELI5 BUSINESS PIPELINE — KEYFİYYƏT VƏ İMKAN YENİLƏMƏSİ").
Reference (yalnız ideya, icra olunmur): `docs/reference/video_yarat_v4.py`.
| Faza | Vəziyyət |
|---|---|
| 1 Məzmun dəqiqliyi (case model, cold open=insight, uydurma rəqəm, mənbə ili, tək case) | TAMAM (#73–#80); real skript probu son run-da 2 problem qaldı (düzəldildi #79/model 1-ci qat), təkrar prob lazımdır |
| 2 Data vizualları (table, threshold, timeseries, usmap, skelet chart, generik kart, overlay) | TAMAM (#81–#85), renderStill ilə vizual yoxlandı |
| 3 Motion + səs | TAMAM (2026-10-08, #86–#88): Episode.tsx planı oynadır (keçidlər, variantlar, backdrop, vurğu, editorial film), 9 Ken Burns, altyazıda rəqəm rəngi, geniş bayquş chart-ı örtmür; renderStill probu (editorial + dynamic) ilə vizual yoxlandı. 611 test, `tsc` təmiz |
| 4 Publish (midrolls, lead magnet/affiliate, upload checklist) | TAMAM (2026-10-08, #89). Linklər `.env`-də `LEAD_MAGNET_URL` / `AFFILIATE_LINKS` (hələ boş — istifadəçi doldurmalıdır) |
| 5 Default ON, quality_gate, reyestr↔test, error_classes.md, CLAUDE.md, self_audit | TAMAM (2026-10-08, #90–#91) |
| 6 Yekun: testlər + 2 E2E (qiymət qərarı; zaman/coğrafiya) | İCRADADIR — E2E №1 4/13-də dayandırıldı (2026-10-09), №2 başlamayıb |

## Növbəti dəqiq addım

**2026-10-09 16:32:** E2E №1 WMI ilə `--resume` edildi (PID 7404), `[4/13] check_bgs`-dən davam edir; log
`Episodes\_run_should-you-hire-your-first-employee.log`. `Projects/CLAUDE.md` (kod arxitekturası) yaradıldı, `f0ab716`.

**2026-10-09 ~00:25 (İSTİFADƏÇİ "SAXLA" DEDİ — BURADAN DAVAM):** Faza 1–5 TAMAM, **Faza 6 icradadır**.
- **Modellər (son qərar 2026-10-08 gec):** Gemini-dən İMTİNA — şəkil gpt-image-2, yazan gpt-4o-mini, yoxlayan gpt-4o
  (default `openai`). Gemini kodu qalır, yalnız `.env` `LLM_PROVIDER=gemini` ilə (istifadəçi istəmədən açma).
- **Ssenari problemi HƏLL OLUNDU:** 21 cəhdin son xətaları deterministik siniflər idi, LLM-ə buraxılırdı → #105–#109
  (`script_qa.settle_script`: modeldən kənar rəqəmli cümlə silinir, əvvəl/sonra cütü + eşik modeldən yazılır, təkrar
  həll olunur, köhnə mənbəyə il; `quality_gate` auditdən əvvəl+sonra). Retry #107/#108 kodu ilə `script_gen` KEÇDİ
  (2026-10-09 00:08, "ssenari keyfiyyeti: OK"). #109 hələ real run-da sınanmayıb. 692 test keçir, son commit `958dacb`.
- **E2E №1** `should-you-hire-your-first-employee`: 1–3 mərhələ TAMAM (script_gen, scene_plan, render_bgs), istifadəçi
  `[4/13] check_bgs` zamanı DAYANDIRDI (proseslər öldürüldü). Davam: WMI ilə
  `run.py --resume should-you-hire-your-first-employee --provider openai` (CLAUDE.md addım 2; log `Episodes\_run_<slug>.log`),
  Monitor: `[N/13]` + Traceback/XETA/ugursuz. Qalan ~80 dəq (bgs yoxlaması, owl, TTS, render, quality_gate).
- Açıq keyfiyyət müşahidəsi: keçən skriptdə LLM rəqəmləri "a specific amount"/"that same amount" ilə bulandırıb
  (yoxlamalardan keçir, amma zəif) — #112 namizədi: qərar bölməsində qeyri-müəyyən məbləğ ifadəsi qadağası.
1. E2E №1 bitəndən sonra CLAUDE.md addım 4 yoxlamaları (quality_gate.json passed, self_audit.md, 10–12 dəq, −14 LUFS,
   kadrlar, owl, thumbnail, paket: mp4/thumbnail/youtube.txt/srt/script/midrolls/upload_checklist).
2. E2E №2: "Should You Open a Second Location?" (timeseries/usmap) — motion_sheet №1-dən fərqli olmalıdır.
   İstifadəçi 2026-10-09: niyə 2 video olduğu izah edildi → "qalsın" (2 E2E qalır, birə endirilmir).
3. Xətaları qeyd et, "Cari vəziyyət" = HAZIR, commit, istifadəçiyə qısa hesabat (faza üzrə, reyestr #86–#109+, iki E2E,
   açıq qalanlar: `.env` LEAD_MAGNET_URL/AFFILIATE_LINKS boş; Gemini açarı çatda göründü → rotasiya tövsiyəsi).
   Hər video üçün AskUserQuestion: "Video təsdiqlənsin və pipeline-dakı yaddaşı silinsin?"

**2026-10-08:** Faza 3, 4, 5 TAMAM. Növbəti: **Faza 6** — 2 yeni B2B mövzu ilə ardıcıl E2E (CLAUDE.md tetiki): (1) qiymət/xərc qərarı (table + threshold), (2) zaman/coğrafiya datası (timeseries/usmap); hər birində quality_gate keçir, self_audit təmiz, motion_sheet-lər fərqli, 10–12 dəq, −14 LUFS, təhvil paketi tam (mp4, thumbnail, youtube.txt, srt, script, midrolls, upload_checklist). Pullu (OpenAI) — istifadəçi təsdiqi lazımdır. `Episodes\_probe-raise-prices` probe qovluğudur (silinə bilər).

**Vəziyyət (2026-10-07):** açıq iş yoxdur. 12 addımlıq standart E2E-də işlədi (#54–#70), 471 test keçir.
Açıq müşahidələr: abstrakt mövzuda animasiya payı ~84%-ə qalxa bilər ("~60%"-dən yuxarı, generik foto → animasiya);
flaky `test_run_pipeline_from_forces_rerun` (reyestr "—" sətri).
**Növbəti dəqiq addım:** istifadəçinin yeni mövzusu `Video: <Mövzu>` — #71/#72-nin ilk E2E yoxlaması (generik pay + animasiya ≤70%, skriptdə başqa biznes yox, rəqəm ≤ 2 dəfə).
**Əvvəlki (2026-10-05):** açıq iş yox idi. 347 test keçirdi (#50–#53 əlavə).
**Əvvəlki (2026-10-04):** 334 test keçirdi (#45 analitik animasiyalar ~57–60%, #46 kart təkrarı, #47 thumbnail, #48 dedupe, #49 chart mətn/vahid).

**2026-09-30:** ilk tam E2E yeni kodla (#29–#33) KEÇDİ — 53 səhnə, hovuza 0, `duplicates: []`, owl 53/53, 8.85 dəq, ~77 dəq run, xətasız. Açıq yoxlama bağlandı. Video təsdiqləndi, epizod yaddaşı silindi.

### FAZA I — səhnə bayquşu + AI musiqi (2026-09-27) — TAMAM
İstifadəçi tələbi: (1) musiqi **lisenziyasız/istinadsız və ödənişsiz**; (2) bayquş hər səhnədə mətnə uyğun
detallı görünüşdə (ChatGPT), **əsl görünüşü dəyişməsin**. Spec: `docs/superpowers/specs/2026-09-27-scene-owl-and-ai-music-design.md`.
Qərarlar: musiqi = AI (Stable Audio Open, lokal GPU); bayquş = ayrıca şəffaf şəkil, fonun üstündə sağda.

**Hazır (commit `7cd5d6f`, `8579539`, 145 test):**
- `scene_plan`: hər səhnəyə `owl_action` (insan/yazı filtri, bayquşun "hands"-i icazəlidir)
- `llm.edit_image` (multipart `/images/edits`), `render_owls.py` mərhələsi (check_bgs-dən sonra):
  referans `Character/ELI5_Owl/sprites_hd/front.png` → `gpt-image-2` low, `background=transparent`, 1024x1536,
  alpha kəsimi → `owl/scNN.png`; gpt-4o hakimi referansla müqayisə; 3 cəhd → köhnə poz; `owl_qa.json`
- `remotion_build`: `owl/scNN.png` varsa poz `scNN` (flippable=False); `Owl.tsx` dəyişmədi
- `music_gen.py` + `music_gen` mərhələsi (build_episode-dan əvvəl, `MusicGen\.venv`): 6 üslub × 45 s, crossfade
  → `Episodes\<slug>\music.wav`; `ctx.music` default = bu fayl; `--music` versə atlanır; CC BY trek seçimi silindi
- skript dəyişəndə `owl/`, `bg_qa.json`, `owl_qa.json` də silinir (əvvəl `bg_qa.json` qalırdı — köhnə boşluq)
- Proba (ölçülüb): gpt-image-2 edits bayquşu eyni saxladı (eynək/kostyum/qalstuk), RGBA, ~25 s/şəkil

**Mühit:** `MusicGen\.venv` (uv, py3.12, torch 2.x cu128, diffusers). HF gated model qəbul edildi
(hesab MNurlan1993, org "Eli5 Youtube", istifadəçi təsdiqi ilə). Lisenziya: Stability Community (<$1M pulsuz,
çıxış istinadsız). **Stability Community License AKTİVDİR** (2026-09-28, Nurlan Mirkishiyev / "Eli5 Business", umman65@gmail.com, submission `169a89b8-4c5f-43a5-8f27-9a6b2eef5bd1`) — AI musiqi kommersiya istifadəsi üçün qanunidir.

**2026-09-27 axşam: addım 1–2 TAMAM (commit `58b0db5`, 147 test).** Model tam yükləndi (transformer 4.0 GB).
Proba: yükləmə 6 s, 45 s-lik klip ~30 s, VRAM 5.9 GB (8 GB-a sığır, offload lazım deyil). Tapılıb düzəldilən:
repo id ilə `from_pretrained` kökdəki 4.8 GB `model.safetensors`-u yükləməyə başlayırdı → `model_dir()`;
kliplər 0.8–2.4 s sükutla bitirdi → kəsilir; kliplər 7 dB fərqli idi → hər biri −18 LUFS. İndi: addım 3 (E2E).

**Növbəti addımlar (ardıcıl):**
1. ~~Model yükləməsini yoxla/tamamla~~ TAMAM (sessiya bitəndə yarımçıq qala bilər). Xet ilişir → **`HF_HUB_DISABLE_XET=1`**,
   yalnız alt qovluqlar (kökdəki 4.8 GB `model.safetensors`/`model.ckpt` LAZIM DEYİL):
   `HF_HUB_DISABLE_XET=1 MusicGen\.venv\Scripts\python -c "from huggingface_hub import snapshot_download; snapshot_download('stabilityai/stable-audio-open-1.0', allow_patterns=['model_index.json','projection_model/*','scheduler/*','text_encoder/*','tokenizer/*','transformer/*','vae/*'])"`
   (əvvəl `blobs/*.incomplete` sil). Tam ölçü ~5.3 GB (transformer 4.2 GB).
2. Musiqi probu: scratchpad-dakı `probe_music.py` kimi 2 klip → vaxt/VRAM ölç, dinləmə yoxdur → spektr/səs
   səviyyəsi + ffprobe ilə yoxla; 8 GB VRAM-a sığmazsa `enable_model_cpu_offload()`.
3. ~~E2E~~ TAMAM — `what-is-profit-margin` (jurnala bax). Dövr nöqtəsində sükut tapıldı → reyestr #26.
4. ~~progress.md, yaddaş, commit~~ TAMAM.

**FAZA F dizaynı TƏSDİQLƏNDİ (2026-09-23):** Faza 1 / Faza 2 bölgüsü, dizayn dəyişməz qəbul edildi.

1. [x] Spec: `docs/superpowers/specs/2026-09-23-faza-f-automation-design.md` — istifadəçi təsdiqlədi
2. [x] Plan: `docs/superpowers/plans/2026-09-23-faza-f-faza1-automation.md` — Task 0–16
3. [x] İcra: inline, **tam avtonom** (istifadəçi: "mövzunu verim və tam hazır video əldə edim") —
   aralıq təsdiq yoxdur, vizual yoxlamanı Claude özü edir
4. [x] Task 15 — inteqrasiya: `_integ-compound` (6.27 dəq, 18m23s, HAZIRDIR)
5. [x] Task 16 — E2E: `how-credit-cards-actually-work` — 2380 söz, narration 662 s, **11.19 dəq**,
   29m58s, `final_video_problems=[]`, `pack_problems=[]`, resume 8 mərhələni 11.5 s-də keçdi
6. [x] **E2E-dən sonra vizual düzəliş (2026-09-24/25, TAMAM):**
   - Tapıldı: 300 s-də fon "game interface" → mənasız yazı; thumbnail-da bust bayquşun kəsik tərəfi içəri baxırdı
   - Düzəldildi, commit `5d58498`: `scene_plan.clean_bg_prompt` (yazı daşıyan hissələri atır, `TEXT_BEARING`
     regex, `FALLBACK_BG`) + `cards.paste_sprite` (bust sağ-alt kənara yapışır, kəsik tərəf çölə flip)
   - Epizodun scenes.json-u `clean_bg_prompt` ilə yeniləndi; bg/, bg_hd/, cards/, youtube/, mp4 silindi;
     `python run.py --resume how-credit-cards-actually-work` arxa planda işə salındı (render_bgs 33/37-də idi)
   - **Problem (aşağıda həll edildi):** `bg/sc16.png` — kredit kartının yaxın planı, üstündə mənasız yazı
     ("Pirxirt", "COOVAUDRYOND", rəqəmlər). Filter "credit card"-ı tutmur, bu mövzuda kart hər yerdədir.

   - **2026-09-25 HƏLL EDİLDİ (commit `f7ce99b`):** 37 fon yoxlandı → 8-də aydın gibberish (sc12/14/16/20/21/24/28/34).
     Eyni seed ilə 15 probe render: güclü negativ prompt **heç nə vermir**; yazını obyektin adı gətirir.
     `clean_bg_prompt`: payment card → `BLANK_CARD`, pizza box → tray, calendar/calculator/bills/card reader/…
     atılır, "showing/indicating …" quyruqları kəsilir. 95 test. 32 səhnənin promptu dəyişdi, fonları silindi,
     `python run.py --resume how-credit-cards-actually-work` işə salındı (2026-09-25)

   - **2026-09-25 TAMAM:** yenidən qurma 11.19 dəq HAZIRDIR (19:13→19:42, ~30 dəq), 37 fonun hamısı yazısız,
     kadrlar 30/120/300/500 s + thumbnail vizual yoxlandı — qüsur yoxdur. **Faza 1 bağlandı.**

**FAZA G — keyfiyyət düzəlişi (2026-09-26, TAMAM).** İstifadəçinin 5 şikayəti + "Remotion istifadə et":
1. Səs yazıları oxumur → intro/bölmə başlığı/outro indi səsləndirilir (`tts_gen`, commit dddd4f3)
2. Şəkillər təkrar → səhnə 14–32 söz (~7 s, ~98 şəkil), LLM hissə-hissə + son mövzular, təkrar yenidən soruşulur,
   fallback pool təkrarsız (commit 6571652)
3. Şəkillər məntiqsiz/qarışıq → bir əsas obyekt, max 3 prompt hissəsi, SDXL "medium shot, single focal subject"
4. Animasiya dona-dona → ölçüldü: zoompan 73/89 kadr dayanıb sıçrayırdı; Remotion CSS transform 0.005 px təcil
   (`Remotion/`, `Projects/remotion_build.py`, commit 0cfa5cb, e8c785c, b5d16b4)
5. Personaj donuq/səliqəsiz → yalnız tam bədən pozları, eyni ölçü/yer xətti, spring giriş, nəfəs, səsə uyğun tərpənmə,
   poz cross-fade, ardıcıl eyni poz yox
**2026-09-26 sessiyası (istifadəçi "yaddaşa yaz, sonra davam edəcəyik" dedi — burada dayandı):**
- scene_plan düzəlişləri (commit 5ec7e61, dd44ecb, da0ea64, c183352, 29a202d): LLM yarımçıq/yenidən nömrələnmiş
  cavabı `align()` ilə düzülür; təkrarlar 12-lik hissələrlə 3 raund yenidən soruşulur (`RETRY_NOTE` — fiziki metafora);
  <5 sözlük prompt "pis" sayılır; ekranlı cihazlar (phone/computer/laptop/tablet), sheet/written, someone/blackboard
  filtrdə; `FALLBACK_POOL` = biznes/avtomatlaşdırma metaforaları; SDXL negativə collage/grid/split screen. 114 test.
- **Tapıldı və düzəldildi (commit d30f12c, ac6d3c6):** `stages._build_cmd` hələ köhnə `build_episode.py`-ni çağırırdı —
  Remotion pipeline-a QOŞULMAMIŞDI. İndi `remotion_build.py`.
- `what-is-business-automation`: 98 səhnə, narration 935 s (15.6 dəq). 98 fon vizual yoxlandı (scratchpad sheet1–4.jpg):
  bir aydın obyekt, məntiqli. 6 problemli səhnə (21, 23, 28, 47, 56, 91) promptu əl ilə dəyişdirildi, `--only` ilə
  yenidən render + upscale edildi, yoxlandı — yaxşıdır. scene_plan/render/upscale/tts/srt HAZIR.
- **2026-09-26 TAMAM — FAZA G bağlandı.** Əvvəlki render sessiya bağlananda 4563/28054-də ölmüşdü → yenidən.
  Yoxlamada tapıldı: Ken Burns `inOut(sin)` hər ~7 s-lik səhnənin başında/sonunda fonu dayandırırdı ("dur-get")
  → sabit sürət (commit `425128e`), epizod yenidən render edildi (Remotion ~22 dəq, 8x concurrency).
  Final: **15.59 dəq**, 1920×1080 H.264 High 4.1 yuv420p, AAC 48 kHz stereo, **−14.2 LUFS**, 435 MB,
  tam dekod xətasız, `final_video_problems=[]`, youtube/ paketi (8 fəsil, thumbnail) hazır.
  Kadrlar (intro, bölmə başlığı, səhnələr, outro, thumbnail) vizual yoxlandı. 114 test keçir.

**2026-09-26 — `how-ai-agents-change-automation` HAZIRDIR (ilk tam avtomatik keyfiyyət yoxlamalı epizod):**
16.12 dəq, 1920×1080 H.264 High 4.1 yuv420p, AAC 48 kHz stereo, −14.2 LUFS, 457 MB, dekod xətasız,
`final_video_problems=[]`, youtube/ (8 fəsil, thumbnail). `check_bgs`: raund 1 → 10/97 pis, raund 2 → 6, raund 3 → 2
(ehtiyat fona keçdi); 10 fon avtomatik yenidən çəkildi. 128 test keçir.

**2026-09-27 — FAZA H (istifadəçi: "kredit əlavə etdim, yarımçıq qalanları tamamla, musiqi əlavə et,
personaj sabit dayansın, şəkli səhnəyə uyğunlaşsın, tam hazır olsun"):**
1. `what-is-cash-flow` yenidən quruldu: pozlar səhnə mətninə görə yenidən seçildi (52-dən 34-ü dəyişdi,
   bir dəfəlik skript), sabit bayquş, güzgülənmiş fonlar, Carefree musiqisi, istinadlı youtube/ paketi.
2. İndi: istifadəçi Claude-a **`Video: <Mövzu>`** yazır (tetik əmri, 2026-09-27) və ya özü "ELI5 Yeni Video" qısayolunu
   açır → `python run.py "Mövzu"` (~45 dəq: skript 1 dəq, ~50 ChatGPT şəkli ~10 dəq
   [limit 5/dəq], hakim ~2 dəq, upscale ~13 dəq, TTS+SRT ~2 dəq, Remotion ~11 dəq). Claude `Start-Process` ilə
   müstəqil açır; fon yoxlamasını pipeline özü edir (`check_bgs`, `Episodes/<slug>/bg_qa.json`).
Köhnə 2 epizod (`what-is-business-automation`, `how-ai-agents-change-automation`) 2026-09-27 istifadəçi
qərarı ilə silindi. `Episodes\`-də yalnız `what-is-cash-flow` qalıb.

---

## FAZA F dizaynı (təsdiqləndi 2026-09-23, icra olundu)

### İstifadəçi tələbləri (2026-09-23, öz sözləri ilə)
- Mövzu verəndə video avtomatik yaransın, hazır şəkildə təqdim olunsun
- Video **heç vaxt 10 dəqiqədən aşağı olmasın**
- Şəkil və videolar keyfiyyətli olsun
- Video effektləri daha yaxşı olsun
- **Personaj videoya çox səliqəsiz və keyfiyyətsiz yerləşir** — düzəldilməli
- YouTube-da paylaşmaq üçün ideal vəziyyətə gətirilməli

### Diaqnoz — kadr analizi (f120.png, ölçülmüş, təxmin deyil)

| Problem | Kök səbəb |
|---|---|
| Bayquş bulanıq | Sprite mənbəyi 200×235 px, ekranda 756 px → **3.2× upscale** |
| Bayquş "yapışdırılmış" | Kölgə yox, ayaqlar yerə oturmur, kənarda ağ halo, height 0.70 = kadrın 70%-i |
| Fon yumşaq | SDXL 1344×768 → Ken Burns 3840×2160 → **2.9× upscale** |
| Fon kompozisiyası pozulur | `__SPACE__` boş sahə istəyinə SDXL əməl etmir, bayquş obyektləri örtür |
| Subtitr amatyor | Arial Bold ağ + outline, çox böyük, personajın üstünə düşür, fon qutusu yox |
| Effektlər monoton | 29 səhnə boyu yalnız tək oxlu Ken Burns + eyni 0.5 s fade |

### İstifadəçi qərarları (AskUserQuestion, 2026-09-23)
1. **Sprite HD = "Hər ikisi"** — indi Real-ESRGAN upscale, böyük sheet gələndə əvəz edilir
2. **Effektlər = "+ Animasiyalı fon (LTX-Video I2V)"**
3. **Kompozisiya = "Kiçik, künc"** — hündürlük 0.38–0.45, kölgə ilə

### Təklif olunan arxitektura

**Orchestrator** — `Projects/pipeline.py`, tək əmr: `python run.py "Mövzu"`
Mövcud skriptlər **dəyişmir**, subprocess kimi düzgün venv ilə çağırılır.
`Episodes/<slug>/state.json` hər mərhələnin statusunu saxlayır → `--resume <slug>` qaldığı yerdən davam edir.

| # | Mərhələ | Venv | Resume açarı |
|---|---|---|---|
| 1 | script_gen | Projects | `script.md` |
| 2 | scene_plan | Projects | `scenes.json` |
| 3 | ComfyUI start | ComfyUI\.venv | port 8188 cavabı |
| 4 | render_bgs + upscale | Projects | `bg/scNN.png` sayı |
| 5 | tts_gen | TTS\.venv | `audio/scNN.wav` sayı |
| 6 | make_srt | Whisper\.venv | `narration.srt` |
| 7 | build_episode | Projects | `<slug>.mp4` |
| 8 | publish paketi | Projects | `youtube/` |

Hər mərhələdən sonra avtomatik yoxlama: söz sayı, audio uzunluğu, pix_fmt, A/V drift.
Səhv → dayan, səbəbi yaz.

**Keyfiyyət düzəlişləri**
- Sprite: Real-ESRGAN 4× offline → `sprites_hd/` (200×235 → 800×940), alpha ayrıca, 1px alpha erode (halo)
- Sprite ekran hündürlüyü 0.70 → **0.42** (454 px) → böyütmə yox, kiçiltmə → kəskin
- Ayaq altına yumşaq kontakt kölgəsi (ellips, multiply) + arxaya yüngül vignette
- Fon: SDXL → 4x-UltraSharp upscale → 5376×3072 → Ken Burns bundan kəsir
- Subtitr: Montserrat SemiBold, kiçik ölçü, yarımşəffaf qara qutu, maks 2 sətir, bayquş zonasından yuxarı
- Effektlər: çoxoxlu Ken Burns (zoom+pan, istiqamət növbələşir), keçidlər növbələşir
  (fade/slideleft/wipe/dissolve), bölmə başlığı lower-third, 4 s intro + 6 s outro,
  fon musiqisi ducking ilə
- YouTube: audio 48 kHz stereo, **-14 LUFS**, `youtube/` qovluğu (title, description+chapters, tags, thumbnail.png)

**Uzunluq 8–10 dəq (sərt qayda, 2026-09-26; əvvəl ≥ 10 dəq idi)**
`--words 2150` (199 wpm → 10.8 dəq). Addım 5-dən sonra yoxlama: narration < 600 s olsa,
avtomatik əlavə bölmə yazdırılır və TTS təkrarlanır.

**LTX-Video** — 2026-09-26 istifadəçi qərarı ilə plandan çıxarıldı.

---

## Risklər / açıq suallar

- **Fonlar OpenAI-dən asılıdır** (gpt-image-2): API əlçatmazdırsa mərhələ 2 dəfə təkrar edilir, sonra dayanır
  (lokal SDXL ehtiyatı istifadəçi qərarı ilə silindi). `gpt-image-2`-nin dəqiq qiyməti ölçülməyib
  (158 çıxış token/şəkil; gpt-image-1 low = 400 token ≈ $0.016).
- Musiqi CC BY 4.0-dır: description-dakı istinad silinməməlidir (YouTube-a yükləyəndə olduğu kimi saxla).
- Böyük character sheet istifadəçidən gözlənilir (verəndə `BOXES` və `CUTS` koordinatları yenidən hesablanır).
- Audio hazırda 24 kHz mono — Faza 1-də 48 kHz stereo-ya keçir.

---

## Təkrarlanmamalı yanlış yollar

| Yanaşma | Nəyə görə rədd edildi |
|---|---|
| Personajı generativ model ilə çəkmək (IP-Adapter, LoRA) | Tutarlılıq yoxdur. Sprite overlay 100% piksel-eyni nəticə verir. |
| `montage.py`-da `-pix_fmt` verməmək | ffmpeg yuv444p (High 4:4:4) seçir, heç bir pleyer/YouTube açmır. |
| Sprite mövqeyini LLM-dən istəmək | LLM bütün səhnələri eyni tərəfə qoyur. Koddan deterministik təyin edilir. |
| Skripti tək çağırışda yazdırmaq | Model söz hədəfini 40% aşağı tutur. Bölmə-bölmə + OVERSHOOT lazımdır. |
| Analogiya sahəsini LLM-ə sərbəst buraxmaq | Hər bölmədə eyni analogiya (lemonade stand) təkrarlanır. |
| `cmd.exe /c start /min run_comfyui.bat` (Git Bash-dan) | ComfyUI qalxmır. Birbaşa `.venv/Scripts/python.exe main.py ...` işə salınmalıdır. |
| Heredoc `str.replace` ilə fayl düzəlişi | Səssiz uğursuz olur. `plan.md` və oxşar fayllar **Edit tool** ilə düzəldilməlidir. |
| `build_episode.py`-da müddətləri XFADE ilə doldurmamaq | Narration-un sonu 14 s kəsilir. |
| Heredoc/`python -c` daxilində `\b` yazmaq (2026-10-04, #28-in təkrarı) | Alət zəncirində 0x08 olur, regex səssizcə zəifləyir (`visuals.py` faiz/dollar, `progress.md`). Regex-i Edit/Write tool ilə yaz və ya `chr(92)+"b"`; `test_no_backspace_characters_in_source` tutur. |
| `sed -i` əvəzində `\n` yazmaq | Git Bash sed literal `\n` qoyur, Python sintaksisi pozulur. Çoxsətirli düzəliş yalnız Edit tool ilə. |
| LLM promptunda yer tutucu nümunə (`["..", ".."]`) | Model hərfən köçürür → videoda boş maddələr. Nümunə həmişə real dəyərlərlə; validator ≥3 hərf tələb edir (#49). |
| Chart vahidini LLM-ə tapşırmaq | "$4" ekranda "4" çıxdı. Vahid danışıqdan deterministik (`visuals.unit_of`); +/− düsturda ortaq vahid. |
| Animasiya seçimində növ/başlıq limiti olmamaq | 40-dan 22 keypoints, eyni başlıq 5 dəfə. `KEYPOINTS_SHARE` 0.3 + unikal başlıq. |
| E2E-də `scene_plan`-dan sonra planı yoxlamadan gözləmək | Pullu mərhələlərə (gpt-image) pis planla keçilir. `scenes.json`-u dərhal yoxla (animasiya payı, növlər, boş mətn); pisdirsə prosesi dayandır, düzəlt, `--resume <slug> --from scene_plan`. |
| Shell işçi qovluğu `Episodes\<slug>\` içində qalanda `forget_episode.py` | Windows qovluğu kilidləyir (WinError 32). Əvvəl `cd /c/YouTubeAI`. |
| Windows ffmpeg-ə `/tmp/...` yolu vermək | Açılmır. Müvəqqəti fayllar scratchpad qovluğuna. |
| Şərhdə/testdə ölçülməmiş rəqəmi fakt kimi yazmaq | Data dürüstlüyü pozulur. Ölçülməyibsə "ölçülməyib/ehtiyat" yaz. |
| Ssenari rəqəm yoxlamasında `grep … \| cut -c1-260` (2026-10-04, why-9-99) | Abzas kəsilir — sc54-ün "$99.90" hesabı ilk baxışda "ssenaridə yoxdur" göründü. Rəqəmli abzası tam oxu (`sed -n 'Np'`). |
| if/elif zəncirində yeni xüsusi şərti ümumi şaxədən SONRA qoymaq (2026-10-04, `math_check._run`) | "nine ninety-nine" qaydası heç işləmədi (`UNITS/TENS` şaxəsi əvvəl tutdu); test tutdu. Xüsusi hal həmişə ümumidən əvvəl. |
| Vizual yoxlamanı yalnız tam render-dən sonra etmək (2026-10-05, #53) | Boş chart 20 dəq yenidən render apardı. `build_episode` bitən kimi `remotion_props.json`-da hər animasiyanın `reveal[0]/frames` nisbətinə bax (> 0.35 → şübhəli). |
| Python skripti ilə `open(..., newline='\n')` yazıb CRLF faylı LF-ə çevirmək (2026-10-05) | `git diff` bütün faylı dəyişmiş göstərir. Edit tool üslubu saxlayır; skriptlə yazanda orijinal sonluğu saxla (bax scratchpad `restore_eol.py` məntiqi: HEAD blob-da `\r\n` varsa CRLF). |
| Bir Bash çağırışında iki heredoc + `'''` Python mətni (2026-10-05) | Bash ikinci heredoc-da "unexpected EOF" verdi, AMMA birinci Python bloku artıq icra olunmuşdu — fayl yarımçıq dəyişdi. Böyük kod blokunu Write ilə scratchpad-a yaz, kiçik splice skripti ilə yapışdır; splice idempotent olsun. |
| LLM-in verdiyi mənbə URL/sitatına güvənmək (2026-10-05 probe) | gpt-4o-mini URL-ləri uydurdu (404), sitatları parafraz etdi. Mənbə yalnız səhifə yüklənib rəqəm + cümlə orada tapılanda qəbul olunur. |
| Mənbə hakiminə dar axtarış ipucunu (`fact_need`) "qərar" kimi vermək (E2E 2026-10-05) | Hakim əlaqəli statistikanı (48% firma qiymət artırdı) "aid deyil" dedi. Hakim yalnız video qərarına baxır; `fact_need` yalnız axtarış ipucudur. |
| Skriptlə sənədə `\f` (məs. `Projects\forget`) yazmaq | Form feed (0x0C) olur — `progress.md`-də tapıldı. Guard test indi kod + `.md`-də bütün idarə simvollarını tutur. |
| Bash-da `VAR=1 python …` əvəzinə `.venv=1 Projects/…python` yazmaq (2026-10-06) | Nöqtəli ad bash dəyişəni deyil → "command not found", reyestr yazılmadı. Sadəcə `Projects/.venv/Scripts/python -` yaz, prefikssiz. |
| Run dayananda dəyişmiş `scenes.json` promptlarının orijinalını saxlamamaq (2026-10-06) | check_bgs yeni promptu yazıb render-dən əvvəl ölür → şəkil köhnə, prompt yeni; orijinal heç yerdə yoxdur. Resume-dan əvvəl uyğunsuzluğu bil, hakim şəkli yenidən yoxlayır. |
| Quoted heredoc-dakı Python `'''…'''` sətrinə `"\n"` yazmaq (2026-10-06, ÜÇ DƏFƏ — qeyddən sonra da) | Python `\n`-i real yeni sətrə çevirir → `newline="` + yeni sətir → SyntaxError / replace tutmur. Yeni sətir literalı olan kodu Edit aləti ilə yaz; heredoc-da Python yazmazdan əvvəl `\n` axtar — varsa Edit istifadə et. |

| Heredoc-dakı Python splice-da əvəzlənən mətnə `"\n"` (2026-10-07, DÖRDÜNCÜ dəfə — `script_qa.story_fixes`) | Yenə SyntaxError. QAYDA: splice mətnində `\n` varsa splice YOX, birbaşa Edit aləti. Splice yalnız `\n`-siz tək sətirli əvəzləmələr üçün. |
| Heredoc splice-da `'''…'''` daxilində `\\n` qaçışı (2026-10-07, `script_gen` hint) | Əvəzlənəcək mətn faylla üst-üstə düşmədi, `assert` dayandırdı (zərərsiz). Çoxsətirli/qaçışlı mətn → Edit aləti. |
| `sleep N; cmd` ilə arxa plan prosesini gözləmək (2026-10-07) | Alət bloklayır. Arxa plan əmri `run_in_background` ilə — bitəndə bildiriş gəlir; aralıq yoxlama üçün loqu oxu. |
| Python skript çıxışını fayla yönləndirib dərhal oxumaq (2026-10-07) | stdout bufer olunur, loq boş görünür. `python -u` və ya `PYTHONUNBUFFERED=1` ilə işə sal. |
| Bash-da `python3 - <<EOF … \|\| .venv python - <<EOF2` fallback zənciri (2026-10-08) | Windows-da `python3` Microsoft Store stub-ıdır — stdin gözləyib 120 s ilişdi, fayl dəyişmədi. `python3` yazma; yalnız `Projects/.venv/Scripts/python`; mətn düzəlişi isə Edit aləti ilə. |
| Heredoc Python splice-da `"…\\n"` (2026-10-08, BEŞİNCİ dəfə — `test_pipeline.py` fixture) | Fayla real yeni sətir yazıldı (string literal qırıldı); Edit ilə düzəldildi. QAYDA mütləqdir: əvəzlənən mətndə `\n` VARSA heredoc YOX — yalnız Edit aləti. |
| renderStill probunda fon kimi thumbnail götürmək (2026-10-08) | Thumbnail-da yazı və bayquş var — kadrda "ikinci bayquş/yazı" görünür, pipeline xətası kimi çaşdırır. Probe fonu yazısız şəkil olsun (və ya StudioBackdrop). |
| Heredoc Python splice-da `rf"\b…"` (2026-10-08, ALTINCI dəfə — `case_model.py`) | Fayla real backspace (0x08) yazıldı, 2 test düşdü (`test_no_backspace_characters_in_source` tutdu). Escape (`\b`, `\n`) olan kod HEÇ VAXT heredoc-dakı Python string-i ilə yazılmır — yalnız Edit/Write aləti. |
| Heredoc Python splice-da `"\n\n…"` axtarış mətni (2026-10-08, YEDDİNCİ dəfə — `script_gen.py`) | Uyğunluq tapılmadı (assert dayandırdı, fayl dəyişmədi). QAYDA: `\n` olan mətnin əvəzlənməsi YALNIZ Edit aləti ilə — heredoc-da Python splice YOX. |
| Claude-un PowerShell alətindən `Start-Process … run.py --resume` (2026-10-08) | Alət çağırışı bitəndə proses ağacı ilə birlikdə öldü (log `[1/13] script_gen` sətrində qaldı, xəta yox, 18 dəq boşa). Düzgün yol: `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c "…python.exe -u run.py … > log 2> log.err"'; CurrentDirectory='C:\YouTubeAI'}` — sonra 20 s gözləyib python prosesinin sağ olduğunu yoxla. |

**Daimi qayda (2026-10-04):** hər videoda rast gəlinən HƏR xəta video təhvil verilməzdən əvvəl bu cədvələ və ya
reyestrə yazılır (CLAUDE.md addım 5). Xəta yoxdursa jurnalda "xəta yoxdur".

---

## İcra jurnalı (ən yeni yuxarıda)

### 2026-10-05/06 — 12 addımlıq məzmun standartı (#54–#63), E2E davam edir
- Yeni modullar: `speech.py`, `captions.py` (yeni `captions` mərhələsi), `research.py`, `script_qa.py`; dəyişən:
  `script_gen` (plan → mənbə → yazı → hekayə/redaktor qapısı → rəqəm auditi → `script_qa.json`), `visuals` (`stats`,
  keypoints yox), `scene_plan`/`check_bgs` (literal kadr, `generic` ≤10%), `tts_gen` (Cold Open + to_speech),
  `remotion_build` + Remotion (`Kicker`, intro `hook`, `Stats`), `publish_pack` (mənbə linki). 442 test.
- Quraşdırıldı: `Projects\.venv`-ə `pypdf`, `num2words` (uv pip).
- E2E xətaları (hamısı qeydə alındı): #61 (yumşaq redaktor, ziddiyyətli uzatma, mənbə təhrifi, başlıq ":" bug),
  #62 (retry `--force`-suz), #63 (itki işarəsi); mənbə hakimi `fact_need`-lə səhv müqayisə (yanlış yollar cədvəli);
  mənim alət səhvlərim: CRLF→LF, ikiqat heredoc, heredoc-da `\n` qaçışı (yanlış yollar cədvəli).

### 2026-10-05 — pricing (why-9-99) videosu təsdiqləndi, epizod yaddaşı silindi
Kod düzəlişləri qalır: reyestr #50–#53 (347 test).

### 2026-10-03/04 — analitik animasiyalar (#45), kart təkrarı (#46), thumbnail (#47), dedupe (#48)
İstifadəçi 5 tələb verdi; model dəyişikliyi rədd edildi ("olduğu kimi qalsın"), animasiya payı ~60%. Kod + 34 yeni test
(328 keçir), Remotion `tsc` təmiz, 9 animasiya növünün kadrı render edilib vizual yoxlandı, real thumbnail probu
(2 × gpt-image-2 high, ~72 s/şəkil) keçdi.
E2E test videosu (break-even) təsdiqləndi, epizod yaddaşı silindi (2026-10-04).

### 2026-10-02 — #40 hesab/rəqəm səhvləri fail-closed yoxlama, #41 429 gözləmə
- `number_audit.py` (yeni), `math_check` sabit qaydaları + son hökm 2-ci qatda, `script_gen` SYSTEM qaydası, `llm.retry_after`
- 288 test keçir. Real: why-9-99 ssenarisi düzəldi ("$50 an hour for one hour each … $150 … more for four clients"), ~5 dəq
- `Hazir_Videolar\` və `Episodes\why-9-99…` istifadəçi tərəfindən silindi (köhnə video səhvli idi); mövzu yeni sessiyada sıfırdan çəkiləcək

### 2026-09-30 — video 10–12 dəq (#37); bayquş gpt-image-2 + magenta key (#36)
- 253 test keçir; real: 'What Is Break-Even Point?' intro/outro + səhnə bayquşu gpt-image-2 ilə, fon silindi, hakimdən 1-ci cəhddə keçdi

### 2026-09-30 — sabit, mövzuya uyğun giriş/çıxış bayquşu (#35, #36)
- 247 test keçir; real API: 'What Is Cash Flow?' → əşya 'a clear glass jar filled with coins', intro/outro hakimdən 1-ci cəhddə keçdi; Remotion still renderində bayquş tərpənmir, uzun başlığı örtmür

### 2026-09-30 — hesab səhvlərinə qarşı qapı (#34)
- `math_check.py` + pipeline qapısı; 233 test keçir. Real payment-fees ssenarisində "eight hundred" → "eighty dollars", başqa dəyişiklik yox, 2 təkrar yoxlamada 0 yalançı həyəcan
- Artıq hazır `Hazir_Videolar\how-small-businesses-…` videosunda səhv qalır (yeni kod yalnız yeni videolara tətbiq olunur)

### 2026-09-29 gecə — təsdiq + yaddaş silmə mərhələsi
- Köhnə pricing run-u (`--resume why-9-99-…`, check_bgs/render_bgs prosesləri) istifadəçi istəyi ilə dayandırıldı
- Yeni: video hazır olandan sonra Claude AskUserQuestion ilə təsdiq istəyir; təsdiqdə `Projects\forget_episode.py <slug>` → `Episodes\<slug>\` + həmin epizodun `_run_*.log/.err` silinir (`Hazir_Videolar` qalır), progress.md-dən o videonun sətirləri çıxarılır (CLAUDE.md addım 7; 2026-10-04-dən əvvəl 6 idi)
- Kod başqa epizodların məlumatını oxumur (yoxlanıb) — silmədən sonra pipeline köhnə videonu "xatırlamır"
- 196 test keçir (`test_forget_episode.py`)
- İstifadəçi təsdiqi ilə 5 köhnə epizodun (cash-flow, profit-margin, same-business-after-ai, will-ai-replace, yarımçıq pricing) yaddaşı + `Temp\cashflow_*` silindi → `Episodes\` boşdur, pipeline təmiz başlayır

### 2026-09-29 axşam — pricing yenidən (yeni qaydalar) + check_bgs düzəlişləri (#31, #32)
- İstifadəçi: köhnə pricing qeydlərini sil, yeni qaydalarla yarat → `Episodes\_archive` (1.8 GB) + köhnə `_run_pricing*` loqları silindi, yeni run başladı
- Run 1–3 mərhələ keçdi (skript 1319 söz ~8.8 dəq, yetkin ton), `check_bgs` 2 dəfə yanlış təkrarla düşdü → #31 (CLIP + gpt-4o təsdiqi); ikinci run-da hovuz dövrəsi göründü → #32
- İstifadəçi qərarı: pipeline düzəlişləri bitsin, sessiya bağlanır, növbəti sessiyada **başqa mövzu** veriləcək. Pricing epizodu `Episodes\why-9-99-…` 4/11-də dayandırılıb (`run.py --resume` ilə davam edə bilər və ya silinə bilər)
- 185 test keçir

### 2026-09-29 — Qaydalar: təkrar kadr qəti yox (#29) + yetkin görünüş, realist foto (#30)
- Kod + TDD: 168 test keçdi; CLIP modeli (`openai/clip-vit-base-patch32`) MusicGen venv-də, bir epizod ~17 s
- Kalibrasiya pricing fonlarında: təkrarlar ≥ 0.884, fərqli obyektlər ≤ 0.873 → hədd 0.88; köhnə epizodda 25 səhnə təkrar kimi tutuldu (qəbul olunan davranış)
- Video yaradılmadı (istifadəçi istəyi); növbəti mövzuda yeni stil ilk dəfə E2E yoxlanacaq

### 2026-09-28 — E2E: `why-9-99-feels-cheaper-than-10-the-psychology-of-pricing` HAZIRDIR
- **9.03 dəq** (542 s), −14.3 LUFS, `final_video_problems=[]`, musiqidə sükut yox; 55 səhnə, `owl_qa` 55/55 ilk cəhddə ok
- Vizual: 4 kadr + thumbnail — eyni bayquş, sağda; tapılan problem #27 (altyazıda `$39 .99`) → test + düzəliş, `--from build_episode` ilə yenidən montaj
- "Hook" yazısı/səsi silindi (#28) → `--from tts_gen` ilə yenidən quruldu
- Qeyd: 11/55 fon `check_bgs`-dən 3 cəhddə keçmədi (mismatch) → ehtiyat fon; səhnə 8 fonunda gpt-image öz-özünə robot çəkib (thumbnail-a düşüb)

### 2026-09-27 — FAZA I E2E: `what-is-profit-margin` HAZIRDIR (səhnə bayquşu + AI musiqi ilk dəfə)
- **8.92 dəq** (535 s), 1920×1080 H.264 + AAC, −14.2 LUFS, `final_video_problems=[]`, 65 dəq (18:47→19:52 UTC), xəta yox
- Mərhələ vaxtları: render_bgs 10 dəq · check_bgs 2.5 · **render_owls 11** · upscale_bgs 15 · tts 2.5 · **music_gen 3** · build 18
- Bayquş: 52/52 `owl_qa` ilk cəhddə ok; 12 kadr vizual yoxlandı — eyni personaj (eynək/kostyum/qalstuk), poz və
  əşya səhnəyə uyğun (pambıq qənd, tərəzi, pul, gül, sınıq qumbara), RGBA kənarı təmiz
- Musiqi: 6 klip × 25–27 s, trek 229 s, −17.8 LUFS. Videoda dövr nöqtəsində (228 s) 1.25 s sükut tapıldı → düzəldildi
  (reyestr #26), bu epizodun səsi video yenidən render olunmadan yenidən mikslənib (`-c:v copy`, hardlink bərpa)
- youtube.txt-də CC BY kredit yoxdur; thumbnail vizual yoxlandı

### 2026-09-27 — `will-ai-replace-employees` HAZIRDIR (tetik "Video: Will AI Replace Employees?")
- **9.38 dəq** (563 s), 1920×1080 H.264 High yuv420p, AAC 48 kHz stereo, 324 MB, musiqi Life_of_Riley
- 45 dəq tam avtomatik (20:50→21:35 UTC), `check_bgs` passed, xəta/əl müdaxiləsi yox
- 6 kadr + thumbnail vizual yoxlandı: fonlarda yazı/insan yox, bayquş sabit sağda, subtitr düzgün

### 2026-09-27 — FAZA H: musiqi + sabit personaj, cash flow tamamlandı
- Kredit əlavə edildi → `what-is-cash-flow` publish paketi hazırlandı
- Musiqi: FreePD bağlanıb → incompetech (Kevin MacLeod, CC BY 4.0) 4 trek; slug-a görə növbə; description-a istinad
- Personaj: `Owl.tsx` hərəkətsiz (nəfəs/yellənmə/danışıq/spring/tərəf sürüşməsi silindi), həmişə sağda;
  cross-fade ikiqat bayquş göstərdi (kadr yoxlaması) → poz fon keçidinin 7-ci kadrında ani dəyişir
- Pozlar: `vary_poses` (zorla növbə) → `fit_poses` (LLM-in səhnəyə uyğun seçimi), prompt "pick the pose that best fits"
- Köhnə sol-kompozisiyalı fonlar `flip` ilə güzgülənir (fonlarda yazı yoxdur → güzgü təhlükəsizdir)
- İş masasına "ELI5 Yeni Video" qısayolu; bat musiqini pipeline-a buraxır. 127 test.
- İstifadəçi: "köhnə videoları sil, yeni videolar bir qovluğa" → 2 köhnə epizod silindi; `deliver()` →
  `Hazir_Videolar\` (mp4 hardlink + png + txt). 129 test.
- İstifadəçi: "hər mövzunun ayrıca qovluğu olsun, qarışmasın" → `Hazir_Videolar\<slug>\` (mp4 + thumbnail.png +
  youtube.txt + subtitles.srt + script.md); iş masasındakı qovluq qısayolu istifadəçi tərəfindən silindi. 130 test.

### 2026-09-26 — E2E: `what-is-cash-flow` (ChatGPT şəkilləri, 8–10 dəq qaydası)
- Video HAZIR: **8.52 dəq** (511 s), 1920×1080 H.264 High 4.1 yuv420p, AAC 48 kHz stereo, −14.2 LUFS, 376 MB,
  dekod xətasız, `final_video_problems=[]`. 52 səhnə, gpt-image-2 (low), `check_bgs` 5 fonu yenidən çəkdi.
- **Publish paketi (youtube/) hazır deyil — OpenAI krediti bitdi.** Kredit əlavə edildikdən sonra:
  `python run.py --resume what-is-cash-flow` (yalnız publish mərhələsi, ~1 dəq).
- Yolda tapılıb kodda düzəldilən: reyestr #17–#23 (429 limit, 8–10 dəq, köhnə fayllar, təkrar obyekt,
  heyvanlar, ehtiyat fon, balans xətası). 118 test.

### 2026-09-26 — Şəkillər ChatGPT ilə, təmizlik
- İstifadəçi: "şəkillər chatgpt ilə hazırlansın", "lazımsız nə varsa sil", "LTX-i plandan çıxar";
  altyazı səsləndirməsi artıq var — dəyişməz qaldı
- `render_bgs`: OpenAI `gpt-image-2`, low (istifadəçi seçimi), 1536x1024 → 16:9, 4 paralel; probda
  gpt-image-1 bayquş üçün boş tərəfi pozdu, gpt-image-2 əməl etdi. ComfyUI yalnız upscale üçün.
- Silindi: SDXL/IP-Adapter/CLIP-vision modelləri, köhnə ffmpeg montaj kodu, Temp/Output/ComfyUI sınaqları,
  2 köhnə epizod, qalan 2 epizodun ara faylları (mp4 + youtube/ + srt qalıb) — ~16 GB. 102 test.

### 2026-09-25/26 — İstehsal: `what-is-business-automation`
- 2402 söz, **12.55 dəq**, 1920×1080 yuv420p, AAC 48 kHz stereo, 192 MB; ilk keçid ~38 dəq
- Fon yoxlamasında sc35-də cizgi oğlan ("a basketball player") → commit `27fc2d4`: insan isimləri
  promptdan atılır (`HUMAN`, "robot chef" saxlanır), 7 səhnə yenidən çəkildi, `--resume` ~19 dəq
- Dərs: negativ prompt nə yazını, nə insanı saxlayır — **ismi promptdan çıxarmaq** yeganə işləyən yoldur

### 2026-09-23/24 — Task 15/16 + vizual düzəlişlər
- `_integ-compound` 6.27 dəq, E2E `how-credit-cards-actually-work` 11.19 dəq — hər iki HAZIRDIR
- Kadr yoxlamasında 2 qüsur → commit `5d58498` (yazılı fon promptu filtri, bust thumbnail flip), 90 test
- Yenidən qurmada 3-cü qüsur: kredit kartı yaxın planda mənasız yazı (sc16) — 2026-09-25 həll edildi (`f7ce99b`)
- Dərs: SDXL yazı çəkə bilməz; obyektin özü yazı daşıyırsa (kart, əskinas, kitab) da gibberish çıxır →
  yalnız söz filtri kifayət deyil, hər fon vizual yoxlanmalıdır

### 2026-09-23 — Faza 1 kodu yazıldı (Task 0–14), git repo, 86 test
- Plandan kənara çıxmalar (hamısı ölçmə/kadr yoxlamasına əsasən):
  - **Ken Burns mənbəyi 3840×2160** (5120 → 0.6 fps idi, 10 dəq video ~8 saat); şəkillər bir dəfə dekod
    olunur, `loop` filtri ilə təkrarlanır (`-loop 1` hər kadrda 5K PNG açırdı və qraf 361-ci kadrda ilişirdi)
  - **Bust sprite-lər** (happy/thinking/confident — ayaqsız, yanı kəsik): kölgəsiz, kadrın alt və yan
    kənarına yapışır, kəsik tərəf ekran kənarına baxsın deyə lazım olanda `hflip`
  - **`center` sprite mövqeyi ləğv** (subtitr aşağı-mərkəzdə bayquşun üstünə düşürdü) — scene_plan sağ/sol
  - SDXL pozitiv promptdan "no people" çıxarıldı (CLIP inkarı anlamır → fonda insan çıxırdı), negativ genişləndi
  - İlk chapter adı "Intro" ("Hook" daxili termindir)

### 2026-09-23 — Faza 1 implementasiya planı yazıldı
- 17 task (0–16), TDD, hər task-da commit; layihə git repo deyil → Task 0-da `git init`
- Aşkarlanan faktlar: PATH-dakı `python` = hermes venv (Pillow yox) → hər şey `Projects\.venv` ilə;
  ffmpeg 8.1 → filter qrafı fayla (`-/filter_complex`), Windows 32K əmr limiti səbəbindən
- Spec dəqiqləşdirmələri planda: subtitr ölçüsü libass 288-miqyası, lower-third yuxarı-sol,
  iki qapılı uzunluq qaydası (söz qapısı + TTS saniyə qapısı → invalidate + scene_plan-dan təkrar)

### 2026-09-23 — FAZA F dizaynı təsdiqləndi, spec yazıldı
- İstifadəçi: Faza 1 / Faza 2 bölgüsü + dizayn olduğu kimi təsdiq
- Spec: `docs/superpowers/specs/2026-09-23-faza-f-automation-design.md` (qəbul meyarları A1–A9, 9 mərhələ)
- Spec-də dəqiqləşdirmə: keyfiyyət düzəlişləri üçün `montage.py`, `build_episode.py`, `script_gen.py` dəyişir
  (köhnə CLI geriyə uyğun); "skriptlər dəyişmir" yalnız orchestrator-un çağırış üsuluna aiddir

### 2026-09-23 — FAZA F dizaynı
- Kadr analizi aparıldı (`f120.png`): sprite 3.2× upscale, fon 2.9× upscale, kölgə yox, subtitr amatyor
- GPU yoxlanıldı: RTX 4060 Laptop 8 GB → LTX üçün sərhəddə
- Model qovluğu yoxlanıldı: `C:/YouTubeAI/Models` (SDXL var; **upscale model yoxdur, LTX yoxdur**)
- İstifadəçi 3 qərar verdi (sprite HD = hər ikisi, effekt = LTX I2V, kompozisiya = kiçik künc)
- Dizayn təqdim edildi → təsdiqləndi (eyni gün)
- `progress.md` yaradıldı

### 2026-09-23 — Addım 27 düzəlişi: video açılmırdı
- Kök səbəb: `pix_fmt=yuv444p` / `profile=High 4:4:4 Predictive` (RGB PNG girişi + `-pix_fmt` verilməyib)
- Düzəliş: `montage.py`-a `-pix_fmt yuv420p -profile:v high -level 4.1`
- 7.5 s test klipdə yoxlanıldı → istifadəçi təsdiqlədi → tam re-render → dekod testi xətasız

### 2026-09-22/23 — FAZA E (addım 21–28) tamam
- İlk tam epizod çıxdı: `trademark-copyright-patent`
- Yol boyu 6 real qüsur tapılıb düzəldildi: skript qısalığı, analogiya təkrarı, sprite mövqeyinin
  donması, müddətin səssiz klemplənməsi, xfade audio kəsilməsi, yuv444p
- Kokoro real sürəti ölçüldü: **199 wpm** (əvvəl 150 fərz edilirdi) → sabitlər yeniləndi
- Whisper tanıması 1550 söz = skriptlə söz-söz uyğun → audio/mətn hizalanması təsdiqləndi
