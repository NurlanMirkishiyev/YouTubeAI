# progress.md — pipeline v2

Sessiyanın əvvəlində oxunur, hər mərhələdən sonra yenilənir (ən yenisi yuxarıda).

## Aktiv run (2026-10-14 00:2x) — DAYANIB: OpenAI balansı bitib
- Ssenari: `Ssenariler\eli5_business_why_expensive_brands_make_people_want_them.md`,
  slug `eli5-business-why-expensive-brands-make-people-want-their-products-even-more`.
- Plan OK (94 səhnə: intro + 55 foto + 37 anim + outro; quote 13, ardıcıl deyil). Fotolar hazır (img/ 57 fayl).
- Owl mərhələsi: 40 bayquş hazır, sonra HTTP 429 (balans). Kredit əlavə olunandan sonra:
  `python run.py --resume eli5-business-why-expensive-brands-make-people-want-their-products-even-more` (WMI ilə).

## Cari vəziyyət (2026-10-13, PAUZA — istifadəçi: "hər şeyi yaddaşa yaz, sonra davam edəcəyik")
- **Pipeline v2 tam işlək, `master`-də, GitHub-a push olunub** (`NurlanMirkishiyev/YouTubeAI`, son commit 3ea5fb9).
  Açıq branch yoxdur. 145 test keçir, `npx tsc --noEmit` təmiz. Git tarixçəsi istifadəçi istəyi ilə təmizlənib
  (v1 tarixçəsi GitHub-da yoxdur); tam köhnə tarixçənin lokal ehtiyatı: `C:\YouTubeAI_backup\YouTubeAI_full_history.bundle`.
- **Hər video üçün standart (istifadəçi 2026-10-13 bəyəndi və hamısına tətbiq etdirdi):**
  - Intro (≥6 s): bayquş mövzuya uyğun salamlayır (GPT mətni, səsli), bulanıq mövzu fonu + "ELI5 BUSINESS" + başlıq
    söz-söz animasiyası, böyük bayquş (820px).
  - Outro (≥10 s): bayquş sağollaşır + subscribe çağırışı, "Thanks for watching!" + SUBSCRIBE düyməsi klik → SUBSCRIBED,
    zəng yellənir; outro bayquşu propsuz (əl edir, yuxarı işarə edir).
  - Eyni şəkil yoxdur: plan buraxılan səhnələri yenidən soruşur, ALREADY USED + DUPLICATE təmiri + `unique_guard`;
    images dHash ≤8 bit → "fərqli kompozisiya" ilə yenidən çəkir.
  - Spec/plan: `docs/superpowers/specs|plans/2026-10-13-unique-images-intro-outro*`.
- Əsas pipeline qaydaları: foto/bayquş/musiqi/thumbnail/intro-outro fonu fallback-siz; plan GPT strict json_schema;
  animasiya mətni narrasiyadan dəqiq fraqment (≤7 söz); fotoda bayquş yox (`photo_safe`); mix −14 LUFS (iterativ gain).
