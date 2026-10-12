# ELI5 Business video pipeline v2 — dizayn

Tarix: 2026-10-12. Köhnə pipeline (v1) istifadəçi qərarı ilə tam silinir, tag qoyulmur. v2 sıfırdan yazılır.

## 1. Dəyişməz qaydalar (yalnız bunlar v1-dən qalır)

1. Bayquşun görünüşü dəyişmir: `Character/ELI5_Owl` referansı (dəyirmi eynək, göy kostyum, sarı qalstuk).
2. Bayquş **videonun hər kadrında** ekrandadır: foto səhnədə, animasiya səhnədə, keçidlərdə, girişdə və çıxışda.
3. Hər səhnənin bayquşu həmin səhnəyə uyğun pozada **gpt-image-2** ilə hazırlanır (referans sprite ilə edit).
4. Səhnəyə uyğun real fotolar **gpt-image-2** ilə çəkilir.

## 2. Əsas prinsiplər

- **Ssenari yoxlanmır.** Nə yazılıbsa oxunur və qəbul olunur. Uzunluq, rəqəm, hesab, struktur yoxlaması yoxdur,
  ssenari "problemi" axtarılmır və bildirilmir.
- **Ssenaridən kənar heç nə yoxdur.** Səsləndirilən mətn sözbəsöz ssenarinin danışıq mətnidir. Ekrandakı hər
  rəqəm və yazı həmin səhnənin danışığından və ya ssenari başlığından götürülür. Yeganə nəzarət GPT çıxışı
  üzərindədir: GPT ssenaridə olmayan rəqəm/mətn yazarsa, o atılır və danışıqdakı cümlə göstərilir. Xəbərdarlıq
  və ya dayanma olmur.
- **Heç bir mərhələ videonu dayandırmır.** Hər xəta üçün retry → fallback, sonra iş davam edir.
- Səhnələrin **60%-i foto, 40%-i Remotion animasiyası**; animasiyalar müxtəlifdir.

## 2a. Qəti proseslər (istifadəçi 2026-10-12, §4 cədvəlindəki fallback sütununu ləğv edir)

Foto, səhnə bayquşu, musiqi və thumbnail heç vaxt fallback ilə əvəz olunmur. "Foto → quote animasiyası",
"bayquş → referans sprite", "musiqi → musiqisiz", "thumbnail → ilk foto" fallback-ləri QADAĞANDIR. Əvəzinə: retry
(backoff ilə); şəkil 4xx təhlükəsizlik/moderasiya rəddi alsa prompt gpt-4o-mini ilə eyni mövzuda yenidən yazılır və
yenidən çəkilir; bütün cəhdlər tükənsə mərhələ xəta ilə dayanır (səbəb + `--resume` göstərişi) və resume həmin
hissəni yenidən çəkir. Foto/animasiya bölgüsü (60/40) dəqiq qalır.

## 3. Giriş formatı

`Ssenariler\*.md`. Nümunə: `eli5_business_how_free_apps_make_billions_script.md`.

- `# Başlıq` → videonun adı və slug. Yoxdursa fayl adı istifadə olunur.
- `## <vaxt kodu> — <ad>` → bölmə. Vaxt kodu atılır, ad ekranda bölmə adı kimi göstərilir.
- `**NARRATION:**` altındakı abzaslar səsləndirilir. `**`, `*`, `---` işarələri təmizlənir, mətn dəyişmir.
- `**VISUAL:**` sətri səsləndirilmir; həmin bölmənin şəkil/animasiya ideyasıdır.
- Danışıq olmayan bölmələr (`Editing and Visual Plan`, `Production Notes`) və meta sətirlər
  (`**Format:**`, `**Target runtime:**`, `**Narration language:**`, ikinci `##` alt başlığı) atılır.
- `NARRATION:` işarəsi olmayan sadə mətn ssenarisi də qəbul olunur: başlıq və `VISUAL:` xaricindəki abzaslar
  danışıqdır.

## 4. Mərhələlər

Əmr: `python run.py "<ssenari faylı>"`. Davam etmək üçün: `python run.py --resume <slug>`.
Epizod qovluğu: `Episodes/<slug>/`, loq: `run.log`. Hər mərhələ çıxış faylı varsa keçilir.

| # | Mərhələ | İş | Fallback | Fayl |
|---|---|---|---|---|
| 1 | script | Format oxunur, bölmələr ~1–3 cümləlik səhnələrə bölünür | — | `scenes.json` |
| 2 | plan | GPT: hər səhnə foto/animasiya (60/40), foto promptu (VISUAL + danışıq), animasiya məzmunu, bayquş pozası | GPT xətası → deterministik bölgü, foto promptu VISUAL-dan, animasiya "açar ifadə" | `scenes.json` |
| 3 | images | gpt-image-2 foto 1536×1024, paralel, limitə uyğun | 2 retry → səhnə animasiyaya keçir | `img/scNN.png` |
| 4 | owl | gpt-image-2 edit + referans sprite, magenta fon lokal silinir | 2 retry → referans sprite | `owl/scNN.png` |
| 5 | voice | Kokoro (TTS\.venv), səhnə-səhnə; səhnə müddəti = səs müddəti + kiçik fasilə | — | `voice/scNN.wav` |
| 6 | captions | Altyazı ssenari mətnindən; vaxt səhnə səsi daxilində söz uzunluğuna görə | — | `captions.json`, `<slug>.srt` |
| 7 | music | Stable Audio (MusicGen\.venv), video uzunluğunda | xəta → musiqisiz | `music.wav` |
| 8 | render | Remotion: bir kompozisiya, 1920×1080, 30 fps | — | `video_raw.mp4` |
| 9 | mix | ffmpeg: səs + musiqi (danışıqda alçalır), −14 LUFS | — | `<slug>.mp4` |
| 10 | publish | Thumbnail (gpt-image-2 + bayquş); başlıq = ssenari başlığı; description ssenari cümlələrindən; teqlər başlıq sözlərindən | thumbnail xətası → ilk foto + bayquş | `Hazir_Videolar/<slug>/` |

