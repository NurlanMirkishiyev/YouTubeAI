# FAZA F — Automation + Keyfiyyət (Faza 1) — Dizayn spec

**Tarix:** 2026-09-23 · **Status:** TƏSDİQLƏNİB (istifadəçi: "Faza 1 / Faza 2", "olduğu kimi təsdiq")
**Əhatə:** plan.md addım 29–36. Bu spec **Faza 1**-i (Ken Burns əsaslı tam pipeline) təsvir edir.
Faza 2 (LTX-Video I2V, `--motion ltx`) ayrıca spec ilə, Faza 1 bitdikdən sonra.

---

## 1. Məqsəd

`python run.py "Mövzu"` → ≥ 10 dəqiqəlik, YouTube-a yükləməyə hazır video + `youtube/` paketi.
İnsan müdaxiləsi yalnız sonda: videonu izləyib yükləmək.

### Qəbul meyarları (ölçülə bilən)
| # | Meyar | Yoxlama |
|---|---|---|
| A1 | Narration ≥ 600 s | `ffprobe narration.wav` |
| A2 | Video 1920×1080@30, H.264 High, yuv420p, L4.1 | `ffprobe` |
| A3 | Audio AAC 48 kHz **stereo**, inteqrasiya olunmuş loudness −14 ±1 LUFS | `ffmpeg -af ebur128` |
| A4 | A/V drift < 0.2 s (video uzunluğu − audio uzunluğu) | `ffprobe` |
| A5 | Sprite heç vaxt böyüdülmür (ekran hündürlüyü ≤ HD sprite hündürlüyü) | kod assert |
| A6 | Fon Ken Burns-a ≥ 3840×2160 mənbədən girir (upscale edilmiş) | kod assert |
| A7 | `youtube/` qovluğu: `title.txt`, `description.txt` (chapters ilə), `tags.txt`, `thumbnail.png` 1280×720 | fayl yoxlaması |
| A8 | Tam dekod testi xətasız (`ffmpeg -v error -i x.mp4 -f null -`) | exit code 0, boş stderr |
| A9 | `--resume <slug>` bitmiş mərhələləri təkrarlamır | state.json + log |

---

## 2. Arxitektura

### 2.1 Orchestrator
- **Giriş:** `C:\YouTubeAI\run.py` (nazik wrapper) → `Projects\pipeline.py`.
- CLI: `run.py "Mövzu" [--words 2150] [--music PATH] [--resume SLUG] [--from STAGE] [--motion kenburns]`
- Mövcud skriptlər **subprocess** kimi, **öz venv python-u** ilə çağırılır (import yox — venv-lər fərqlidir).
- `Episodes/<slug>/state.json`:
  ```json
  {"topic": "...", "slug": "...", "created": "ISO", "stages": {
     "script_gen": {"status": "done|failed|pending", "started": "ISO", "finished": "ISO", "error": null}, ...}}
  ```
  Yazılış **atomik**dir (tmp fayl + `os.replace`).
- Mərhələ "bitib" sayılır ancaq **resume açarı** fayl sistemində mövcuddursa **və** mərhələ yoxlaması keçirsə.
  (state.json yalan desə belə, fayl sistemi həqiqətdir.)

### 2.2 Mərhələlər
| # | Mərhələ | Venv | Çağırış | Resume açarı | Sonrakı yoxlama |
|---|---|---|---|---|---|
| 1 | script_gen | Projects (sistem python) | `script_gen.py TOPIC --slug --words` | `script.md` | söz sayı ≥ 0.95 × hədəf |
| 2 | scene_plan | sistem | `scene_plan.py DIR` | `scenes.json` | hər səhnədə narration + bg_prompt |
| 3 | comfy_up | ComfyUI\.venv | `main.py` birbaşa (Git Bash `.bat` işləmir) | `GET :8188/system_stats` 200 | 120 s timeout |
| 4 | render_bgs | sistem | `render_bgs.py DIR` | `bg/scNN.png` sayı = səhnə sayı | ölçü ≥ 1344×768 |
| 5 | upscale_bgs | ComfyUI (4x-UltraSharp workflow) | yeni `_workflows/upscale_4x_api.json` | `bg_hd/scNN.png` sayı | ölçü ≥ 3840×2160 |
| 6 | tts_gen | TTS\.venv | `tts_gen.py DIR` | `narration.wav` | **≥ 600 s** (bax §4) |
| 7 | make_srt | Whisper\.venv | `make_srt.py narration.wav DIR/narration` | `narration.srt` | söz sayı ≈ skript ±5% |
| 8 | build_episode | sistem | `build_episode.py DIR --srt --music` | `<slug>.mp4` | A2–A4, A8 |
| 9 | publish | sistem | yeni `publish_pack.py DIR` | `youtube/thumbnail.png` | A7 |

