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
   - `owl_qa.json` (hamısı ok, `cards.intro/outro` ok), giriş/çıxış kartı kadrı — mövzuya uyğun bayquş, tərpənmir, bir neçə kadr + `thumbnail.png` vizual — bayquş eyni personaj, sağda, yazı/insan yox;
   - `checks.final_video_problems(mp4) == []`, müddət 8–10 dəq, −14 LUFS;
   - `math_check.json` → `"problems": []`;
   - `bg_qa.json` → `"duplicates": []`; kadrlarda uşaqsayağı görüntü (oyuncaq/cizgi fon) yoxdur;
   - musiqi dövr nöqtəsində sükut yoxdur (`silencedetect=n=-40dB:d=0.4`; ~0.4 s danışıq fasiləsi normaldır).
5. `Hazir_Videolar\<slug>\` hazır olduğunu qısa bildir, `progress.md` jurnalına sətir yaz, commit et.
6. **Təsdiq + yaddaşı silmə** (istifadəçi 2026-09-29): AskUserQuestion ilə soruş — "Video təsdiqlənsin və
   pipeline-dakı yaddaşı silinsin?". Təsdiqdə: `Projects\.venv\Scripts\python Projects\forget_episode.py <slug>`
   (`Episodes\<slug>\` + həmin epizodun `_run_*.log/.err` silinir; `Hazir_Videolar\<slug>\` QALIR), sonra
   `progress.md`-dən həmin videonun jurnal/vəziyyət sətirlərini sil (reyestrdəki ümumi kod düzəlişləri qalır), commit.
   Rədd edilsə — heç nə silinmir, istifadəçinin iradını düzəlt. Test: `Projects/tests/test_forget_episode.py`.
Bir neçə mövzu → ardıcıl (paralel yox: gpt-image limiti 5 şəkil/dəq). Yalnız həqiqi blokerdə soruş
(OpenAI balansı bitib, model yüklənmir, sirr lazımdır).

## Dəyişməz istifadəçi qərarları
- Video **8–10 dəq**, heç vaxt 10 dəqiqədən uzun deyil.
- İlk saniyələrdə **"Hook" yazısı/sözü olmur** (nə ekranda, nə səsdə); giriş kartındakı mövzu başlığı və
  bölmə başlıqları (lower-third) qalır (2026-09-28). Test: `Projects/tests/test_spoken_titles.py`.
- **Təkrar kadr QƏTİ olmur** (2026-09-28): bir epizodda eyni obyekt/fon iki dəfə yox. `check_bgs` CLIP ilə
  (`bg_dedupe.py`, hədd 0.88) yoxlayır, sonrakı təkrarı yenidən çəkir; qalarsa mərhələ keçmir.
  Test: `Projects/tests/test_no_repeats.py`.
- **Uşaq videosu kimi görünmür** (2026-09-28, seçim A): fonlar realist fotoqrafiya (Pixar/3D yox), oyuncaq/
  konfet/karusel yox; ssenari 25–45 yaş yetkinlər üçün; uşaq musiqisi yox. Bayquş dəyişmir.
  Test: `Projects/tests/test_adult_look.py`.
- **Hesab səhvi QƏTİ olmur** (2026-09-30): ssenaridəki hər rəqəmli cümlə `math_check.py` ilə yoxlanır
  (gpt-4o 3 baxış + Python hesabı); `math_check.json` olmadan `script_gen` mərhələsi keçmir. YouTube
  metadata-da rəqəm/hesab yoxdur. Test: `Projects/tests/test_number_accuracy.py`.
- Bayquş sabit (animasiya yox) — **giriş/çıxış kartında da** (2026-09-30): orada hər mövzuya ayrıca yaradılmış
  `owl/intro.png` (açılış) və `owl/outro.png` (qapanış, sağollaşır), eyni mövzu əşyası ilə. Test: `test_card_owls.py`.
- Bayquş həmişə sağda; hər səhnədə mətnə uyğun ChatGPT bayquşu, görünüşü
  (dəyirmi eynək, göy kostyum, sarı qalstuk) dəyişməz.
- Musiqi: AI, lokal (Stable Audio Open), pulsuz, istinadsız. Stability Community License aktivdir (2026-09-28).
  Pullu musiqi/səs xidməti təklif etmə.
- Yeni problem tapılanda: `progress.md` reyestrinə sətir + test (TDD) + kod düzəlişi — əl ilə həll yox.

## Texniki
- Testlər: `Projects\.venv\Scripts\python -m pytest -q Projects/tests` (repo kökündən).
- Açarlar `.env`-də — commit etmə. HF yükləməsi: `HF_HUB_DISABLE_XET=1`.
- Cavab dili: azərbaycanca, qısa.
