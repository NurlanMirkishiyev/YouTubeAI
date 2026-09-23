# ELI5 Business --- Lokal AI YouTube Video İstehsal Planı

## Məqsəd

Həftədə **2 ədəd**, hər biri təxminən **10 dəqiqəlik**, ELI5 Business
bayquş personajının istifadə olunduğu YouTube videolarını mümkün qədər
**lokal, open-source, avtomatlaşdırılmış və aşağı xərclə** hazırlayan
sistem qurmaq.

### Mövcud avadanlıq

-   Lenovo Legion Slim 5 16AHP9
-   GPU: NVIDIA, 8 GB VRAM
-   RAM: 32 GB
-   SSD: 1 TB
-   Hədəf çıxış: 1920×1080, 30 FPS, MP4
-   İstehsal tempi: həftədə 2 video

------------------------------------------------------------------------

## Yekun sistem

``` text
Video mövzusu
      ↓
Script generator
      ↓
Scene Planner
      ↓
Vizual promptlar
      ↓
ComfyUI
 ┌────┼──────────────┐
 ↓    ↓              ↓
Owl   Illustration   Diagram
 ↓
Qısa Image-to-Video klipləri
      ↓
Kokoro TTS
      ↓
Whisper
      ↓
FFmpeg
      ↓
Hazır 1080p YouTube videosu
```

------------------------------------------------------------------------

# Mərhələ 1 --- İş mühitinin hazırlanması

> Qeyd (2026-09-22): D: diski mövcud olmadığı üçün bütün quraşdırma `C:\YouTubeAI` altındadır.

## 1.1 Qovluq strukturu

``` text
C:\YouTubeAI\
├── ComfyUI\
├── Models\
├── Character\
│   └── ELI5_Owl\
├── TTS\
├── Whisper\
├── Projects\
├── Music\
├── Temp\
└── Output\
```

## 1.2 Quraşdırılacaq əsas komponentlər

-   [x] NVIDIA driver-lərin yoxlanılması / yenilənməsi
-   [x] Python
-   [x] Git
-   [x] FFmpeg
-   [x] ComfyUI
-   [x] ComfyUI Manager
-   [x] 8 GB VRAM-a uyğun image model
-   [x] IP-Adapter/reference workflow
-   [x] Kokoro TTS
-   [x] Whisper
-   [ ] Son mərhələdə Wan/LTX image-to-video workflow

### Nəticə

Kompüter lokal AI video istehsalına hazır olacaq.

------------------------------------------------------------------------

# Mərhələ 2 --- ELI5 Owl Master Character

Göndərilmiş character sheet əsas referans kimi istifadə ediləcək.

Qorunmalı xüsusiyyətlər:

-   qəhvəyi/ağ bayquş görünüşü
-   böyük qara dairəvi eynək
-   böyük ifadəli gözlər
-   tünd göy biznes kostyumu
-   ağ köynək
-   sarı qalstuk
-   sevimli 3D cartoon görünüşü
-   eyni bədən proporsiyaları
-   eyni rəng palitrası

## 2.1 İlk üsul

Əvvəlcə **IP-Adapter/reference-image** yanaşması test ediləcək.

## 2.2 Character consistency testi

Eyni personaj aşağıdakı minimum 10 səhnədə yaradılacaq:

1.  Lövhədə qrafik izah edir
2.  Laptop qarşısında işləyir
3.  Müqavilə tutur
4.  Düşünür
5.  Sevinir
6.  Auditoriyaya dərs keçir
7.  Kalkulyator istifadə edir
8.  Biznes binasının qarşısında dayanır
9.  AI diaqramını göstərir
10. İki biznes sahibinə mövzu izah edir

### Qərar nöqtəsi

Əgər görünüş kifayət qədər stabil qalırsa:

**IP-Adapter workflow saxlanılır.**

Əgər personaj nəzərəçarpacaq dərəcədə dəyişirsə:

**ELI5 Owl üçün xüsusi LoRA hazırlanır.**

### QƏRAR (2026-09-22) — Sprite yanaşması

IP-Adapter nəticələri istifadəçi tərəfindən rədd edildi (personaj təhrif olunur: sarı iris,
ağ üz ləkəsi yox, qanad/əl fərqi). 100% uyğunluq tələbi → personaj **generativ çəkilmir**,
character sheet-dən kəsilmiş **sprite-lər** istifadə olunur:

- `Projects/sprites/make_sprites.py` → `Character/ELI5_Owl/sprites/{front,three_q,side,happy,thinking,confident,chart,box}.png`
  (deterministik near-white flood-fill maska, AI yoxdur; `Projects/.venv` — rembg artıq lazım deyil)