ComfyUI 3-cü mərhələdə pipeline tərəfindən qaldırılıbsa, 5-dən sonra **dayandırılır** (TTS/Whisper-ə VRAM azad olsun).
Əgər artıq işləyirdisə, toxunulmur.

### 2.3 Xəta davranışı
- Hər subprocess: stdout/stderr → `Episodes/<slug>/logs/<stage>.log`.
- Exit ≠ 0 və ya yoxlama keçmir → state `failed`, `error` sahəsinə qısa səbəb, pipeline **dayanır**, exit 1.
- Heç bir mərhələ səssizcə ötürülmür.

---

## 3. Keyfiyyət düzəlişləri

### 3.1 Sprite (personaj)
- **Offline, bir dəfəlik:** Real-ESRGAN 4× → `Character/ELI5_Owl/sprites_hd/<ad>.png` (200×235 → ~800×940).
  Alpha kanalı ayrıca upscale olunur (lanczos), RGB ESRGAN ilə; sonra 1 px alpha erode (ağ halo gedir).
  Skript: `Projects/sprites/upscale_sprites.py`. Böyük character sheet gələndə `make_sprites.py` → eyni qovluq.
- Ekran hündürlüyü default **0.70 → 0.42** (454 px) — kiçiltmə, böyütmə yox (A5).
- Mövqe: `left` / `right` künc (center yalnız Hook/Outro), margin 90 px.
- **Kontakt kölgəsi:** ayaq altında yumşaq qara ellips (en = sprite eni × 0.7, blur σ≈18, opacity 0.35).
- Bob animasiyası saxlanılır, amplitud 7 → 4 px.

### 3.2 Fon
- SDXL 1344×768 → 4x-UltraSharp → **5376×3072** → Ken Burns bu mənbədən kəsir (A6).
- `models/upscale_models/4x-UltraSharp.pth` yüklənməlidir (**hazırda yoxdur**).
- Yumşaq vignette (kənarlar −12% parlaqlıq) — sprite-ı fondan ayırır.

### 3.3 Hərəkət (Ken Burns)
- Səhnə indeksinə görə deterministik 4 hərəkət növbələşir: zoom-in mərkəz, zoom-out, pan L→R + zoom, pan R→L + zoom.
- Zoom diapazonu 1.00–1.10, easing (smoothstep) — sabit sürət yox.

### 3.4 Keçidlər
- Növbə ilə: `fade`, `slideleft`, `wipeleft`, `dissolve`; 0.5 s. Bölmə dəyişəndə həmişə `fade`.
- `XFADE` sabiti eyni qalır → `build_episode.py` müddət kompensasiyası dəyişmir.

### 3.5 Subtitr
- Font: Montserrat SemiBold (`Assets/fonts/`, yoxdursa Segoe UI Semibold fallback — log-da xəbərdarlıq).
- ASS style: FontSize 15 (1080p-də ~46 px), ağ, `BorderStyle=3` (yarımşəffaf qara qutu, `BackColour=&H80000000`),
  maks 2 sətir, `MarginV=70`, alignment 2 (aşağı-mərkəz). Sprite zonası ilə üst-üstə düşmür (sprite künc, subtitr mərkəz).

### 3.6 Struktur elementləri
- **Intro 4 s:** başlıq kartı (mövzu adı, bayquş `front`, fade-in). Narration 4 s sürüşür.
- **Lower-third:** hər yeni bölmənin ilk səhnəsində bölmə adı, 3 s, sol-aşağı.
- **Outro 6 s:** "Subscribe" kartı + bayquş `happy`. Narration bitəndən sonra.
- Intro/outro PNG kartları Pillow ilə yaradılır (`Projects/cards.py`), montage-a adi səhnə kimi verilir (sprite `-`).

### 3.7 Audio
- Narration 24 kHz mono → **48 kHz stereo** (`aresample=48000`, `pan=stereo|c0=c0|c1=c0`).
- Musiqi: `sidechaincompress` ilə ducking (narration danışanda musiqi ~ −18 dB, pauzada −10 dB).
- Son master: `loudnorm=I=-14:TP=-1.5:LRA=11` (iki keçidli — əvvəl ölçmə, sonra tətbiq) (A3).
- Musiqi verilməyibsə: musiqisiz davam, log-da xəbərdarlıq (placeholder ton **istifadə olunmur**).

---

