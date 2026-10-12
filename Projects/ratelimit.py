"""Ortaq sliding-window limiter: gpt-image limiti 5 sekil/deq (thread-safe)."""
from __future__ import annotations

import threading
import time

IMAGES_PER_MIN = 5
WINDOW = 60.0


class RateLimiter:
    def __init__(self, calls: int = IMAGES_PER_MIN, window: float = WINDOW,
                 clock=time.monotonic, sleep=time.sleep) -> None:
        self.calls, self.window, self._clock, self._sleep = calls, window, clock, sleep
        self._stamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                self._stamps = [t for t in self._stamps if now - t < self.window]
                if len(self._stamps) < self.calls:
                    self._stamps.append(now)
                    return
                wait = self.window - (now - self._stamps[0])
            self._sleep(max(wait, 0.01))


IMAGE_LIMITER = RateLimiter()
