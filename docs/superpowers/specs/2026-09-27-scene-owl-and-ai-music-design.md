# Səhnəyə uyğun bayquş + AI musiqi — dizayn (2026-09-27)

İstifadəçi tələbi: (1) musiqi lisenziya/istinad tələb etməsin və **ödənişsiz** olsun; (2) personaj hər
səhnədə mətnə uyğun, detallı görünüşdə olsun (ChatGPT ilə), amma əsl görünüşü dəyişməsin.
Qərarlar (AskUserQuestion): musiqi = AI ilə; bayquş = ayrıca şəffaf şəkil, fonun üstünə.

## Proba nəticələri (ölçülüb)
- `gpt-image-2` `/v1/images/edits` + `background=transparent` + referans `sprites_hd/front.png`:
  RGBA, alpha 0..254, ~25 s/şəkil, personaj eyni (eynək, kostyum, sarı qalstuk, kəmər, ayaqlar).
- Stable Audio Open 1.0: Stability Community License — <$1M gəlir pulsuz, çıxış istifadəçiyə məxsus,
  çıxış üçün istinad yoxdur; kommersiya üçün pulsuz qeydiyyat. HF repo gated (istifadəçi qəbul etməlidir).

## 1. Səhnə bayquşu
- `scene_plan`: LLM hər səhnəyə `owl_action` yazır (1 hərəkət/emosiya, ≤1 əşya, insan/yazı yox).
- `render_owls.py` (yeni mərhələ, `check_bgs`-dən sonra): hər səhnə üçün edits çağırışı (referans +
  `OWL_STYLE` + action), alpha ilə kəsilir → `owl/scNN.png`. Sonra vision hakimi (gpt-4o): `same_character`,
  `full_body`, `writing`, `people`, `extra_owls`. Pis → yenidən (maks 3 cəhd); yenə pis → fayl silinir və
  həmin səhnədə köhnə poz sprite-ı qalır. Hesabat `owl_qa.json`. Limit: `RateLimiter` 5 şəkil/dəq.
- `remotion_build`: `owl/scNN.png` varsa səhnənin pozu `scNN` (ölçü şəkildən, `flippable=False`);
  yoxdursa əvvəlki poz. `Owl.tsx` dəyişmir (sağda, sabit).
- Köhnə epizodlar (`owl_action` yoxdur) → mərhələ heç nə çəkmir, köhnə davranış.

## 2. AI musiqi (HF girişi açılandan sonra)
- `music_gen.py` (lokal GPU, Stable Audio Open, ayrı venv): epizoda 4–6 fərqli sakit instrumental ~45 s
  hissə → crossfade → `Episodes/<slug>/music.wav`. `--music` verilməyibsə pipeline bunu istifadə edir.
- CC BY trekləri, `credits.json`, description istinadı silinir.

## Xəta/emniyyət
- Bayquş çəkilmirsə/hakim xətasıdırsa pipeline dayanmır — köhnə poz.
- Musiqi yaradılmırsa video musiqisiz yox, mərhələ xəta verir (retry 2 dəfə, sonra dayanır).

## Test
- TDD: `owl_action` planda; edits multipart; alpha kəsimi; hakim parse; retry/fallback məntiqi;
  `episode_props` səhnə bayquşu; STAGES sırası; musiqi crossfade uzunluğu.
- E2E: bir test videosu, kadr yoxlaması.
