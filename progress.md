# progress.md — pipeline v2

Sessiyanın əvvəlində oxunur, hər mərhələdən sonra yenilənir (ən yenisi yuxarıda).

## Cari vəziyyət
- 2026-10-12: v1 tam silindi (yalnız bayquş hissələri qaldı). v2 `pipeline-v2` branch-ında (master-ə merge YOX,
  push YOX). Plan: `docs/superpowers/plans/2026-10-12-pipeline-v2.md`, spec:
  `docs/superpowers/specs/2026-10-12-pipeline-v2-design.md`.
- **Task 0–13 TAMAM** (hər biri task review + fix round, hamısı təmiz). 81 test keçir. Bütün qərarlar (Ruling) və
  təxirə salınmış kiçik qeydlər: SDD ledger `.superpowers/sdd/2026-10-12-pipeline-v2/progress.md` (git-ignored, diskdə).
- 2026-10-12 (davam): final review fix dalğası TAMAM, commit 775f040 (107 test, tsc OK). Fallback-lər silindi
  (generate.py: retry + təhlükəsizlik rəddində prompt yenidən yazılır + tükənsə xəta). Scoped re-review: Critical
  yox, ready for E2E; Important (balansda paralel növbə) düzəldi (e400940).
- E2E-də tapılan: plan GPT `anim`-i obyekt yox, ad siyahısı qaytarırdı → hamısı quote. Düzəliş: strict JSON schema
  (e400940), dəqiq fraqment + rədd səbəbi ilə 2-ci keçid + sadalamadan list (f76de76). Nəticə: 24 animasiyadan 4 quote.
- E2E-də daha 2 problem tapılıb düzəldi: fotolarda real bayquş (VISUAL-da "owl mascot") → photo_safe + prompt
  qaydası (37c9f64); səs −15.9 LUFS → mix gain limiterdən sonra iterativ ölçülür, −14.2 LUFS (2038233). 4 addımlı
  flow sözləri qırmır. 124 test, tsc OK.
- **E2E İLK VİDEO HAZIR:** `Hazir_Videolar/how-free-apps-make-billions-without-charging-you/` (12:30, 1080p,
  60 səhnə: 36 foto + 24 animasiya, bayquş hər kadrda, thumbnail, youtube.txt fəsillərlə). Flow düzəlişi üçün
  render+mix+publish yenidən işlədi (00:06): −14.2 LUFS, peak −1.0 dBFS, 12:30, kadrlar yoxlanıb.

## Növbəti dəqiq addım (davam edəndə)
1. (Tamam) Yenidən render yoxlanıb.
2. (Tamam 2026-10-13) v2 master-ə merge + GitHub-a push olundu; pipeline-v2 branch-ı silindi. İş indi master-dədir.
   İstifadəçinin istəyi ilə git tarixçəsi təmizləndi: v1 tarixçəsi silindi (force-push, tək root commit 11a7683),
   köhnə v1 plan/spec sənədləri silindi. Tam köhnə tarixçənin ehtiyatı:
   `C:\YouTubeAI_backup\YouTubeAI_full_history.bundle` (lazım deyilsə istifadəçi silə bilər).

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
| Mərhələ bitdi deyə nəticəyə inanmaq | Sonda ffprobe müddət + `ebur128` LUFS + kontakt-vərəq kadrlar + thumbnail-a bax |

## İcra jurnalı
- 2026-10-12 gecə: fix dalğası + E2E; ilk video hazır (5 commit: 775f040..2038233).
- 2026-10-12: Task 0–13 tamam, 81 test; final review göndərildi; istifadəçi E2E-ni saxlatdı.
- 2026-10-12: Task 0–10 tamam (hər biri task review + fix round); Task 11, 12 düzəlişdə; Task 13 (qaydalar) yazıldı.
- 2026-10-12: v2 dizayn + plan təsdiqləndi; v1 silindi.