## 4. Uzunluq ≥ 10 dəq (sərt qayda)
- Default `--words 2150` (199 wpm → ~10.8 dəq).
- 6-cı mərhələdən sonra: `narration < 600 s` →
  1. `script_gen.py --extend N` (yeni rejim): çatışmayan söz sayı qədər **yeni bölmə** yazılır
     (mövcud bölmələrdən fərqli analogiya sahəsi ilə), Outro-dan əvvələ daxil edilir;
  2. `scene_plan.py --force`, render (yalnız yeni səhnələr), TTS (yalnız yeni səhnələr), yenidən yoxlama.
- Maks **2 cəhd**; yenə < 600 s → `failed`, səbəb yazılır.

---

## 5. YouTube paketi (`publish_pack.py`)
- `title.txt` — LLM, ≤ 70 simvol, 3 variant (ilki default).
- `description.txt` — 2–3 cümləlik xülasə + **chapters** (`00:00 Intro`, hər bölmənin real başlama vaxtı
  scenes.json müddətlərindən + intro sürüşməsi) + hashtag-lar. İlk chapter mütləq `00:00`.
- `tags.txt` — 10–15 teq, cəmi ≤ 500 simvol.
- `thumbnail.png` — 1280×720: ən parlaq/kontrastlı fon + bayquş `confident` böyük + 3–5 sözlük başlıq (Montserrat ExtraBold, qalın kontur).

---

## 6. Dəyişən / yeni fayllar

| Fayl | Növ | Qeyd |
|---|---|---|
| `run.py` | yeni | wrapper |
| `Projects/pipeline.py` | yeni | orchestrator, state, yoxlamalar |
| `Projects/checks.py` | yeni | ffprobe/ebur128 əsaslı yoxlama funksiyaları |
| `Projects/sprites/upscale_sprites.py` | yeni | bir dəfəlik HD sprite |
| `Projects/upscale_bgs.py` | yeni | ComfyUI 4x workflow çağırışı |
| `Projects/_workflows/upscale_4x_api.json` | yeni | |
| `Projects/cards.py` | yeni | intro/outro/lower-third PNG |
| `Projects/publish_pack.py` | yeni | YouTube paketi |
| `Projects/_ffmpeg/montage.py` | **dəyişir** | kölgə, hərəkət növləri, keçidlər, subtitr stili, audio master. Köhnə CLI geriyə uyğun qalır. |
| `Projects/build_episode.py` | **dəyişir** | `bg_hd/` üstünlük, intro/outro, lower-third tokenləri |
| `Projects/script_gen.py` | **dəyişir** | `--extend N` rejimi, default `--words 2150` |

Qeyd: "mövcud skriptlər dəyişmir" prinsipi **orchestrator** üçündür (onları subprocess kimi çağırır);
keyfiyyət düzəlişləri isə məhz render skriptlərinin içində olmalıdır.

---

## 7. Test strategiyası
- **Unit (pytest, sistem python):** state.json oxu/yaz/resume məntiqi, chapters vaxt hesabı, Ken Burns ifadə generatoru,
  keçid növbəsi, sprite ölçü assert-i, `--extend` söz hesabı, filter_complex string qurulması (snapshot).
- **İnteqrasiya:** 3 səhnəlik mini epizod (`--words 300`, uzunluq qaydası `--min-seconds 30` ilə yumşaldılır) → A2–A4, A7, A8.
- **E2E:** real mövzu ilə tam qaçış, qəbul meyarları A1–A9.
- **Vizual:** 3 kadr çıxarılır (`f030`, `f120`, `f300`) və istifadəçiyə göstərilir — sprite kəskinliyi, kölgə, subtitr.

---

## 8. Risklər
- 4x-UltraSharp + Real-ESRGAN modelləri yüklənməlidir (~70 MB) — yükləmə mənbəyi planda göstəriləcək.
- 5376×3072 × 30 səhnə diskdə ~1–1.5 GB/epizod (PNG). Qəbul edilir; `bg_hd/` sonradan silinə bilər.
- zoompan 5K mənbədə yavaşdır — render müddəti ölçüləcək; > 30 dəq olarsa mənbə 3840×2160-ə endirilir.
- Montserrat fontu sistemdə yoxdursa — `Assets/fonts/`-a qoyulur (OFL lisenziya).
- Real fon musiqisi istifadəçidən gözlənilir (`Music/` boşdur).

## 9. Faza 2 (bu spec-in xaricində)
`--motion ltx`: LTX-Video 2B fp8 I2V, əvvəlcə 1 səhnədə test, 8 GB VRAM-da `--lowvram`; klip ~5 s → ping-pong loop.
Ayrıca spec + plan.