- Hazır videolar (`Hazir_Videolar\`):
  - `how-free-apps-make-billions-without-charging-you` — 12:30, 60 səhnə, −14.2 LUFS. **Intro/outro-SUZ** (köhnə
    formatda; o zaman bu xüsusiyyət yox idi) və orada 3 cüt eyni promptlu foto var (sc1/3, sc5/6, sc16/18).
  - `how-a-coffee-shop-makes-money` — 43 s **test** videosu (mini E2E, intro/outro yoxlaması üçün). Lazım deyilsə silinə bilər
    (+ `Episodes\how-a-coffee-shop-makes-money`).

## Növbəti dəqiq addım (davam edəndə)
1. İstifadəçidən soruş: ilk videonu (`how-free-apps...`) yeni formatda (intro/outro + dublikat fotolar yenidən)
   hazırlayaq? Yol: `Episodes\how-free-apps...\scenes.json`-a `plan.add_bookends` tətbiq et, dublikat promptlu
   fotoların (sc03, sc06, sc18) promptunu `plan.unique_guard`/GPT ilə yenilə və png-lərini sil; `voice/`, `narration.wav`,
   `captions.json`, `*.srt`, `music.wav` (müddət dəyişir), `video_raw.mp4`, `<slug>.mp4`, `published`, `props.json` sil;
   sonra `python run.py --resume how-free-apps-make-billions-without-charging-you` (WMI ilə). Sonda kadrlar/LUFS yoxla.
2. Test videosunu (`how-a-coffee-shop-makes-money`) silmək istəyib-istəmədiyini soruş.
3. Yeni video: `Video: <ssenari>` (CLAUDE.md Tetik) — intro/outro avtomatikdir.

## Tarixçə (qısa)
- 2026-10-12: v1 silindi, v2 dizayn + Task 0–13 + final review fix dalğası; ilk E2E video (3 problem tapılıb düzəldi:
  plan json_schema, fotoda real bayquş, LUFS). v2 master-ə merge + push, git tarixçəsi təmizləndi.
- 2026-10-13: unikal şəkillər + intro/outro (brainstorm → spec → plan → TDD → mini E2E), master-ə merge + push.

## Təkrarlanmamalı yanlış yollar
| Nə | Düzgün yol |
|---|---|
| Uzun run-u alətdən `Start-Process` ilə açmaq | WMI `Invoke-CimMethod Win32_Process Create` (CLAUDE.md Tetik) |
| Regex olan kodu heredoc ilə yazmaq | Edit/Write aləti |
| Python skripti ilə çoxsətirli `str.replace` redaktə (CRLF/escape uyğunsuzluğu; `\b` backspace-ə çevrildi) | Edit aləti |
| `sed -i 'Ns/.*/…/'` sətir nömrəsi ilə əvəzləmə (əvvəlki insert nömrələri sürüşdürdü, `s["type"]=t` silindi) | Edit aləti; sonra `git diff` ilə bax |
| Run-u öldürmək üçün `*run.py*` filtri olan PowerShell-i Bash-dan çağırmaq (filtr öz əmr sətrinə də uyğun gəldi, özünü öldürdü) | PowerShell alətində `-notlike '*Get-CimInstance*'` ilə, sonra prosesin öldüyünü yoxla |
| `_run.log`-u yeni run-dan dərhal sonra oxumaq (köhnə məzmun görünür) | Epizodun `run.log`-unda yeni `[n/10]` sətirlərini say |
| Plan GPT-dən `json_object` ilə anim istəmək (gpt-4o-mini obyekt yox, növ adları qaytardı → hamısı quote) | strict `json_schema` (plan.SCHEMA), cavab sxemdən kənara çıxa bilmir |
| GPT-yə "narration words" demək (parafraz edir: "Old perspective", "Users benefit" → grounding rədd edir) | "EXACT fragment, ≤7 söz" + rədd olunanları səbəbi ilə 2-ci keçid + sadalamadan list (`grounding.enumeration`) |
| Ssenari VISUAL-ındakı "owl mascot"-u foto promptuna buraxmaq (fotoda real bayquş) | `plan.photo_safe` + SYSTEM qaydası + `images.STYLE` "No owl, no mascot" |
| Tək keçidli `loudnorm=I=-14` (−15.9 LUFS verdi; limiter/true-peak loudness-i yeyir) | `mix.solve_gain`: gain limiterdən SONRA ölçülür, ±0.3 LU-ya qədər iterasiya |
| Flow qutusunda `overflowWrap:'anywhere'` ("somethin g") və ya `hyphens:'auto'` ("pic-tures") | `break-word` + 4 addımda 280px border-box, 34px şrift |
| Plan pis çıxanda run-u images-ə buraxmaq (pul boşa gedir) | Plan bitən kimi `scenes.json`-da növ paylanmasına bax (quote ≤ ~5/24); pisdirsə dərhal dayandır, `scenes.json` + `img/` sil, yenidən başlat |
| Foto/bayquş xətası üçün bütün epizodu yenidən çəkmək | Yalnız pis fotoların promptunu düzəlt, həmin `img/scNN.png`-ləri sil, `--resume` (qalanı keçilir) |
| Bayquşa "subscribe button-a işarə et" pozası vermək (gpt-image qırmızı qutu çəkir) | "waving goodbye, pointing up, no props/buttons" |
| `pipeline._texts` ilə intro/outro mətnini ssenari ilə müqayisə etmək (hər run reset olardı) | `_texts` intro/outro-nu keçir |
| Mərhələ bitdi deyə nəticəyə inanmaq | Sonda ffprobe müddət + `ebur128` LUFS + kontakt-vərəq kadrlar + thumbnail-a bax |

## İcra jurnalı
- 2026-10-13: unikal şəkillər + intro/outro master-də (bütün videolar üçün standart); pauza.
- 2026-10-12 gecə: fix dalğası + E2E; ilk video hazır (5 commit: 775f040..2038233).
- 2026-10-12: Task 0–13 tamam, 81 test; final review göndərildi; istifadəçi E2E-ni saxlatdı.
- 2026-10-12: Task 0–10 tamam (hər biri task review + fix round); Task 11, 12 düzəlişdə; Task 13 (qaydalar) yazıldı.
- 2026-10-12: v2 dizayn + plan təsdiqləndi; v1 silindi.
