# Unikal şəkillər + intro/outro — dizayn (2026-10-13)

İstifadəçi təsdiqi: 2026-10-13 ("bəli"). Seçimlər: intro/outro **GPT mətni + səs**, dizayn **mövzu fonu + bayquş +
Remotion animasiyası**, müddət **intro ≥6 s, outro ≥10 s**.

## 1. Problem (ilk E2E videodan ölçülüb)
- 3 cüt foto eyni promptla çəkilib (sc1=sc3, sc5=sc6, sc16=sc18).
- 10 səhnə eyni bayquş pozasını alıb ("standing and explaining, friendly").
- Kök səbəb: GPT batch cavabında bəzi səhnələri buraxır → `plan_scenes` boşluğa VISUAL/defolt yazır; eyni bölmənin
  səhnələri eyni VISUAL-ı paylaşır.

## 2. Unikal şəkillər
1. **Buraxılan səhnələr** (`plan._ask_batch` cavabında olmayan `n`): bir dəfə də yalnız onlar üçün soruşulur.
2. **Prompt qaydası:** SYSTEM-ə "hər photo_prompt və owl pozası videonun digər səhnələrindən fərqli olsun (yer, insan,
   obyekt, bucaq)". Hər batch-a əvvəlki batch-ların `photo_prompt`/`owl` siyahısı "ALREADY USED" kimi verilir.
3. **Dublikat aşkarı:** plan sonunda normallaşdırılmış (`lower`, boşluq/durğu silinmiş) eyni `photo_prompt` və ya eyni
   `owl` olan səhnələr (ilkindən başqası) GPT-yə "bunlardan fərqli et" qeydi ilə bir dəfə də verilir.
4. **Deterministik son qoruyucu** (GPT yenə də təkrar qaytarsa və ya cavab verməsə):
   - foto: `photo_safe(VISUAL)` + səhnənin öz narrasiyasından ilk cümlə (narrasiya hər səhnədə fərqlidir) → unikal;
   - bayquş: `DEFAULT_POSES` (≥10 fərqli poza) siyahısından növbə ilə, artıq istifadə olunanı keçərək.
5. **Çəkiləndən sonra:** `images` hər yeni fotonun dHash-ini (64 bit) epizodun digər fotoları ilə müqayisə edir;
   Hamming məsafəsi ≤ `DUP_BITS` (8) olsa şəkil yadda saxlanmır, prompta " Different composition, camera angle and
   setting." əlavə edilib yenidən çəkilir (adi retry kimi sayılır; tükənsə mərhələ dayanır — əvəzləmə YOX).

## 3. İntro və outro
### Plan
`plan.bookends(title, first_texts)` — bir strict-schema GPT çağırışı:
`{greeting (≤16 söz, başlığın mövzusunu anır, kanal: "ELI5 Business"), farewell (≤26 söz, sağollaşma + subscribe
çağırışı), bg_prompt (mövzu fonu, real foto, mətnsiz, bayquşsuz), owl_intro (salamlayan poza + mövzu propu),
owl_outro (əl edən, subscribe-a işarə edən poza)}`. Söz limiti aşılsa bir dəfə yenidən soruşulur; yenə aşılsa
cümlə sərhədində kəsilir. Xəta → bir retry, sonra plan mərhələsi xəta verir (balans xətası dərhal).

### Data
`scenes.json`: başa `{"n": 0, "type": "intro"}`, sona `{"n": N+1, "type": "outro"}` (section "", section_start
False, text = greeting/farewell, photo_prompt = bg_prompt, owl = poza, anim None). 60/40 bölgüsü yalnız məzmun
səhnələrinə. Köhnə `scenes.json` (intro-suz) işləməyə davam edir.

### Mərhələlər (mövcud axın, kiçik dəyişiklik)
- images: `type in ("photo", "intro", "outro")` → fon şəkli çəkilir; done-yoxlaması da eyni.
- owl: dəyişməz (bütün səhnələr).
- voice: intro/outro WAV `MIN_S = {"intro": 6.0, "outro": 10.0}`-a qədər sükutla uzadılır.
- captions: dəyişməz (mətn səhnədən).
- render.props: `img` intro/outro üçün də verilir; `types.ts` `type` birliyi genişlənir.
- publish: təsvir ilk **məzmun** səhnəsinin mətnidir; fəsillər dəyişməz (intro bölməsiz → "0:00 <başlıq>").

### Remotion
- `IntroScene`: fon şəkli (blur 6px, qaraltma 45%), başlıq (Montserrat 800, ~84px, sola düzlənmiş, söz-söz qalxan
  animasiya, sarı alt xətt), "ELI5 Business" kiçik etiket.
- `OutroScene`: eyni fon; mərkəz-solda qırmızı **SUBSCRIBE** düyməsi (spring pop, 1.2 s-də "klik" — düymə boz
  "SUBSCRIBED"-ə keçir, zəng ikonu yellənir), altında "Thanks for watching!".
- `OwlLayer`: intro/outro səhnəsində bayquş böyük (`OWL_H_BIG = 820`), yenə sağ-aşağıda — "bayquş hər kadrda" qorunur.
- Intro/outro-da SectionTitle göstərilmir.

## 4. Qaydalar
`CLAUDE.md` "Prinsiplər"-ə istisna: ssenaridən kənar yalnız intro salamı və outro sağollaşması (GPT, mövzuya uyğun,
səsli). Fon və bayquşları üçün də fallback YOX (retry / prompt yenidən yazılır / dayanır).

## 5. Test
TDD: plan (buraxılan səhnə, dublikat təmiri, deterministik qoruyucu, bookends söz limiti, intro/outro yerləşməsi və
60/40), images (dHash dublikatı yenidən çəkilir, intro/outro fonu), voice min müddət (saf funksiya), render.props
(intro/outro img), publish təsviri, inteqrasiya testi (intro/outro ilə), `tsc`. Sonda real mini-run (qısa ssenari) +
intro/outro kadrlarına baxış.
