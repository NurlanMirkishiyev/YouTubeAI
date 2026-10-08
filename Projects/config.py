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

# Faza 5.1 (istifadeci 2026-10-07): butun videolarda default ACIQ; sondurmek yalniz istifadeci qerari ile.
# Test: tests/test_defaults.py (False olsa dusur).
CASE_MODEL = True        # strukturlu case modeli + deterministik qerar hesabi (quality_gate model_result teleb edir)
SFX = True               # whoosh/pop/tick/boom qati (remotion_build master)
NUMBER_OVERLAY = True    # foto sehnesinde danisilan reqemin count-up overlay-i
TYPEWRITER = True        # cold open typewriter (motion.plan_motion)
MOTION_VARIANTS = True   # epizoda hereket plani: theme, variantlar, kecidler (motion.py)
REQUIRED_KINDS = ("table", "threshold", "timeseries", "usmap")   # visuals.KINDS-de olmalidir


def _env(name: str) -> str:
    load_env()
    return os.environ.get(name, "").strip()


def lead_magnet_url() -> str:
    return _env("LEAD_MAGNET_URL")


def affiliate_links() -> list[str]:
    return [x.strip() for x in _env("AFFILIATE_LINKS").split(LINK_SEP) if x.strip()]