Paketin tərkibi: `<slug>.mp4`, `thumbnail.png`, `<slug>.srt`, `youtube.txt` (başlıq, description, teqlər).

## 5. Ekran

- Foto səhnə: tam ekran foto, yavaş zoom/pan. Animasiya səhnə: tünd fon, animasiya ekranın sol ~70%-ində.
- Bayquş həmişə sağ-aşağıdadır; səhnə dəyişəndə yumşaq keçidlə poza dəyişir, ekrandan heç vaxt çıxmır.
- Bölmə adı bölmənin ilk səhnəsində ~3 s yuxarı-solda görünür.
- Altyazı aşağıda, mərkəzdə, fon qutusunda, ≤2 sətir; bayquşun üstünə düşmür.
- Keçidlər: fade / slide / wipe növbə ilə.

## 6. Animasiyalar

8 növ, hər biri ≥2 giriş variantı ilə:
- `counter` — böyük rəqəm sayğacı;
- `bars` — müqayisə sütunları;
- `percent` — faiz dairəsi;
- `flow` — A → B → C axını;
- `list` — siyahı;
- `versus` — A vs B;
- `timeline` — zaman xətti;
- `quote` — danışıqdan açar ifadə.

- Eyni növ ardıcıl iki dəfə gəlmir; bir növ animasiyaların ≤25%-idir.
- Rəqəm və mətn yalnız həmin səhnənin danışığından götürülür. Kod yoxlayır: rəqəm danışıqda yazılan və ya
  sözlə deyilən dəyər olmalıdır ("five dollars" = 5), mətn parçaları danışıqda olmalıdır. Uyğun gəlməsə,
  növbəti növ sınanır, sonda `quote` göstərilir.

## 7. Qovluq (sonda yalnız bunlar)

```
C:\YouTubeAI\
  .claude\  .env  .env.example  .gitignore  CLAUDE.md  progress.md  run.py  pytest.ini
  Character\ELI5_Owl\        # bayquş referansı
  Ssenariler\                # istifadəçinin ssenariləri
  Projects\                  # yeni Python modulları + tests\ (+ .venv)
  Remotion\                  # src\ yeni; node_modules, package.json saxlanır
  TTS\.venv  MusicGen\.venv  # Kokoro, Stable Audio
  Episodes\  Hazir_Videolar\ # iş və nəticə qovluqları
  docs\superpowers\          # bu spec və plan
```

Silinir:
- `Projects\` köhnə kodu və testləri;
- `Remotion\src\` və köhnə konfiqlər;
- `Whisper\`, `ComfyUI\`, `Models\` (ComfyUI modelləri), `Music\`, `Output\`, `Temp\`, `Assets\`
  (şriftlər Remotion-a köçür);
- `Episodes\*`, `Hazir_Videolar\*` (v1 videoları, istifadəçi 2026-10-12), `docs\*` (bu spec xaric);
- `plan.md`, `README.md`, `run_comfyui.bat`, `Yeni_Video.bat`;
- köhnə `CLAUDE.md`, `progress.md`, yaddaş qeydləri.

## 8. Modullar (`Projects\`)

| Modul | Məsuliyyət |
|---|---|
| `script.py` | md → bölmələr → səhnələr |
| `plan.py` | GPT planı + grounding (yalnız danışıqdan) + 60/40 və növ növbələşməsi |
| `images.py` | gpt-image-2 foto |
| `owl.py` | gpt-image-2 bayquş + magenta key-out |
| `voice.py` | Kokoro çağırışı |
| `captions.py` | altyazı + srt |
| `music.py` | Stable Audio çağırışı |
| `render.py` | Remotion props + render |
| `mix.py` | ffmpeg mix + loudnorm |
| `publish.py` | thumbnail + youtube.txt + paket |
| `llm.py` | OpenAI çağırışları (chat, image, edit), retry |
| `pipeline.py` | mərhələ sırası, resume, loq |

Remotion `src\`: `Episode.tsx` (səhnə ardıcıllığı + daimi bayquş qatı + altyazı + bölmə adı),
`PhotoScene.tsx`, `anim\*.tsx` (8 növ), `Owl.tsx`.

## 9. Testlər

pytest, şəbəkəsiz; LLM və alt-proseslər parametr kimi əvəz olunur. Testlər bunları yoxlayır:
- ssenari oxunması (bu format və sadə mətn), meta/qeyd bölmələrinin atılması, mətnin sözbəsöz qalması;
- 60/40 bölgüsü, növ növbələşməsi, ≤25% pay;
- uydurma rəqəm/mətnin `quote`-a düşməsi;
- fallback-lər: şəkil → animasiya, bayquş → referans, musiqi → yox;
- resume.

E2E: `eli5_business_how_free_apps_make_billions_script.md` ilə tam video.

## 10. Dil və model

Danışıq ingiliscədir (ssenari dili). Kod şərhləri ASCII-azərbaycanca.
Modellər: plan gpt-4o-mini; şəkil, bayquş və thumbnail gpt-image-2.
