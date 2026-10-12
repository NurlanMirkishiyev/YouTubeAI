"""Her sehnenin bayqusu: gpt-image-2 edit + referans sprite (gorunus deyismir), magenta fonda cekilir, lokal silinir.
Alinmasa retry, tehlukesizlik reddinde poza eyni movzuda yeniden yazilir; tukense merhele dayanir (sprite ile evez
olunmur, --resume yeniden cekir)."""
from __future__ import annotations

import io
import json
import os

import numpy as np
from PIL import Image

import generate
import llm
import ratelimit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWL_REF = os.path.join(ROOT, "Character", "ELI5_Owl", "sprites_hd", "front.png")
PAD = 6                  # alpha kesiminden sonra kenar (px) - kontur kesilmesin
ALPHA_MIN = 16
CHARACTER = ("The exact same cartoon owl character as in the reference image: same brown feathers and "
             "feather tuft, same round black glasses, same navy suit, white shirt, yellow tie and brown belt, "
             "same proportions, face and 3D Pixar-like art style.")
RULES = ("Only this one owl (plus the single prop if mentioned). Full body from head to feet, feet visible, "
         "standing, centered. Background: a perfectly flat, uniform, solid pure magenta (#FF00FF) colour "
         "filling the whole image - no gradient, no floor, no shadow, no texture, no checkerboard. "
         "Nothing magenta or pink on the owl or the prop. No text, no letters, no people, no other animals.")
KEY_BORDER, KEY_SPREAD_MAX, KEY_DIST, KEY_SOLID, KEY_MIN_ALPHA = 4, 0.05, 40.0, 0.12, 0.06


def owl_prompt(action: str) -> str:
    return f"{CHARACTER} New pose for this scene: {action}. {RULES}"


def key_out(im: Image.Image) -> Image.Image:
    """Bircins magenta fonu seffaf edir. Fon butun sekilde silinir (suse banka icinden gorunen fon da),
    yarimseffaf kenarda fon rengi cixarilir (unmix) - cehrayi haşiye qalmir. Artiq seffaf sekil toxunulmur.
    Fon magenta / bircins deyilse ValueError -> sekil cekilmemis sayilir, yeniden cekilir."""
    if im.mode in ("RGBA", "LA", "P") and "A" in im.convert("RGBA").getbands():
        alpha = np.asarray(im.convert("RGBA").getchannel("A"))
        edge = np.concatenate([alpha[:KEY_BORDER].ravel(), alpha[-KEY_BORDER:].ravel(),
                               alpha[:, :KEY_BORDER].ravel(), alpha[:, -KEY_BORDER:].ravel()])
        if np.median(edge) < 16:
            return im.convert("RGBA")
    c = np.asarray(im.convert("RGB")).astype(np.float64)
    border = np.concatenate([c[:KEY_BORDER].reshape(-1, 3), c[-KEY_BORDER:].reshape(-1, 3),
                             c[:, :KEY_BORDER].reshape(-1, 3), c[:, -KEY_BORDER:].reshape(-1, 3)])
    k = np.median(border, axis=0)
    if not (k[0] > 180 and k[2] > 180 and k[1] < 90):
        raise ValueError(f"fon magenta deyil: {tuple(int(v) for v in k)}")
    spread = float(np.mean(np.linalg.norm(border - k, axis=1) > KEY_DIST))
    if spread > KEY_SPREAD_MAX:
        raise ValueError(f"fon bircins deyil ({spread:.0%} ferqli kenar pikseli)")
    km = min(k[0], k[2]) - k[1]
    m = np.minimum(c[..., 0], c[..., 2]) - c[..., 1]
    a = np.where(m <= KEY_SOLID * km, 1.0, np.clip(1.0 - m / km, 0.0, 1.0))
    a[a < KEY_MIN_ALPHA] = 0.0
    safe = np.where(a > 0, a, 1.0)[..., None]
    fg = np.clip((c - (1.0 - a)[..., None] * k) / safe, 0, 255)
    out = np.dstack([fg, a * 255.0]).round().astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def trim_alpha(im: Image.Image) -> Image.Image:
    """Seffaf kenarlari kesir - ekranda olcu bayqusun ozune gore hesablanir, bos sahe ile yox."""
    im = im.convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a >= ALPHA_MIN else 0).getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(0, l - PAD), max(0, t - PAD), min(im.width, r + PAD), min(im.height, b + PAD)))


def _one(path: str, action: str, edit, limiter, rewrite) -> None:
    def draw(a: str) -> None:
        if limiter:
            limiter.acquire()
        im = trim_alpha(key_out(Image.open(io.BytesIO(edit(owl_prompt(a), OWL_REF)))))
        tmp = generate.tmp_path(path)
        im.save(tmp)
        os.replace(tmp, path)
    generate.with_retry(draw, action, rewrite=rewrite, label=f"bayqus {os.path.basename(path)}")


def render_owls(ep: str, edit=None, workers: int = 3, limiter=ratelimit.IMAGE_LIMITER,
                rewrite=llm.rewrite_safe) -> None:
    edit = edit or (lambda p, r: llm.edit_image(p, r))
    with open(os.path.join(ep, "scenes.json"), encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.join(ep, "owl"), exist_ok=True)
    todo = [s for s in data["scenes"] if not os.path.isfile(os.path.join(ep, "owl", f"sc{s['n']:02d}.png"))]
    generate.run_parallel(lambda s: _one(os.path.join(ep, "owl", f"sc{s['n']:02d}.png"),
                                         s.get("owl") or "standing and explaining, friendly", edit, limiter, rewrite),
                          todo, workers)
    print(f"  bayqus: {len(todo)} sehne", flush=True)
