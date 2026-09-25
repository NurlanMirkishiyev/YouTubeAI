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
| FAZA F / Faza 1 (automation + keyfiyyət) | **Task 0–16 icra olundu, 90 test keçir** — E2E işlədi, amma **fonlarda yazı problemi açıqdır** (aşağıya bax) |
| FAZA F / Faza 2 (LTX-Video) | başlanmayıb — ayrıca spec lazımdır |

**İstifadə:** `python run.py "Mövzu"` (istənilən python; özünü `Projects\.venv`-ə keçirir) →
`Episodes\<slug>\<slug>.mp4` + `Episodes\<slug>\youtube\`. Yarımçıq qalsa: `python run.py --resume <slug>`.
Musiqi: `--music Music\<trek>.mp3` (verilməsə musiqisiz).

**Ölçülmüş (2026-09-23):** fon upscale 15 s/fon · sprite HD 8 ədəd 71 s · 8.14 dəq epizodun montajı ~7 dəq ·
köhnə epizodun FAZA F versiyası (`faza1_test.mp4`) bütün A2/A3/A4/A8 yoxlamalarından keçdi.

**İlk epizod:** `Episodes/trademark-copyright-patent/trademark-copyright-patent.mp4`
1550 söz · 29 səhnə · 7.97 dəq · 1920×1080@30 · H.264 High / yuv420p / L4.1 · AAC 24 kHz mono · 137 MB
Tam dekod testi xətasız. Oynadılması istifadəçi tərəfindən təsdiqlənib.

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
6. [~] **E2E-dən sonra vizual düzəliş (DAVAM EDİR — sessiya burada dayandı, 2026-09-24):**
   - Tapıldı: 300 s-də fon "game interface" → mənasız yazı; thumbnail-da bust bayquşun kəsik tərəfi içəri baxırdı
   - Düzəldildi, commit `5d58498`: `scene_plan.clean_bg_prompt` (yazı daşıyan hissələri atır, `TEXT_BEARING`
     regex, `FALLBACK_BG`) + `cards.paste_sprite` (bust sağ-alt kənara yapışır, kəsik tərəf çölə flip)
   - Epizodun scenes.json-u `clean_bg_prompt` ilə yeniləndi; bg/, bg_hd/, cards/, youtube/, mp4 silindi;
     `python run.py --resume how-credit-cards-actually-work` arxa planda işə salındı (render_bgs 33/37-də idi)
   - **YENİ AÇIQ PROBLEM:** `bg/sc16.png` — kredit kartının yaxın planı, üstündə mənasız yazı
     ("Pirxirt", "COOVAUDRYOND", rəqəmlər). Filter "credit card"-ı tutmur, bu mövzuda kart hər yerdədir.

   - **2026-09-25 HƏLL EDİLDİ (commit `f7ce99b`):** 37 fon yoxlandı → 8-də aydın gibberish (sc12/14/16/20/21/24/28/34).
     Eyni seed ilə 15 probe render: güclü negativ prompt **heç nə vermir**; yazını obyektin adı gətirir.
     `clean_bg_prompt`: payment card → `BLANK_CARD`, pizza box → tray, calendar/calculator/bills/card reader/…
     atılır, "showing/indicating …" quyruqları kəsilir. 95 test. 32 səhnənin promptu dəyişdi, fonları silindi,
     `python run.py --resume how-credit-cards-actually-work` işə salındı (2026-09-25)

   - **2026-09-25 TAMAM:** yenidən qurma 11.19 dəq HAZIRDIR (19:13→19:42, ~30 dəq), 37 fonun hamısı yazısız,
     kadrlar 30/120/300/500 s + thumbnail vizual yoxlandı — qüsur yoxdur. **Faza 1 bağlandı.**

**FAZA G — keyfiyyət düzəlişi (2026-09-26, DAVAM EDİR).** İstifadəçinin 5 şikayəti + "Remotion istifadə et":
1. Səs yazıları oxumur → intro/bölmə başlığı/outro indi səsləndirilir (`tts_gen`, commit dddd4f3)
2. Şəkillər təkrar → səhnə 14–32 söz (~7 s, ~98 şəkil), LLM hissə-hissə + son mövzular, təkrar yenidən soruşulur,
   fallback pool təkrarsız (commit 6571652)
3. Şəkillər məntiqsiz/qarışıq → bir əsas obyekt, max 3 prompt hissəsi, SDXL "medium shot, single focal subject"
4. Animasiya dona-dona → ölçüldü: zoompan 73/89 kadr dayanıb sıçrayırdı; Remotion CSS transform 0.005 px təcil
   (`Remotion/`, `Projects/remotion_build.py`, commit 0cfa5cb, e8c785c, b5d16b4)
5. Personaj donuq/səliqəsiz → yalnız tam bədən pozları, eyni ölçü/yer xətti, spring giriş, nəfəs, səsə uyğun tərpənmə,
   poz cross-fade, ardıcıl eyni poz yox
**İndi:** `run.py --resume what-is-business-automation --from scene_plan` arxa planda (log: scratchpad `ep2v3.log`).
Sonra: fon kontakt vərəqi, kadr + hamarlıq yoxlaması, istifadəçiyə hesabat.

---

## FAZA F dizaynı (təsdiq gözləyir)

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

**Uzunluq ≥ 10 dəq (sərt qayda)**
`--words 2150` (199 wpm → 10.8 dəq). Addım 5-dən sonra yoxlama: narration < 600 s olsa,
avtomatik əlavə bölmə yazdırılır və TTS təkrarlanır.

**LTX-Video — mərhələli**
- **Faza 1** (əvvəl): yuxarıdakı hər şey, `--motion kenburns` default → ~50–60 dəq-ə hazır video
- **Faza 2** (sonra): `--motion ltx` bayrağı, əvvəlcə **1 səhnədə test**

Səbəb (aşağıdakı "Risklər"ə bax): 8 GB VRAM sərhəddədir, LTX bütün pipeline-ı bloklamamalıdır.

---

## Risklər / açıq suallar

- **GPU = RTX 4060 Laptop, 8 GB VRAM.** LTX 2B fp8 + T5-XXL fp8 ≈ 8–10 GB → sərhəddə.
  `--lowvram` ilə işləyə bilər, **zəmanət yoxdur**. Birdəfəlik ~10–12 GB yükləmə.
  Səhnə başına ~2–4 dəq × 30 = **+60–120 dəq/epizod** (təxmin, ölçülməyib).
- **LTX klip uzunluğu ~5 s**, səhnələr 12–30 s → ping-pong loop ilə doldurulmalıdır.
- `Music/` boşdur — yalnız `_placeholder_tone.wav`. İstifadəçi royalty-free trek verməlidir.
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

### 2026-09-25/26 — İstehsal: `what-is-business-automation`
- 2402 söz, **12.55 dəq**, 1920×1080 yuv420p, AAC 48 kHz stereo, 192 MB; ilk keçid ~38 dəq
- Fon yoxlamasında sc35-də cizgi oğlan ("a basketball player") → commit `27fc2d4`: insan isimləri
  promptdan atılır (`HUMAN`, "robot chef" saxlanır), 7 səhnə yenidən çəkildi, `--resume` ~19 dəq
- Dərs: negativ prompt nə yazını, nə insanı saxlayır — **ismi promptdan çıxarmaq** yeganə işləyən yoldur

### 2026-09-23/24 — Task 15/16 + vizual düzəlişlər
- `_integ-compound` 6.27 dəq, E2E `how-credit-cards-actually-work` 11.19 dəq — hər iki HAZIRDIR
- Kadr yoxlamasında 2 qüsur → commit `5d58498` (yazılı fon promptu filtri, bust thumbnail flip), 90 test
- Yenidən qurmada 3-cü qüsur: kredit kartı yaxın planda mənasız yazı (sc16) — **açıqdır**
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
- Dizayn təqdim edildi → **təsdiq gözlənilir**
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
