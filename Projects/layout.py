"""Ekran zonalari (1920x1080) - Remotion komponentleri ile eyni (visuals/common.tsx AREA).
Bayqus hemise sagda, altyazi asagida: chart, xerite sayqaci ve foto reqem overlay-i bu zonalara girmir.
Qutu: (x, y, en, hundurluk)."""
from __future__ import annotations

W, H = 1920, 1080
AREA = (90, 175, 1220, 660)                 # chart sahesi (common.tsx AREA)
TITLE_H = 96
OWL_ZONE = (1370, 120, 550, 960)            # bayqus sagda (~1370 px-den), basliq setrinden asagi
OWL_MARGIN_X = 70                           # bayqusun sag kenardan mesafesi (Remotion theme.ts ile eyni)
CHART_OWL_GAP = 20                          # #86: chart sehnesinde bayqus AREA-nin sag kenarindan bu qeder sagda
CAPTION_ZONE = (0, 870, 1920, 210)          # altyazi asagida (~870 px-den)
MAP_BOX = (AREA[0] + 20, AREA[1] + TITLE_H + 30, 860, 500)        # ABS konturu
MAP_COUNTER = (AREA[0] + 900, AREA[1] + TITLE_H + 40, 300, 170)   # boyuk sayqac - xeritenin saginda
OVERLAY_BOX = (110, 240, 620, 230)          # foto sehnede reqem overlay-i: yuxari-sol (lower-third-dan asagi)


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
