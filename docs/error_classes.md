# Xəta sinifləri kataloqu

Generated from `Projects/quality_gate.py` (`ERROR_CLASSES`) — əl ilə redaktə etmə: `python Projects/quality_gate.py --write-catalog`.

Yeni xəta tapılanda əvvəlcə mövcud sinfə aid olub-olmadığı yoxlanır. Aiddirsə, həmin qapının niyə buraxdığı düzəldilir (yalnız simptom yox); aid deyilsə yeni sinif + qapı + test əlavə olunur.

| Sinif | Tərif | Qapı (quality_gate) | Test |
|---|---|---|---|
| Hesab səhvi | ssenaridəki hesablama nəticəsi yanlışdır | math_check | `test_number_accuracy.py::test_real_bug_monthly_total_is_caught` |
| Buraxılmış dəyişən | qərar hesabı case-in bir dəyişənini unudur (naive hesab) | script_qa, case_model | `test_case_model.py::test_naive_calculation_that_drops_a_variable_is_caught` |
| Case uyğunsuzluğu | case kəmiyyəti modeldəkindən fərqlidir | script_qa, case_model | `test_case_model.py::test_case_quantity_that_contradicts_the_model_is_caught` |
| Uydurma rəqəm | model, mənbə, il və ya sabitdən gəlməyən rəqəm | math_check | `test_number_audit.py::test_given_number_outside_the_model_is_caught` |
| Köhnə mənbə | 3 ildən köhnə mənbə ilsiz sitat olunur | script_qa | `test_research.py::test_old_source_must_be_named_with_its_year` |
| Tərif/analogiya | termin səhv izah olunur və ya analogiya yanıldır / başqa biznesdir | script_qa | `test_script_story.py::test_review_checks_story_consistency_and_source_faithfulness`<br>`test_script_story.py::test_analogies_are_everyday_images_never_another_business` |
| Vəd cavabsız | video qərar sualına konkret qayda ilə cavab vermir | script_qa | `test_script_story.py::test_answer_must_be_a_concrete_conditional_rule` |
| Təkrar | eyni rəqəm 2 dəfədən çox deyilir, Recap misal/rəqəm təkrarlayır | script_qa | `test_script_story.py::test_same_figure_three_times_in_one_section_is_a_repeat`<br>`test_script_story.py::test_recap_with_an_example_is_rejected` |
| Generik kart | flow/timeline addımı case-ə bağlı deyil (Analyze → Evaluate…) | chart_empty | `test_data_visuals.py::test_generic_flow_steps_are_rejected` |
| Boş chart | chart-ın ilk saniyələrində yalnız başlıq görünür | chart_empty | `test_remotion_build.py::test_chart_scenes_render_a_skeleton_from_the_first_frame` |
| Real data itkisi/uydurması | yüklənmiş rəsmi seriya qrafikə düşmür və ya qrafikdə deyilməyən/interpolasiya olunmuş real data var | data_visuals | `test_data_sources.py::test_series_in_the_episode_needs_its_data_visual`<br>`test_data_sources.py::test_split_series_sentence_with_too_few_points_is_not_drawn` |
| Eyni animasiyalar | bir animasiya novu payi asir, ardicil eyni nov, nov sayi az | visual_variety | `test_visual_variety.py::test_quality_gate_fails_a_monotonous_video`<br>`test_visual_variety.py::test_one_kind_never_exceeds_its_share` |
| Generik foto | case biznesinin literal kadrı olmayan foto > 10% | bg_qa | `test_literal_frames.py::test_stage_fails_when_more_than_ten_percent_of_photos_are_generic` |
| Təkrar kadr | epizodda eyni obyekt/fon iki dəfə | bg_qa | `test_no_repeats.py::test_check_bgs_stage_fails_while_duplicates_remain` |
| Uşaqsayağı görünüş | oyuncaq/cizgi fon, uşaq musiqisi | bg_qa | `test_adult_look.py::test_judge_rejects_childish_images` |
| Səs səviyyəsi | yekun səs −14 ±1 LUFS deyil | video | `test_sfx.py::test_master_mixes_sfx_before_loudnorm_to_minus_14` |
| TTS dili/tələffüzü | rəqəm səsdə səhv/başqa dildə oxunur | captions_qa | `test_speech.py::test_numbers_are_spelled_for_the_voice`<br>`test_captions.py::test_mispronounced_number_is_reported` |
| Altyazı formatı | altyazı ssenaridən deyil və ya rəqəm "$4,000" formatında deyil | captions_qa | `test_captions.py::test_srt_uses_display_numbers` |
| Etiket toqquşması | chart/overlay/sayğac bayquş və ya altyazı ilə üst-üstə düşür | overlay | `test_remotion_build.py::test_overlay_box_avoids_the_owl_and_the_captions`<br>`test_remotion_build.py::test_wide_owl_on_a_chart_scene_stays_right_of_the_chart_area`<br>`test_data_visuals.py::test_map_counter_and_box_avoid_owl_and_captions` |
| Eyni animasiya | hərəkət planı son epizodlara > 50% oxşardır | motion | `test_motion.py::test_history_similarity_above_half_changes_the_theme` |
| Sabit kodlanmış data | chart-da danışıqda olmayan rəqəm | chart_empty | `test_visuals.py::test_number_not_in_narration_is_rejected`<br>`test_data_visuals.py::test_timeseries_number_not_said_is_rejected` |
| Ölü vaxt (səssiz kart) | qara kart + sükut; typewriter səhnə müddətini uzadır | motion, video | `test_remotion_build.py::test_props_carry_the_motion_plan_and_emphasis` |
| SFX səviyyəsi/sıxlığı | SFX nitqdən < 18 dB aşağı, 10 s-də > 2, söz ortasında | sfx | `test_sfx.py::test_density_is_at_most_two_per_ten_seconds`<br>`test_sfx.py::test_sfx_sits_at_least_18_db_below_speech` |
| Real şəxs haqqında mənbəsiz hüquqi iddia | real şəxs/şirkət haqqında ittiham (sued, fraud…) | script_qa | `test_script_story.py::test_unsourced_legal_claim_about_a_real_company_is_caught` |
