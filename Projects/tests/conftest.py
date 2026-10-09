"""Test importlari: Projects, Projects/_ffmpeg, Projects/sprites sys.path-e elave olunur."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
for p in (PROJ, os.path.join(PROJ, "_ffmpeg"), os.path.join(PROJ, "sprites")):
    if p not in sys.path:
        sys.path.insert(0, p)
if HERE not in sys.path:
    sys.path.insert(0, HERE)        # testler bir-birinin fixture-larini (MODEL, PLAN) import edir

import urllib.request  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """#136 (2026-10-10): kod deyisikliyinden sonra bir test LLM yolunu real OpenAI-ye cixardi (pullu, yavas).
    Testler sebekeye cixmir - real urlopen bloklanir; oz urlopen-ini evez eden test bunu ustune yazir."""
    def blocked(*a, **k):
        raise RuntimeError("test sebekeye cixmaga calisdi - LLM/fetch parametr kimi evez olunmalidir")
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
