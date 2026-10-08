"""Pipeline konfiqurasiyasi (Faza 4/5, istifadeci 2026-10-07).
Monetizasiya linkleri `.env`-den oxunur (kodda URL yoxdur): bos olarsa description-a heç ne yazilmir.
  LEAD_MAGNET_URL=https://...                 (pulsuz checklist / lead magnet)
  AFFILIATE_LINKS=Ad - https://... | Ad - https://...
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import load_env  # noqa: E402

LINK_SEP = "|"


def _env(name: str) -> str:
    load_env()
    return os.environ.get(name, "").strip()


def lead_magnet_url() -> str:
    return _env("LEAD_MAGNET_URL")


def affiliate_links() -> list[str]:
    return [x.strip() for x in _env("AFFILIATE_LINKS").split(LINK_SEP) if x.strip()]
