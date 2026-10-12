import ratelimit


def test_sixth_call_waits_until_the_window_frees_up():
    now = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        now[0] += s
    lim = ratelimit.RateLimiter(5, 60.0, clock=lambda: now[0], sleep=sleep)
    for _ in range(5):
        lim.acquire()
    assert slept == []
    lim.acquire()
    assert slept and abs(sum(slept) - 60.0) < 0.1


def test_default_is_five_per_minute():
    assert ratelimit.IMAGES_PER_MIN == 5 and ratelimit.IMAGE_LIMITER.calls == 5
