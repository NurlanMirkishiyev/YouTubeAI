# CLAUDE.md — YouTubeAI (ELI5 Business video pipeline v2)

Dizayn: `docs/superpowers/specs/2026-10-12-pipeline-v2-design.md`. Canlı vəziyyət: `progress.md` (sessiyanın
əvvəlində oxu, hər mərhələdən sonra yenilə).

## Dəyişməz qaydalar
1. Bayquşun görünüşü dəyişmir (`Character/ELI5_Owl`, referans `sprites_hd/front.png`).
2. Bayquş videonun HƏR kadrında ekrandadır (sağ-aşağı), heç vaxt yox olmur.
3. Hər səhnənin bayquşu səhnəyə uyğun gpt-image-2 ilə hazırlanır.
4. Səhnəyə uyğun real fotolar gpt-image-2 ilə çəkilir.

## Prinsiplər
- Ssenari yoxlanmır və dəyişdirilmir: nə yazılıbsa sözbəsöz oxunur. Ssenaridən kənar heç nə əlavə olunmur
  (ekrandakı rəqəm/yazı yalnız səhnə danışığından, bölmə adından, başlıqdan).
  **Yeganə istisna (istifadəçi 2026-10-13):** videonun başında bayquş mövzuya uyğun salamlayır (intro, ≥6 s),
  sonunda sağollaşır və subscribe-a çağırır (outro, ≥10 s) — mətn GPT ilə (`plan.add_bookends`), səsli + altyazılı;
  fon (gpt-image-2) və iki bayquş pozası da fallback-siz.
- Səhnələrin 60%-i foto, 40%-i Remotion animasiyası (intro/outro xaric); animasiyalar səhnədən səhnəyə fərqlidir.
- **Premium animasiya (istifadəçi 2026-10-14):** hər video mövzuya uyğun rəng teması alır (`plan.with_theme`,
  royal/gold/emerald/electric/sunset/crimson = `theme.ts` PALETTES); hər animasiyaya mənaya uyğun ikon(lar)
  (`grounding.ICONS` = `anim/Icon.tsx`, yazı deyil). Remotion: `anim/Backdrop` (canlı fon), `anim/kit` (şüşə kart,
  gradient yazı, Badge, Burst, Shine), `anim/Anims` + `anim/TextAnims` (8 növ × 2 variant); kadr heç vaxt donmur.
  Yeni ikon/tema: hər iki tərəfə əlavə et (`test_icon_and_theme_names_match_remotion`).
- Eyni şəkil olmur: plan təkrarlanan foto promptu / bayquş pozasını yenidən yazdırır, images dHash ilə çox oxşar
  fotonu "fərqli kompozisiya" ilə yenidən çəkir.
- Heç bir mərhələ ssenari səbəbilə videonu dayandırmır (ssenari yoxlanmır).
- **Ssenari formatı ümumidir (`script.py`):** yalnız danışıq oxunur. Danışıq etiketi (NARRATION/Voiceover/VO/Narrator/
  Script/Host…), rejissor etiketi (VISUAL(S)/On-screen text/B-roll/SFX/Camera/`[..]`/`(..)`…) və meta etiket/bölmə
  (Format, Video title, Thumbnail idea, Editing/Production notes, Core takeaway…) istənilən formada tanınır
  (`**X:**`, `**X**:`, tək `**X**`, `### X`, `X:`). Yeni format çıxsa: lüğətə (SPEECH/DIRECTION/META) söz əlavə et + test.
  Qalan şübhəli cümlə `run.log`-da `XEBERDARLIQ` kimi görünür (run dayanmır).
- **Altyazı:** oxunan söz rənglə izlənir (Kokoro söz vaxtları `voice/scNN.words.json` → `captions.py` difflib uyğunlaşdırma).
- **Thumbnail stili istifadəçi seçimidir** (`config/thumbnail.json`, `thumbs.STYLES`), özbaşına dəyişmə. Yazı:
  ssenarinin "Thumbnail idea" sitatı, yoxdursa başlığın dəqiq fraqmenti. Bayquş: ayrıca poza `owl/thumb.png`.
  Nümunə: `python Projects/thumbs.py samples <ssenari>` → `Thumbnail_Numuneler\`; seçim: `thumbs.py select <stil>`.
- **Qəti, əvəzlənməyən proseslər (istifadəçi 2026-10-12):** foto (gpt-image-2), səhnə bayquşu (gpt-image-2), musiqi
  (Stable Audio), thumbnail (gpt-image-2) HEÇ VAXT fallback ilə əvəz olunmur (foto → sitat animasiyası YOX, bayquş →
  sprite YOX, musiqisiz video YOX, thumbnail → ilk foto YOX). Alınmasa: retry; şəkil təhlükəsizlik səbəbilə rədd
  olunsa prompt eyni mövzuda yenidən yazılıb çəkilir; hamısı tükənsə run dayanır, səbəbi deyilir, `--resume` həmin
  hissəni yenidən çəkir. OpenAI balansı bitəndə də dayanır — istifadəçiyə de, kredit əlavə olunandan sonra `--resume`.

## Tetik
`Video: <ssenari faylı>` (`Ssenariler\` içində, `.md`-siz də olar) → sualsız:
1. WMI ilə aç (alətdən `Start-Process` alət çağırışı bitəndə ölür):
   `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c "C:\YouTubeAI\Projects\.venv\Scripts\python.exe -u run.py "<fayl>" > C:\YouTubeAI\Episodes\_run.log 2>&1"'; CurrentDirectory='C:\YouTubeAI'}`
   20 s sonra prosesin sağ olduğunu yoxla.
2. Monitor ilə `Episodes\<slug>\run.log`-u (mərhələlər) və `Episodes\_run.log`-u (stdout: cəhd/retry, `HAZIR`)
   izlə: `\[[0-9]+/10\]|xetasi|DAYANDI|BITDI|HAZIR|alinmadi|XEBERDARLIQ`.
3. Kəsilsə: `python run.py --resume <slug>` (mərhələ faylı varsa keçilir).
4. Bitəndə qısa yoxla: mp4 müddəti (ffprobe), −14 LUFS, bir neçə kadr (bayquş hər kadrda), thumbnail;
   `Hazir_Videolar\<slug>\` hazır olduğunu bildir.

## Əmrlər
- Testlər: `Projects\.venv\Scripts\python -m pytest -q Projects/tests`
- Remotion tip yoxlaması: `cd Remotion; npx tsc --noEmit`

## Struktur
`run.py` → `Projects/pipeline.py` mərhələləri: script → plan → images → owl → voice → captions → music → render →
mix → publish. Modullar: `script, plan, grounding, images, owl, ratelimit, speech, voice, captions, music, render,
mix, publish, thumbs, pipeline, llm`. Remotion: `Remotion/src/` (Episode, PhotoScene, AnimScene, anim/Anims, OwlLayer,
Captions, SectionTitle). `TTS/.venv` (Kokoro), `MusicGen/.venv` (Stable Audio). Açarlar `.env`-də — commit etmə.
Cavab dili: azərbaycanca, qısa.
