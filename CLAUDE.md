# CLAUDE.md — YouTubeAI (ELI5 Business video pipeline)

## Sessiyanın əvvəli (HƏMİŞƏ)
1. `progress.md`-ni oxu ("Cari vəziyyət", "Növbəti dəqiq addım", "Problemlər reyestri").
2. Açıq iş varsa ondan davam et; yoxdursa istifadəçinin mövzusunu gözlə.
3. `progress.md` HƏR mərhələdən sonra yenilənir (tamamlanan iş → "İcra jurnalı", ən yenisi yuxarıda).

## Tetik: mövzu = hazır video (tam avtonom)
İstifadəçi `Video: <Mövzu>` yazır və ya sadəcə mövzunu yazır → **sualsız, təsdiqsiz** dərhal:
1. Mövzu azərbaycanca verilibsə, ingiliscə başlığa çevir (məs. "What Is Profit Margin?").
2. PowerShell ilə müstəqil proses aç (Claude sessiyası bağlansa da işləsin):
   `Start-Process "C:\YouTubeAI\Projects\.venv\Scripts\python.exe" -ArgumentList 'run.py','"<Mövzu>"' -WorkingDirectory C:\YouTubeAI -RedirectStandardOutput Episodes\_run_<slug>.log -RedirectStandardError Episodes\_run_<slug>.log.err`
3. Loqu Monitor ilə izlə (`[N/11]` mərhələ sətirləri + error/traceback). Ölsə: `run.py --resume <slug>`.
4. Bitəndə özün yoxla (istifadəçidən soruşma):
   - `owl_qa.json` (hamısı ok), bir neçə kadr + `thumbnail.png` vizual — bayquş eyni personaj, sağda, yazı/insan yox;
   - `checks.final_video_problems(mp4) == []`, müddət 8–10 dəq, −14 LUFS;
   - musiqi dövr nöqtəsində sükut yoxdur (`silencedetect=n=-40dB:d=0.4`; ~0.4 s danışıq fasiləsi normaldır).
5. `Hazir_Videolar\<slug>\` hazır olduğunu qısa bildir, `progress.md` jurnalına sətir yaz, commit et.
Bir neçə mövzu → ardıcıl (paralel yox: gpt-image limiti 5 şəkil/dəq). Yalnız həqiqi blokerdə soruş
(OpenAI balansı bitib, model yüklənmir, sirr lazımdır).

## Dəyişməz istifadəçi qərarları
- Video **8–10 dəq**, heç vaxt 10 dəqiqədən uzun deyil.
- İlk saniyələrdə **"Hook" yazısı/sözü olmur** (nə ekranda, nə səsdə); giriş kartındakı mövzu başlığı və
  bölmə başlıqları (lower-third) qalır (2026-09-28). Test: `Projects/tests/test_spoken_titles.py`.
- Bayquş sabit (animasiya yox), həmişə sağda; hər səhnədə mətnə uyğun ChatGPT bayquşu, görünüşü
  (dəyirmi eynək, göy kostyum, sarı qalstuk) dəyişməz.
- Musiqi: AI, lokal (Stable Audio Open), pulsuz, istinadsız. Stability Community License aktivdir (2026-09-28).
  Pullu musiqi/səs xidməti təklif etmə.
- Yeni problem tapılanda: `progress.md` reyestrinə sətir + test (TDD) + kod düzəlişi — əl ilə həll yox.

## Texniki
- Testlər: `Projects\.venv\Scripts\python -m pytest -q Projects/tests` (repo kökündən).
- Açarlar `.env`-də — commit etmə. HF yükləməsi: `HF_HUB_DISABLE_XET=1`.
- Cavab dili: azərbaycanca, qısa.
