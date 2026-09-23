"""FAZA F 3.1 - sprites\\*.png -> RealESRGAN anime 4x -> sprites_hd\\*.png (+ <ad>_shadow.png).
RGB ESRGAN ile, alpha ayrica lanczos ile boyudulur, sonra erode (ag halo gedir).
Istifade (bir defelik, ComfyUI isleyir olmalidir):
  Projects\\.venv\\Scripts\\python Projects\\sprites\\upscale_sprites.py
Boyuk character sheet gelende: make_sprites.py -> bu skript yeniden.
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)

SRC_JSON = r"C:\YouTubeAI\Character\ELI5_Owl\sprites\sprites.json"
HD_DIR = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"
MODEL = "RealESRGAN_x4plus_anime_6B.pth"
ERODE_PX = 3             # HD miqyasinda (~1 px orijinalda)
SHADOW_W_RATIO = 0.70    # kolge eni / sprite eni
SHADOW_ASPECT = 0.18     # ellips hundurluyu / eni
SHADOW_BLUR = 18
SHADOW_OPACITY = 0.35
CUT_RATIO = 0.60         # alt hissede setrin bu qederinden cox hissesi doluysa sprite kesikdir
CUT_PROBE = 0.008        # yoxlama setri: dolu hissenin altindan hundurluyun bu payi qeder yuxari


def finish_alpha(alpha: Image.Image, size: tuple[int, int], erode_px: int) -> Image.Image:
    a = alpha.convert("L").resize(size, Image.LANCZOS)
    if erode_px > 0:
        a = a.filter(ImageFilter.MinFilter(2 * erode_px + 1))
    return a.filter(ImageFilter.GaussianBlur(0.8))


def is_cut_at_bottom(alpha: Image.Image, ratio: float = CUT_RATIO) -> bool:
    """Doldurulmus hissenin altina yaxin setir genis ve dolu olarsa sprite 'bust'-dur
    (ayaqsiz govde - kadrin altina yapisir). Tam bedende orada yalniz ayaqlar olur (<= ~36%).
    Olculmus: bust 0.74-0.81, tam beden 0.19-0.36."""
    solid = alpha.convert("L").point(lambda v: 255 if v > 128 else 0)
    box = solid.getbbox()
    if box is None:
        return False
    y = max(box[1], box[3] - 1 - round(CUT_PROBE * alpha.height))
    filled = sum(1 for x in range(box[0], box[2]) if solid.getpixel((x, y)))
    return filled / (box[2] - box[0]) > ratio


def compose_rgba(rgb: Image.Image, alpha: Image.Image) -> Image.Image:
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def make_shadow(width: int) -> Image.Image:
    ew = round(width * SHADOW_W_RATIO)
    eh = max(4, round(ew * SHADOW_ASPECT))
    pad = SHADOW_BLUR * 3
    mask = Image.new("L", (width, eh + 2 * pad), 0)
    x0 = (width - ew) // 2
    ImageDraw.Draw(mask).ellipse((x0, pad, x0 + ew, pad + eh), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)).point(
        lambda v: round(v * SHADOW_OPACITY))
    shadow = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    shadow.putalpha(mask)
    return shadow


def upscale_sprite(name: str, src: str) -> dict:
    from upscale import upscale_file  # ComfyUI klienti yalniz real isde lazimdir
    out = upscale_file(src, MODEL, f"sprite_{name}")
    with Image.open(out) as up, Image.open(src) as orig:
        rgb = up.convert("RGB")
        alpha = finish_alpha(orig.getchannel("A"), rgb.size, ERODE_PX)
    hd = compose_rgba(rgb, alpha)
    dest = os.path.join(HD_DIR, f"{name}.png")
    hd.save(dest)
    shadow = os.path.join(HD_DIR, f"{name}_shadow.png")
    bust = is_cut_at_bottom(alpha)
    if bust:                      # ayaqsiz sprite-e kolge verilmir
        if os.path.isfile(shadow):
            os.remove(shadow)
    else:
        make_shadow(hd.width).save(shadow)
    os.remove(out)
    return {"file": dest, "w": hd.width, "h": hd.height, "bust": bust}


def main() -> None:
    from render_bgs import require_server
    with open(SRC_JSON, encoding="utf-8") as f:
        sprites = json.load(f)
    require_server()
    os.makedirs(HD_DIR, exist_ok=True)
    index = {}
    for name, info in sprites.items():
        index[name] = upscale_sprite(name, info["file"])
        print(f"  {name}: {info['w']}x{info['h']} -> {index[name]['w']}x{index[name]['h']}", flush=True)
    with open(os.path.join(HD_DIR, "sprites.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"OK -> {HD_DIR}")


if __name__ == "__main__":
    main()