- Fonlar personajsız SDXL ilə: `Projects/_workflows/bg_sdxl_api.json` (Workflow B)
- `montage.py --sprites <ad>[@left|right|center][:hündürlük]` — sprite fon üstündə sabit, ±7 px "bob"
- Test: `Temp/sprite_test.mp4`
- Məhdudiyyət: 8 sabit poza; yeni poza üçün yeni sheet lazımdır. LoRA (addım 11) ləğv edilir.

------------------------------------------------------------------------

# Mərhələ 3 --- Character LoRA (yalnız ehtiyac olarsa)

Dataset üçün personajın:

-   front
-   3/4
-   side
-   müxtəlif mimikalar
-   müxtəlif əl/qanad pozaları
-   müxtəlif fəaliyyətlər

üzrə təmiz referansları hazırlanacaq.

Trigger nümunəsi:

``` text
ELI5OWL
```

Prompt nümunəsi:

``` text
ELI5OWL standing beside a business growth chart,
friendly teaching expression,
navy business suit,
yellow tie,
3D educational animation style
```

### Məqsəd

Videodan-videoya mümkün qədər eyni kanal personajını qorumaq.

------------------------------------------------------------------------

# Mərhələ 4 --- Video strukturunun standartlaşdırılması

Bir video:

-   təxminən 10 dəqiqə
-   təxminən 1,300--1,600 söz narration
-   təxminən 25--35 əsas səhnə
-   hər 5--8 saniyədə vizual dəyişiklik

## Vizual paylanma üçün başlanğıc hədəfi

  Vizual növü                       Təxmini pay
  ------------------------------- -------------
  AI şəkillər + pan/zoom/motion         50--60%
  ELI5 Owl səhnələri                    20--30%
  Diaqram/qrafik/text                   10--15%
  Generativ AI video                     5--10%

10 dəqiqənin hamısı generativ AI video kimi hazırlanmayacaq.

------------------------------------------------------------------------

# Mərhələ 5 --- Script Generator

İstifadəçi yalnız mövzunu daxil edir.

Nümunə:

``` text
Trademark vs Copyright vs Patent
```

Sistem hazırlayır:

-   Hook
-   Giriş
-   Sadə ELI5 izahı
-   Real biznes nümunələri
-   Müqayisələr
-   Yekun
-   CTA

Hədəf narration: təxminən **1,300--1,600 söz**.

------------------------------------------------------------------------

# Mərhələ 6 --- Scene Planner

Script avtomatik strukturlaşdırılır.

Nümunə:

``` text
SCENE 07

Duration: 20 sec

Narration:
Copyright protects original creative works...

Visual Type:
CHARACTER

Character:
ELI5OWL

Expression:
Explaining

Visual Prompt:
ELI5OWL standing beside a board showing
a book, music note, photograph and video icon,
friendly educational 3D environment.

Motion:
Slow camera push-in.
```

Vizual növləri:

-   CHARACTER
-   ILLUSTRATION
-   DIAGRAM
-   TEXT
-   IMAGE_TO_VIDEO

------------------------------------------------------------------------

# Mərhələ 7 --- ComfyUI Vizual Sistemi

Üç əsas workflow hazırlanacaq.

## Workflow A --- Character

``` text
ELI5 Owl Reference
        ↓
IP-Adapter / Character conditioning
        ↓
Scene Prompt
        ↓
Image Model
        ↓
Consistent Owl Scene
```

## Workflow B --- Illustration

Personajsız biznes, hüquq, maliyyə, AI və digər izahlı vizuallar.

## Workflow C --- Image-to-Video

Yalnız seçilmiş səhnələr üçün qısa hərəkətli kliplər.

8 GB VRAM səbəbilə VRAM-a qənaət edən / quantized workflow seçiləcək.

------------------------------------------------------------------------

# Mərhələ 8 --- Səsləndirmə

**Kokoro TTS** istifadə ediləcək.

Bir əsas narrator səsi seçilib bütün videolarda qorunacaq.

Məqsəd:

``` text
Eyni personaj
+
Eyni narrator
+
Eyni vizual dil
=
ELI5 Business kanal identikliyi
```

------------------------------------------------------------------------

# Mərhələ 9 --- Subtitle və timing

Hazır narration audio **Whisper** ilə işlənəcək.

Çıxış:

-   timestamp-lər
-   subtitle
-   lazım olduqda söz/cümlə səviyyəsində timing

Subtitle son montaja əlavə ediləcək.

------------------------------------------------------------------------

# Mərhələ 10 --- FFmpeg montaj sistemi

FFmpeg aşağıdakıları birləşdirəcək:

-   AI şəkillər
-   AI video kliplər
-   pan/zoom effektləri
-   keçidlər
-   narrator
-   background music
-   subtitles
-   kanal elementləri

Çıxış:

``` text
1920×1080
30 FPS
H.264 MP4
YouTube-ready
```

------------------------------------------------------------------------

# Mərhələ 11 --- Avtomatlaşdırma

İlk 2--3 test video keyfiyyətə nəzarət üçün yarı-avtomatik hazırlanacaq.

Workflow stabilləşdikdən sonra Python ilə vahid idarəetmə sistemi
qurulacaq.

Hədəf interfeys:

``` text
┌──────────────────────────────────────┐
│       ELI5 BUSINESS AI STUDIO        │
│                                      │
│ Topic                                │
│ [ Trademark vs Copyright vs Patent ] │
│                                      │
│ Duration: [ 10 Minutes ]             │
│ Character: [ ELI5 Owl ✓ ]            │
│ Voice: [ ELI5 Narrator ]             │
│ Resolution: [ 1080p ]                │
│                                      │
│          [ GENERATE VIDEO ]          │
└──────────────────────────────────────┘
```

------------------------------------------------------------------------

# Mərhələ 12 --- Keyfiyyət yoxlaması

Avtomatik renderdən sonra yoxlanacaq:

-   [ ] Personaj consistency
-   [ ] Səhv əllər/qanadlar/obyektlər
-   [ ] Yazı səhvləri
-   [ ] Narration səhvləri
-   [ ] Subtitle timing
-   [ ] Səhnələrin narration ilə uyğunluğu
-   [ ] Musiqinin səs səviyyəsi
-   [ ] Vizual dəyişmə tempi
-   [ ] 1080p render keyfiyyəti
-   [ ] Copyright/licensing uyğunluğu

YouTube upload ilk mərhələdə manual qalacaq.

------------------------------------------------------------------------

# Disk və performans strategiyası

AI sistemi üçün başlanğıcda təxminən **150--250 GB** boş sahə saxlamaq
məqsədəuyğundur.

`Temp` qovluğundakı ara renderlər final video təsdiqləndikdən sonra
təmizlənəcək.

8 GB VRAM səbəbilə:

-   böyük modellərin yüngül/quantized variantlarına üstünlük veriləcək;
-   bütün 10 dəqiqə generativ video edilməyəcək;
-   yüksək keyfiyyətli statik vizual + motion əsas üsul olacaq;
-   generativ video yalnız vacib səhnələrdə istifadə ediləcək.

------------------------------------------------------------------------

# İcra ardıcıllığı

## FAZA A --- Baza

-   [x] 01. Sistem/GPU yoxlaması
-   [x] 02. Qovluqların yaradılması
-   [x] 03. Python + Git + FFmpeg
-   [x] 04. ComfyUI
-   [x] 05. İlk image model
-   [x] 06. İlk test şəkli

## FAZA B --- Personaj

-   [x] 07. ELI5 Owl referansının hazırlanması
-   [x] 08. IP-Adapter
-   [x] 09. 10 consistency testi
-   [x] 10. Nəticələrin qiymətləndirilməsi → IP-Adapter RƏDD EDİLDİ (təhrif); SPRITE yanaşması qəbul edildi (Mərhələ 2 qərarı, 2026-09-22)
-   [x] 11. LoRA → LƏĞV (sprite ilə 100% uyğunluq; Character/ELI5_Owl/sprites/)

## FAZA C --- Audio

-   [x] 12. Kokoro
-   [x] 13. Narrator səsinin seçilməsi → **Kokoro `am_fenrir`** (seçildi 2026-09-22)
-   [x] 14. Whisper
-   [x] 15. Subtitle testi

## FAZA D --- Video

-   [x] 16. FFmpeg montage template
-   [x] 17. Pan/zoom
-   [x] 18. Transitions (xfade, Projects/_ffmpeg/montage.py)
-   [x] 19. Background music (mix hazır; royalty-free trek istifadəçidən → C:/YouTubeAI/Music/)
-   [ ] 20. Image-to-video workflow

## FAZA E --- İlk Episode

### QƏRAR (2026-09-22) --- Script LLM

Script və scene planner **OpenAI-uyğun** API üzərindən işləyir; tək kod bazası
üç backend-i dəstəkləyir (`Projects/llm.py`):

| provider | base_url | model | acar (`C:/YouTubeAI/.env`) | ~qiymət / episode |
|---|---|---|---|---|
| `openai` (**default**) | `https://api.openai.com/v1` | `gpt-4o-mini` | `OPENAI_API_KEY` | ~$0.004 |
| `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` | `DEEPSEEK_API_KEY` | ~$0.003 |
| `ollama` (lokal) | `http://127.0.0.1:11434/v1` | `qwen2.5:7b-instruct` | -- | pulsuz |

