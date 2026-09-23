"""Character sheet -> fonsuz sprite PNG-ler (100% orijinal personaj, generativ deyisiklik yoxdur).
Istifade:
  Projects/.venv/Scripts/python Projects/sprites/make_sprites.py [--sheet sheet.png] [--out dir] [--only front happy]
Metod (deterministik, AI maska yoxdur):
  1. pozani sheet-den kes
  2. ag/aciq-boz fon pikselleri (parlaqliq > LUM_MIN, boz) icinde yalniz KENARA baglanan sahe = fon
     (ag koynek, lovhe sethi, eynek icleri qapali oldugu ucun qorunur)
  3. qalan sahede en boyuk baglanti komponenti = personaj ("?" kimi ayri isareler atilir)
  4. alfa kenari 1 px yumsaldilir, seffaf kenar kesilir
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

SHEET = r"C:\YouTubeAI\Character\ELI5_Owl\eli5_owl_ref.png"
OUT = r"C:\YouTubeAI\Character\ELI5_Owl\sprites"
# (x0, y0, x1, y1) 1448x1086 sheet uzerinde; yazi etiketleri kenarda qalir
BOXES = {
    "front":     (15, 160, 300, 578),
    "three_q":   (315, 160, 585, 578),
    "side":      (585, 170, 800, 578),
    "happy":     (825, 235, 1015, 505),
    "thinking":  (1030, 230, 1230, 505),
    "confident": (1240, 230, 1440, 505),
    "chart":     (15, 655, 440, 995),
    "box":       (480, 625, 780, 995),
}
# Sheet uzerinde (x0, y0, x1, y1) sahelari: personaja BITISIK olan artiq isareler
# ("!", "?" ve s.) — maskadan evvel fon kimi isaretlenir, boylece en boyuk komponente qosulmur.
CUTS = {
    "confident": [(1368, 230, 1440, 292)],   # bas ustundeki "!" isaresi
}
LUM_MIN = 200      # fon namizedi: parlaqliq bu heddden yuxari
GRAY_MAX = 22      # ve kanal ferqi (max-min) bu heddden asagi (rengsiz)
PAD = 2


def background_mask(rgb: np.ndarray) -> np.ndarray:
    lum = rgb.mean(axis=2)
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    cand = (lum > LUM_MIN) & (spread < GRAY_MAX)
    labels, n = ndimage.label(cand)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border = border[border != 0]
    return np.isin(labels, border)


def largest_component(fg: np.ndarray) -> np.ndarray:
    labels, n = ndimage.label(fg)
    if n == 0:
        raise RuntimeError("personaj tapilmadi")
    sizes = ndimage.sum(fg, labels, range(1, n + 1))
    return labels == (int(np.argmax(sizes)) + 1)


def extract(sheet: Image.Image, box: tuple[int, int, int, int],
            cuts: list[tuple[int, int, int, int]] | None = None) -> Image.Image:
    crop = sheet.crop(box).convert("RGB")
    rgb = np.asarray(crop).astype(np.int16)
    fg = ~background_mask(rgb)
    for cx0, cy0, cx1, cy1 in cuts or ():
        x0, y0 = max(0, cx0 - box[0]), max(0, cy0 - box[1])
        x1, y1 = min(crop.width, cx1 - box[0]), min(crop.height, cy1 - box[1])
        if x0 < x1 and y0 < y1:
            fg[y0:y1, x0:x1] = False
    fg = largest_component(fg)
    fg = ndimage.binary_fill_holes(fg)
    alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    out = crop.convert("RGBA")
    out.putalpha(alpha)
    x0, y0, x1, y1 = alpha.getbbox()
    return out.crop((max(0, x0 - PAD), max(0, y0 - PAD), min(out.width, x1 + PAD), min(out.height, y1 + PAD)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    if not os.path.isfile(a.sheet):
        raise SystemExit("sheet tapilmadi: " + a.sheet)
    os.makedirs(a.out, exist_ok=True)
    sheet = Image.open(a.sheet)
    meta_path = os.path.join(a.out, "sprites.json")
    meta = {}
    if a.only and os.path.isfile(meta_path):   # qismi calisdirmada kohne qeydler itmesin
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    for name, box in BOXES.items():
        if a.only and name not in a.only:
            continue
        spr = extract(sheet, box, CUTS.get(name))
        path = os.path.join(a.out, f"{name}.png")
        spr.save(path)
        meta[name] = {"file": path, "w": spr.width, "h": spr.height}
        print(f"{name:10s} {spr.width}x{spr.height} -> {path}")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
