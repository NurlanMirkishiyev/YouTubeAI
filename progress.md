# progress.md — YouTubeAI icra jurnalı

> **Bu fayl nə üçündür:** hər dəfə işə davam edəndə Claude əvvəlcə bu faylı oxuyur və
> son icranın harada dayandığını bilir. **Hər mərhələ tamamlananda bu fayl yenilənir.**
> Qayda: "Cari vəziyyət" və "Növbəti dəqiq addım" bölmələri həmişə aktual olmalıdır;
> tamamlanan iş "İcra jurnalı"na bir sətir kimi əlavə edilir (ən yenisi yuxarıda).

**Layihə:** `C:\YouTubeAI` — həftədə 2 ədəd 10–12 dəq "ELI5 Business" YouTube videosu üçün lokal pipeline
**Master plan:** `plan.md` (addım 01–36)
**Son yenilənmə:** 2026-10-02

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
| 1 | Fonda mənasız yazı (hər epizod) | SDXL yazı çəkə bilmir; obyektin adı yazını gətirir | `clean_bg_prompt` söz filtri + **`check_bgs` vision hakimi** yenidən çəkir (`f7ce99b`, `795a665`) |
| 2 | Fonda insan / insan əli (ep2 sc35, ep3 sc02/sc48) | İnsan ismi promptda; negativ prompt kömək etmir | `HUMAN` filtri (athlete, hands, … əlavə) + `check_bgs` (`27fc2d4`, `795a665`) |
| 3 | Boş/mənasız, kazino, deformasiya fonlar (ep3 sc09/27/97) | LLM zəif metafora seçir | `check_bgs`: no_subject / off_topic / deformed → yeni prompt |
| 4 | Yenidən çəkmə eyni şəkli verirdi (ep3) | Sabit seed (`BASE_SEED + n`) | hər cəhddə yeni seed, `scenes.json`-da `seed` (`795a665`) |
| 5 | Prompt düzəlişi itdi (ep3) | `render_bgs` sonda köhnə `scenes.json`-u üstdən yazırdı | `save_bg_paths` faylı təzədən oxuyur, yalnız `bg` yazır (`795a665`) |
| 6 | Pis fon 3 dəfə də pisdirsə pipeline ilişə bilərdi | — | 3 raunddan sonra istifadə olunmamış `FALLBACK_POOL` fonu |
| 7 | Hakim 84/97 yaxşı fonu "insan" dedi | gpt-4o-mini + tək "ok?" sualı + narration-dakı "you" | gpt-4o, ayrı bəli/xeyr yoxlamaları, "yalnız şəklə bax" (`795a665`) |
| 8 | Animasiya dona-dona | ffmpeg zoompan tam piksel | Remotion sub-pixel (`0cfa5cb`) |
| 9 | Fon hər kəsişdə dayanırdı | Ken Burns `inOut` easing | sabit sürət (`425128e`) |
| 10 | Remotion pipeline-a qoşulmamışdı | `_build_cmd` köhnə skripti çağırırdı | `test_build_stage_renders_with_remotion` (`d30f12c`) |
| 11 | Render sessiya bağlananda öldü | Proses Claude sessiyasına bağlı idi | Claude pipeline-ı **`Start-Process` ilə müstəqil** açır; ölsə `--resume` qaldığı yerdən |
| 12 | Video açılmırdı (yuv444p) | `-pix_fmt` verilməmişdi | spec-ə kodlama + `final_video_problems` yoxlaması |
| 13 | Video 10 dəq-dən qısa | LLM söz hədəfini tutmur | bölmə-bölmə yazı + TTS saniyə qapısı |
| 14 | Hakim API limitinə (429) düşən fonu yoxlamadan keçirdi (ep3 sc89) | 1–4 s backoff TPM limitinə azdır | xətalı fonlar 30 s gözləyib ardıcıl yenidən yoxlanır (`3cee56c`) |
| 15 | Mərhələ bir dəfəlik xəta ilə bütün videonu dayandırırdı | retry yox idi | uğursuz mərhələ 30 s sonra 2 dəfə yenidən cəhd edilir (`547950f`) |
| 16 | "smart kitchen scale/oven" ekranında rəqəm/yazı (ep3 sc16/sc23) | ekranlı cihaz | `digital …`, `smart <cihaz>` yazı daşıyan sayılır, "smart robot" qalır (`547950f`) |
| 17 | gpt-image 97 şəkildən 55-ni 429 ilə itirdi (ep4) | hesab limiti dəqiqədə 5 şəkil | sürüşən pəncərə limiter + API-nin dediyi qədər gözləmə (`63e3379`) |
| 18 | Video 16 dəq çıxırdı; istifadəçi: **8–10 dəq, 10-dan uzun olmasın** | söz hədəfi xalis 199 wpm ilə, max qaydası yox idi | effektiv 150 söz/dəq, default 1230 söz, skript və TTS qapıları həm uzadır həm qısaldır (`--shorten`), final video > 600 s → xəta |
| 19 | Səhnə sayı azalanda köhnə `bg/sc53..95` qalırdı (ep4) | `render_bgs` artıq faylları silmirdi | `prune_extra` (`def75af`) |
| 20 | 52 səhnədə 7 sikkə bankası (ep4) | subyektlər mücərrəd adlanırdı, yalnız son 8 səhnəyə baxılırdı | promptun əsas ismi (`hero`) müqayisə olunur, epizodda eyni isim ≤ 2 dəfə, LLM-ə əsas isimlər də "istifadə olunub" kimi verilir |
| 21 | ChatGPT öz-özünə küçük/pişik/dovşan çəkirdi (ep4, 7 fon) | "Pixar-style" personaj gətirir | şəkil promptunda "no animals or cartoon characters (robots are fine)" |
| 22 | Ehtiyat fon özü 3-cü "jar" oldu (ep4) | fallback seçimi istifadə olunmuş isimlərə baxmırdı | `pick_fallbacks` (`d2cc036`) |
| 23 | OpenAI krediti bitdi → publish 4×3 dəfə boş təkrar, istifadəçi JSON gördü (ep4) | `insufficient_quota` 429 ilə gəlir | dərhal "OpenAI BALANSI BITIB …" xətası, mərhələ təkrarlanmır, konsolda loqun son sətri görünür |
| 24 | Video musiqisiz çıxırdı | `Music\` boş, bat yalnız `--music` ilə ötürürdü | 4 CC BY trek + `pipeline.default_music` + `publish_pack.music_credit` |
| 25 | Personaj tərpənirdi, bölmə dəyişəndə sağ↔sol tullanırdı; istifadəçi: **"sabit dayansın, tərpənməsin, şəkli səhnəyə uyğunlaşsın"** | `Owl.tsx` nəfəs/yellənmə/danışıq/spring + `assign_positions` növbəsi; `vary_poses` pozu zorla dəyişirdi | `Owl.tsx` hərəkətsiz, poz fon keçidinin ortasında ani dəyişir; bayquş həmişə sağda; `fit_poses` LLM seçimini saxlayır; sol-kompozisiyalı köhnə fonlar güzgülənir (`flip`) |
| 26 | AI musiqi: kliplər sonda sükut, 7 dB səviyyə fərqi (proba); dövr nöqtəsində videoda 1.25 s sükut (ep5 228 s) | model klipi 0.8–2.4 s sükut / ~4 s reverb quyruğu (−21→−50 dB) ilə bitirir | hər klip: baş −50 dB, son **−35 dB** ilə kəsilir, −18 LUFS; yekun trek 0.4 s fade-out (`58b0db5` + bu commit) |
| 27 | Altyazıda qiymət bölünürdü: `$39 .99`, `$9 .99` (ep6), köhnələrdə `t -shirt`, `0 .67` | Whisper `" $39"` + `".99"` verir, `compact_words` hər tokeni ayrı söz sayırdı | boşluqsuz başlayan token əvvəlki sözə birləşir (`test_subword_tokens_are_merged_into_previous_word`) |
| 28 | İlk saniyələrdə yuxarı solda **"Hook"** yazısı + səsdə "Hook." (subtitrdə "Huggy."); istifadəçi: **"hook yazısı olmasın, digər başlıqlar qalsın"** | `spoken_titles` regex-ində `\b` əvəzinə backspace (0x08) yazılmışdı → Hook heç vaxt tanınmırdı | funksiya `timeline.py`-yə köçdü (test edilə bilir), regex `hook\b`; `test_spoken_titles.py` |
| 29 | **Təkrar kadrlar** (pricing: 55 səhnədən 10-u eyni ehtiyat fon, 6 peçenye, 3 donuz qumbarası, 2 eyni sikkə); istifadəçi: **"təkrar kadrlar olmasın, qəti"** | ehtiyat hovuz bitəndə hər dəfə `FALLBACK_BG`; eyni obyekt 2 dəfə icazəli idi; son addım yalnız yan-yana təkrarı əvəz edirdi; söz yoxlaması "stack of cookies"/"single cookie" fərqini tutmurdu | `MAX_SAME_HERO=1`, bütün təkrarlar əvəz olunur, hovuz 44 ayrı obyekt və təkrarsız (bitərsə xəta), `next_prompt` epizoddakı obyekti təkrarlamır, **CLIP şəkil yoxlaması** (`bg_dedupe.py`, 0.88) sonrakı təkrarı yenidən çəkir, qalarsa `check_bgs` keçmir (`test_no_repeats.py`) |
| 30 | **Video uşaq videosu kimi görünürdü** (karusel, oyuncaq fabrik/qatar, peçenye, "Pixar" fon, "kids educational" musiqi, "10 yaşlı uşaq" ssenari) | promptlar uşaq auditoriyası üçün yazılmışdı | seçim A: realist foto fon, yetkin (25–45) ssenari və səhnə direktoru, `CHILDISH` söz filtri, hakimdə `childish` yoxlaması, uşaq musiqi stilləri çıxarıldı (`test_adult_look.py`) |
| 31 | check_bgs yanlış "təkrar kadr" ilə 2 dəfə düşdü: saniyəölçən / kompas / qum saatı (pricing E2E-2, 2026-09-29); eyni vaxtda iki qol saatı (0.878) tutulmadı | CLIP realist fotoda mövzu/kompozisiya oxşarlığını ölçür: fərqli obyektlər 0.897–0.918, eyni sikkə 0.884 — tək hədd ayırmır | CLIP yalnız namizəd (`DUP_SIM` 0.85), hər cütü gpt-4o iki şəklə baxıb təsdiqləyir (`confirm_duplicates`, `same_scene`); cavab yoxdursa təkrar sayılır (`test_no_repeats.py`) |
| 32 | 56 fondan 22-si mövzudan kənar ehtiyat fonla bitdi (mayak, yelkənli), hər biri 3 dəfə boşuna çəkildi; resume/retry qəbul olunmuş fonları yenidən çəkirdi (pricing E2E-2) | hakim dar mövzuda yazılı/təkrar obyekt təklif edirdi (qiymət etiketi, menyu, kassa) → rədd → dərhal hovuz → hovuz fonu yenə "mismatch"; `tries` hər run-da sıfırlanırdı | hakim 3 variant verir + istifadə olunmuş obyektlər siyahısı; hamısı rədd olunsa **səbəblə** ikinci təklif (`choose_prompt`, `suggest_again`); "X with a price label" → yalnız əlavə kəsilir (`cut_text_clause`); QA-da artıq seçilmiş hovuz fonu yalnız "mismatch" üçün yenidən çəkilmir, ilk dəfə isə bir şans alır (`needs_redo`); cəhd sayı `bg_qa.json`-dan bərpa (`load_tries`). Ölçü: 10 pis səhnədən hovuza 9 → 0 |
| 33 | #32 düzəlişindən sonra hakim 429 aldı (gpt-4o TPM 30k), 429 alan fonlar **yoxlanmadan** keçdi (pricing E2E-3) | istifadə olunmuş obyekt siyahısı hər hakim sorğusuna qoşulurdu: 535 → ~1980 token × 56 paralel | siyahı yalnız `suggest_again`-də (rədd olunanlar, ardıcıl); `judge_text` < 400 simvol, `max_tokens` 300 (ölçü: in=596) |
| 34 | **Videoda hesab səhvi** (payment-fees: "100 yemək/həftə → $20 qənaət… bir ayda **eight hundred dollars**", düzgün ~$80); istifadəçi: **qəti düzəlsin, bütün videolarda** | ssenarini LLM yazır, heç bir mərhələ hesabı yoxlamırdı | `math_check.py`: rəqəmli HƏR cümlə deterministik tapılır → gpt-4o 3 müstəqil baxışla ifadəyə çevirir → iddia mətndən, nəticə Python-da (`ast`) hesablanır, operandlar mətndə olmalıdır → səhv yalnız çoxluq eyni düzgün dəyəri tapanda; yalnız həmin cümlə yenidən yazılır, düzgün dəyər yoxdursa rədd. `script_gen` yazanda/uzadanda/qısaldanda işləyir; `math_check.json` (skriptin sha256-si) olmadan `verify_script` keçmir. Real ssenaridə: 31 cümlə, 1 səhv düzəldi, 0 yalançı həyəcan (`test_number_accuracy.py`) |
| 35 | Giriş/çıxış kartında bayquş **yenə titrəyirdi**; kartlarda mövzudan asılı olmayan ümumi sprite; istifadəçi: **sabit dayansın, hər mövzuya uyğun açılış/qapanış bayquşu olsun** | `Cards.tsx` `CardOwl`: 7 px sinus `bob` + spring ilə aşağıdan gəlmə (#25 yalnız səhnə bayquşunu `Owl.tsx`-də düzəltmişdi) | `CardOwl` sabit (yalnız 8 kadr fade); `render_owls.run_cards` hər epizoda `owl/intro.png` (qolunu açıb 'başlayaq', əşyanı göstərir) + `owl/outro.png` (gözlər yumulu əl yelləyir, baş əyir); mövzu əşyası `choose_prop` ilə əvvəlcədən seçilir (ekran/yazı/personaj yox), ikisində eyni; hakimdən keçməsə köhnə sprite; en ≤ 470 px (başlığı örtmür). Render sübutu: bayquş bölgəsi kadrlar arası fərq ≤ 11 (fon zoom-u) (`test_card_owls.py`) |
| 36 | OpenAI `gpt-image-2` şəffaf fonu rədd edir (HTTP 400) → **bütün səhnə bayquşları səssizcə köhnə sprite-a düşərdi**, mərhələ yenə keçərdi | `_draw` hər LLMError-u 'bu səhnədə sprite' kimi udurdu; `render_owls` verify `[]` idi | bayquş modeli **gpt-image-2 qalır** (istifadəçi): bircins magenta (#FF00FF) fonda çəkilir, `key_out` fonu lokal silir (bütün şəkildə — şüşədən görünən fon da; yarımşəffaf kənarda fon rəngi çıxarılır, magenta qalığı 0 piksel); fon magenta/bircins deyilsə şəkil yenidən çəkilir; 'not supported for this model' xətası mərhələni dayandırır; `verify_owls`: səhnə bayquşlarının ≥ 80%-i + intro/outro kartı olmalıdır |
| 37 | İstifadəçi: video **10–12 dəq** olsun (əvvəl 8–10) | — | `MIN_SECONDS=600`, `MAX_SECONDS=720`, `DEFAULT_WORDS=1530` (ölçülmüş 1230 söz → 8.85 dəq), outline '~11 minute'; söz/TTS qapıları və final video yoxlaması yeni aralıqla işləyir |
| 38 | `scene_plan` 3 dəfə çökdü: "ehtiyat fon çatmır: 43 lazım, 39 var" (why-9-99, 2026-10-01); qiymət mövzusunda LLM hər səhnəyə "price tag $9.99" yazır → 65-dən 57-si boş fona düşürdü; "$10" rəqəmləri filtrdən keçirdi; gpt-4o artikl yazmır → hamısı atılırdı; ehtiyat fonlar mövzudan kənar (mayak) | LLM qadağaya əməl etmir + filtr boşluqları (`$`/rəqəm, labels, sticker, logo, form, card, review…; "two …", "close-up of", "side by side"); generik hovuz mövzusuzdur | `TEXT_BEARING` `$`/rəqəm + çap olunan şeylər, qiymət bəndi kəsilir, ilk hissəyə artikl, `hero` düzəlişi; SYSTEM/RETRY-də "no price tags/digits"; **`topic_pool`**: qalan səhnələr əvvəlcə mövzuya aid təkrarsız fonlar, generik hovuz yalnız sonda. Test: `test_price_topic.py`. Əlavə: hovuzdan "leather messenger bag" çıxarıldı (briefcase ilə eyni kadr, check_bgs [55,58]) |
| 39 | `make_srt` qapısı 3 dəfə düşdü: "whisper 1776 söz, skript 1646 söz" (why-9-99, 2026-10-01) — səs düzgün idi | Whisper `$9.99` → "9 dollars and 99 cents" (5 söz), `$10` → "10 dollars" (2); skript sayğacı 1 sayırdı | `stages.spoken_words`: qiymətlər tələffüz kimi sayılır (1762 vs 1776 = 0.8%). Test: `test_price_topic.py::test_srt_gate_counts_prices_as_spoken` |

| 40 | **Videoda yenə kobud hesab səhvi** (why-9-99): "three clients a month at $50 an hour … instead of earning **$600** … you'd pull in **$649.97** for four clients" — saat sayı yoxdur, rəqəmlər uyğunsuz; `math_check` [] verdi. İstifadəçi: **"birdəfəlik həll et"** | (1) fail-open: səhv yalnız 3 baxışın çoxluğu EYNİ düzgün dəyəri tapanda sayılırdı — baxışlar fərqli ifadə verdi (`49.99*4` / `3*50` / "hesab deyil") → susdu; (2) natamam hesab (giriş yoxdur) halı ümumiyyətlə tanınmırdı; (3) `4`, `12`, `3`… sabitləri istənilən uydurma ifadəni "əsaslandırırdı"; (4) generator gizli girişlə nəticə yazırdı | **`number_audit.py` — son hökm, fail-closed:** HƏR rəqəm deterministik işarələnir (hərfli marker `⟦A⟧`, sorğuda ≤ 26 — rəqəmli/ikihərfli markeri gpt-4o qarışdırırdı); rol: given / result (ifadə, operandlar rəqəmdən ƏVVƏL deyilməli) / missing; rəqəm yalnız ≥2/3 təsdiqlə keçir; şübhəli rəqəmə fokuslu 2-ci baxış (əvvəlki bölmələr + başlıq kontekstdə; başlıqdakı/əvvəl deyilmiş ≥13 rəqəmin təkrarı ok); keçməsə abzas yenidən yazılır — **bayraqsız rəqəmlər dəyişə bilməz** (real: `$9.99`→`$10` pozulması bloklandı); raundlardan sonra cümlə rəqəmsiz yazılır, olmasa silinir. Sabitlər yalnız vahid sözləri ilə (4 = həftə+ay, 12 = ay+il…). 1-ci qat (`math_check`) yalnız düzəliş ön-keçididir. Generator: "hər girişi nəticədən əvvəl de, gizli kəmiyyət yox, 49.99-u vurma". Real ölçü: why-9-99 3/3 tutuldu və düzəldi (yalnız həmin abzas dəyişdi), payment-fees köhnə $800 səhvi 3/3, yalançı həyəcan 6 run-da 1 (nəticəsi yalnız abzas yoxlaması). Test: `test_number_audit.py` (20) |
| 41 | `math_check` gpt-4o TPM 429-a 81 dəfə düşdü, 4 dəfə 3-cü cəhdə çatdı (1 cəhd qalmışdı) | backoff 1-2-4 s, API "try again in 2.27s" deyirdi | 429-da API-nin dediyi müddət + 1 s, 8 cəhd (`llm.retry_after`, `RATE_RETRIES`). Test: `test_llm.py` |
| 42 | Çıxış kartı bayquşu mövzu əşyası (qiymət etiketi) əvəzinə kitab tutdu, hakim keçirdi; yenidən çəkiləndə "price tag with a dollar amount" 3 dəfə `text` ilə yıxıldı (why-9-99, 2026-10-03) | referans sprite kitab tutur, outro "tucked under the other arm" → model kitabı köçürür; kart hakimi əşyanı yoxlamırdı; LLM əşyası yazı nəzərdə tuturdu | kart pozunda əşya "instead of the book" + "(blank, with no writing or numbers)"; kart hakiminə `missing_prop` (`judge_system(prop)`); `test_card_owls.py` (3 test) |

**Açıq qalan:** yoxdur.

---

## Növbəti dəqiq addım

**Növbəti (2026-10-02):** yeni sessiyada **eyni mövzu sıfırdan**: `Video: Why $9.99 Feels Cheaper Than $10` (köhnə epizod və çatdırılmış video silinib, `Episodes\` və `Hazir_Videolar\` boşdur). Bu, #40 `number_audit`-in ilk tam E2E-sidir: bitəndə `math_check.json` [] + ssenaridəki hər hesablı cümləni özün də yoxla. 288 test keçir.

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

---

## İcra jurnalı (ən yeni yuxarıda)

### 2026-10-02 — #40 hesab/rəqəm səhvləri fail-closed yoxlama, #41 429 gözləmə
- `number_audit.py` (yeni), `math_check` sabit qaydaları + son hökm 2-ci qatda, `script_gen` SYSTEM qaydası, `llm.retry_after`
- 288 test keçir. Real: why-9-99 ssenarisi düzəldi ("$50 an hour for one hour each … $150 … more for four clients"), ~5 dəq
- `Hazir_Videolar\` və `Episodes\why-9-99…` istifadəçi tərəfindən silindi (köhnə video səhvli idi); mövzu yeni sessiyada sıfırdan çəkiləcək

### 2026-10-01 — E2E `why-9-99-feels-cheaper-than-10` HAZIRDIR (#38, #39)
- 65 səhnə, 11.56 dəq, −14.2 LUFS, `final_video_problems=[]`, `math_check` [], `duplicates: []`, owl 65/65 + kartlar ok, sükut yoxdur
- scene_plan 3 dəfə çökdü (#38) → filtr + `topic_pool` (28 mövzu + 9 generik ehtiyat fon); check_bgs [55,58] briefcase≈messenger bag → hovuzdan çıxarıldı; make_srt yalançı qapı (#39) → `spoken_words`
- Kadrlar (giriş/çıxış kartı 6 kadr, 12 səhnə) + thumbnail vizual yoxlandı: bayquş sabit, sağda, mövzu əşyası (qiymət etiketi, yazısız); fonlarda yazı/insan/uşaqsayağı yox
- Qeyd: 9 səhnə hələ generik ehtiyat fondadır (gəmi, mayak, lampa) — mövzu hovuzu 28/37 örtdü

### 2026-09-30 — video 10–12 dəq (#37); bayquş gpt-image-2 + magenta key (#36)
- 253 test keçir; real: 'What Is Break-Even Point?' intro/outro + səhnə bayquşu gpt-image-2 ilə, fon silindi, hakimdən 1-ci cəhddə keçdi

### 2026-09-30 — sabit, mövzuya uyğun giriş/çıxış bayquşu (#35, #36)
- 247 test keçir; real API: 'What Is Cash Flow?' → əşya 'a clear glass jar filled with coins', intro/outro hakimdən 1-ci cəhddə keçdi; Remotion still renderində bayquş tərpənmir, uzun başlığı örtmür

### 2026-09-30 — hesab səhvlərinə qarşı qapı (#34)
- `math_check.py` + pipeline qapısı; 233 test keçir. Real payment-fees ssenarisində "eight hundred" → "eighty dollars", başqa dəyişiklik yox, 2 təkrar yoxlamada 0 yalançı həyəcan
- Artıq hazır `Hazir_Videolar\how-small-businesses-…` videosunda səhv qalır (yeni kod yalnız yeni videolara tətbiq olunur)

### 2026-09-29 gecə — təsdiq + yaddaş silmə mərhələsi
- Köhnə pricing run-u (`--resume why-9-99-…`, check_bgs/render_bgs prosesləri) istifadəçi istəyi ilə dayandırıldı
- Yeni: video hazır olandan sonra Claude AskUserQuestion ilə təsdiq istəyir; təsdiqdə `Projectsorget_episode.py <slug>` → `Episodes\<slug>\` + həmin epizodun `_run_*.log/.err` silinir (`Hazir_Videolar` qalır), progress.md-dən o videonun sətirləri çıxarılır (CLAUDE.md addım 6)
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
