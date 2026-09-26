from PIL import Image

import render_bgs as rb
import scene_plan
from llm import LLMError


def test_prompt_has_house_style_scene_and_free_side_for_the_owl():
    p = rb.build_prompt("a robot arm stacking cubes", "right")
    assert p.startswith(rb.STYLE) and "a robot arm stacking cubes" in p
    assert "empty space on the right side" in p and "no text" in p.lower()
    assert "empty space on the left side" in rb.build_prompt("x", "left")


def test_crop_to_16x9_keeps_full_width_and_center():
    im = Image.new("RGB", (1536, 1024))
    im.paste((255, 0, 0), (0, 0, 1536, 80))          # yuxari zolaq kesilmelidir
    out = rb.crop_16x9(im)
    assert out.size == (1536, 864)
    assert out.getpixel((10, 0)) != (255, 0, 0)


def test_render_one_saves_png_and_uses_fallback_when_prompt_is_refused(tmp_path):
    seen = []

    def gen(prompt):
        seen.append(prompt)
        if len(seen) == 1:
            raise LLMError("HTTP 400: moderation_blocked")
        img = Image.new("RGB", (1536, 1024), (0, 128, 0))
        import io
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    dest = tmp_path / "sc01.png"
    rb.render_one({"bg_prompt": "a scary thing", "pos": "right"}, str(dest), gen)
    with Image.open(dest) as im:
        assert im.size == (1536, 864)
    assert "a scary thing" in seen[0] and scene_plan.FALLBACK_BG in seen[1]


# E2E ep4: hesabin limiti deqiqede 5 sekil; 4 paralel sorgu + 1-4 s backoff 97-den 55-ni itirdi
class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def test_rate_limiter_allows_at_most_n_starts_per_window():
    c = FakeClock()
    lim = rb.RateLimiter(per_min=2, now=c.now, sleep=c.sleep)
    lim.acquire()
    lim.acquire()
    assert c.t == 0.0
    lim.acquire()                      # ucuncu - birincinin pencereden cixmasini gozleyir
    assert c.t >= 60.0


def test_retry_waits_as_long_as_the_api_asks_on_429():
    c = FakeClock()
    calls = []

    def gen(prompt):
        calls.append(prompt)
        if len(calls) < 3:
            raise LLMError('HTTP 429: {"message": "Rate limit ... Please try again in 12s."}')
        return b"png"

    assert rb.with_429_retry(gen, sleep=c.sleep)("p") == b"png"
    assert len(calls) == 3 and all(s >= 12 for s in c.slept)


def test_retry_does_not_swallow_other_errors():
    def gen(prompt):
        raise LLMError("HTTP 400: moderation_blocked")
    try:
        rb.with_429_retry(gen, sleep=lambda s: None)("p")
    except LLMError as e:
        assert "moderation" in str(e)
    else:
        raise AssertionError("xeta udulmamalidir")
