# progress.md — YouTubeAI icra jurnalı

> **Bu fayl nə üçündür:** hər dəfə işə davam edəndə Claude əvvəlcə bu faylı oxuyur və
> son icranın harada dayandığını bilir. **Hər mərhələ tamamlananda bu fayl yenilənir.**
> Qayda: "Cari vəziyyət" və "Növbəti dəqiq addım" bölmələri həmişə aktual olmalıdır;
> tamamlanan iş "İcra jurnalı"na bir sətir kimi əlavə edilir (ən yenisi yuxarıda).

**Layihə:** `C:\YouTubeAI` — həftədə 2 ədəd ~10 dəq "ELI5 Business" YouTube videosu üçün lokal pipeline
**Master plan:** `plan.md` (addım 01–36)
**Son yenilənmə:** 2026-09-23

---

## Cari vəziyyət

| Faza | Vəziyyət |
|---|---|
| FAZA A–E (addım 01–28) | **TAMAM** — ilk epizod çıxdı və oynadılır |
| FAZA F (addım 29–36, automation) | **DİZAYN TƏSDİQ GÖZLƏYİR** — kod yazılmayıb |

**İlk epizod:** `Episodes/trademark-copyright-patent/trademark-copyright-patent.mp4`
1550 söz · 29 səhnə · 7.97 dəq · 1920×1080@30 · H.264 High / yuv420p / L4.1 · AAC 24 kHz mono · 137 MB
Tam dekod testi xətasız. Oynadılması istifadəçi tərəfindən təsdiqlənib.

---

## Növbəti dəqiq addım

**FAZA F dizaynı TƏSDİQLƏNDİ (2026-09-23):** Faza 1 / Faza 2 bölgüsü, dizayn dəyişməz qəbul edildi.

1. [x] Spec: `docs/superpowers/specs/2026-09-23-faza-f-automation-design.md` — istifadəçi təsdiqlədi
2. [x] Plan: `docs/superpowers/plans/2026-09-23-faza-f-faza1-automation.md` — Task 0–16
3. [ ] **İcra üsulu seçimi gözlənilir** (Subagent-Driven / Inline) → sonra Task 0-dan başla
   - Task 10 Step 6-da **istifadəçinin vizual təsdiqi** mütləqdir (kadrlar köhnə f120 ilə müqayisə)
   - Task 16-da istifadəçidən musiqi treki soruşulur

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