Açar heç vaxt koda yazılmır --- yalnız `.env` faylından oxunur.
Scene planner narration mətnini LLM-ə **yazdırmır**: skript deterministik bölünür,
LLM yalnız `bg_prompt` + `sprite` seçir → mətn 1:1 qorunur.

-   [x] 21. Mövzu --- "Trademark vs Copyright vs Patent" (`Episodes/trademark-copyright-patent/`)
-   [x] 22. 10 dəqiqəlik script (`Projects/script_gen.py`, 1550 söz → `Episodes/<slug>/script.md`)
    Bölmə-bölmə generasiya: model uzun mətndə söz hədəfini tutmur, ona görə outline → 8 ayrı çağırış,
    hər bölmə hədəfi `OVERSHOOT = 1.18` ilə böyüdülür, qısa çıxarsa bir dəfə yenidən yazdırılır.
    Outline hər bölməyə **fərqli analogiya sahəsi** təyin edir (təkrarlanma problemi həll olundu).
-   [x] 23. Scene Planner (`Projects/scene_plan.py` → `Episodes/<slug>/scenes.json`, 29 səhnə)
    Narration LLM-ə yazdırılmır (1:1 qorunur); sprite **mövqeyi deterministikdir** (`assign_positions`):
    Hook + CTA mərkəz, digər bölmələr növbə ilə sağ/sol --- LLM-ə buraxılanda hamısı bir tərəfdə qalırdı.
-   [x] 24. Bütün vizuallar (`Projects/render_bgs.py` → 29 PNG 1344×768, ~21 s/ədəd)
    Üslub `bg_sdxl_api.json`-a aiddir; scene planner yalnız məzmun yazır. `__SPACE__` placeholder
    sprite mövqeyinə görə fonun boş tərəfini təyin edir.
-   [x] 25. Voiceover (`Projects/tts_gen.py`, Kokoro am_fenrir CPU → `narration.wav` 7.97 dəq)
    **Ölçülmüş sürət 199 wpm** (kodda 150 fərz edilirdi → `WPM` sabiti düzəldildi, hədəf söz 1850).
    Səhnə müddətləri artıq təxmin deyil --- real audio uzunluğudur (fərq 0.02 s).
-   [x] 26. Subtitle (`Whisper/make_srt.py` → `narration.srt`, 1550 söz tanındı = skript ilə eyni)
-   [x] 27. Final render (`Projects/build_episode.py` → 1920×1080 H.264 High/yuv420p 30fps, 137 MB)
    **Düzəldilmiş qüsur 1:** `montage.py` hər keçiddə `XFADE` qədər örtüşmə yaradır
    (`total = Σd − 0.5×(n−1)`), bu da narration-un son 14 s-ni kəsirdi. İndi son səhnədən başqa
    hər müddətə `XFADE` əlavə olunur → video uzunluğu audio ilə eynidir.
    **Düzəldilmiş qüsur 2 (kritik):** PNG girişləri RGB olduğu üçün ffmpeg avtomatik `yuv444p`
    (High 4:4:4 Predictive) seçirdi — bu format Windows pleyerləri, telefonlar və YouTube
    tərəfindən açılmır. `montage.py`-a `-pix_fmt yuv420p -profile:v high -level 4.1` əlavə edildi.
    Bu qüsur pipeline-ın bütün əvvəlki video çıxışlarına aid idi.
-   [x] 28. Keyfiyyət yoxlaması --- video 478.47 s / audio 478.46 s (fərq 0.01 s), personaj
    kadrlar arası piksel-identik, fonlarda personaj/mətn yoxdur, subtitle yandırılıb.

## FAZA F --- Automation

-   [ ] 29. Python orchestrator
-   [ ] 30. ComfyUI API inteqrasiyası
-   [ ] 31. TTS inteqrasiyası
-   [ ] 32. Whisper inteqrasiyası
-   [ ] 33. FFmpeg inteqrasiyası
-   [ ] 34. Sadə UI
-   [ ] 35. One-click test
-   [ ] 36. Stabil production workflow

------------------------------------------------------------------------

# Uğur kriteriyası

Sistem tamamlandıqda istifadəçi:

1.  Video mövzusunu daxil edir.
2.  Təxminən 10 dəqiqə seçir.
3.  ELI5 Owl personajını seçir.
4.  `Generate Video` düyməsini basır.
5.  Sistem script, səhnələr, vizuallar, səs, subtitle və montajı
    hazırlayır.
6.  İstifadəçi final videonu yoxlayır.
7.  Təsdiqlənmiş MP4 YouTube-a yüklənir.

## Hədəf

**Həftədə 2 keyfiyyətli \~10 dəqiqəlik ELI5 Business videosunu mövcud
laptopda, mümkün qədər lokal və minimum dəyişən xərclə istehsal etmək.**
