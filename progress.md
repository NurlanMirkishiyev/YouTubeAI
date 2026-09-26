# progress.md — YouTubeAI icra jurnalı

> **Bu fayl nə üçündür:** hər dəfə işə davam edəndə Claude əvvəlcə bu faylı oxuyur və
> son icranın harada dayandığını bilir. **Hər mərhələ tamamlananda bu fayl yenilənir.**
> Qayda: "Cari vəziyyət" və "Növbəti dəqiq addım" bölmələri həmişə aktual olmalıdır;
> tamamlanan iş "İcra jurnalı"na bir sətir kimi əlavə edilir (ən yenisi yuxarıda).

**Layihə:** `C:\YouTubeAI` — həftədə 2 ədəd ~10 dəq "ELI5 Business" YouTube videosu üçün lokal pipeline
**Master plan:** `plan.md` (addım 01–36)
**Son yenilənmə:** 2026-09-26

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

**İstifadə:** iş masasında **"ELI5 Yeni Video"** qısayolu = `Yeni_Video.bat` (iki klik → mövzu yaz; `resume` yazsan
yarımçıq epizod davam edir) və ya `python run.py "Mövzu"` (istənilən python; özünü `Projects\.venv`-ə keçirir) →
`Episodes\<slug>\<slug>.mp4` + `Episodes\<slug>\youtube\`. Yarımçıq qalsa: `python run.py --resume <slug>`.
**Bütün hazır videolar bir yerdə:** `C:\YouTubeAI\Hazir_Videolar\` (iş masasında "ELI5 Hazir Videolar"):
`<slug>.mp4` (hardlink, əlavə yer tutmur) + `<slug>.png` (thumbnail) + `<slug>.txt` (başlıq/description/tags) —
pipeline sonda `deliver()` ilə avtomatik yazır.
Musiqi: `--music` verilməsə `Music\*.mp3`-dən slug-a görə trek seçilir (sha1 → epizodlar arasında növbə, resume eyni trek).
4 trek: Kevin MacLeod (incompetech), **CC BY 4.0** → `Music\credits.json` üzrə istinad description.txt-ə avtomatik yazılır.
Yeni trek əlavə edəndə: mp3-ü `Music\`-ə qoy; CC BY-dırsa `credits.json`-a `"fayl.mp3": "Başlıq"` sətri əlavə et.

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

**Açıq qalan:** yoxdur.

---

## Növbəti dəqiq addım

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
2. İndi: istifadəçi yeni mövzu verir → `python run.py "Mövzu"` (~45 dəq: skript 1 dəq, ~50 ChatGPT şəkli ~10 dəq
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

### 2026-09-27 — FAZA H: musiqi + sabit personaj, cash flow tamamlandı
- Kredit əlavə edildi → `what-is-cash-flow` publish paketi hazırlandı
- Musiqi: FreePD bağlanıb → incompetech (Kevin MacLeod, CC BY 4.0) 4 trek; slug-a görə növbə; description-a istinad
- Personaj: `Owl.tsx` hərəkətsiz (nəfəs/yellənmə/danışıq/spring/tərəf sürüşməsi silindi), həmişə sağda;
  cross-fade ikiqat bayquş göstərdi (kadr yoxlaması) → poz fon keçidinin 7-ci kadrında ani dəyişir
- Pozlar: `vary_poses` (zorla növbə) → `fit_poses` (LLM-in səhnəyə uyğun seçimi), prompt "pick the pose that best fits"
- Köhnə sol-kompozisiyalı fonlar `flip` ilə güzgülənir (fonlarda yazı yoxdur → güzgü təhlükəsizdir)
- İş masasına "ELI5 Yeni Video" qısayolu; bat musiqini pipeline-a buraxır. 127 test.
- İstifadəçi: "köhnə videoları sil, yeni videolar bir qovluğa" → 2 köhnə epizod silindi; `deliver()` →
  `Hazir_Videolar\` (mp4 hardlink + png + txt), iş masasında "ELI5 Hazir Videolar". 129 test.

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
