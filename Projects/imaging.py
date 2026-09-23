"""Ortaq sekil yardimcilari."""
from __future__ import annotations

from PIL import Image


def cover_box(w: int, h: int, tw: int, th: int) -> tuple[int, int, int, int]:
    """Merkezden kesim qutusu: (w, h) -> tw:th nisbeti, hec bir bos zolaq qalmadan."""
    target = tw / th
    if w / h > target:
        nw = round(h * target)
        left = (w - nw) // 2
        return (left, 0, left + nw, h)
    nh = round(w / target)
    top = (h - nh) // 2
    return (0, top, w, top + nh)


def fit_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
    return img.crop(cover_box(img.width, img.height, tw, th)).resize((tw, th), Image.LANCZOS)
