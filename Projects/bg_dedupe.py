"""Tekrar kadr yoxlamasi: epizodun fonlari CLIP sekil vektorlari ile muqayise olunur.
Istifadeci (2026-09-28): tekrar kadrlar QETI olmasin. Soz esasli yoxlama (hero) peceniye/sikke/donuz
qumbarasini ferqli sozlerle tutmurdu - pricing E2E-de 6 peceniye, 3 qumbara, 2 eyni sikke kecmisdi.

MusicGen venv-inde isleyir (torch + transformers orada var):
  MusicGen\\.venv\\Scripts\\python Projects\\bg_dedupe.py Episodes\\<slug>   -> stdout: JSON {pairs, redo}
"""
from __future__ import annotations

import glob
import json
import os
import sys

MODEL = "openai/clip-vit-base-patch32"
# Namized hedd - son qerar check_bgs.confirm_duplicates (gpt-4o) verir (reyestr #31).
# Kalibrasiya: eyni sikke 0.884, iki qol saati 0.878 (tutulmali); ferqli obyektler 0.87-0.92-ye qeder cixir
DUP_SIM = 0.85


def find_duplicates(sim: list[list[float]], threshold: float = DUP_SIM) -> tuple[list[tuple[int, int]], list[int]]:
    """sim: fonlarin oxsarliq matrisi (sehne sirasi ile). Qaytarir: oxsar cutler (1-esasli) ve yeniden
    cekilmeli sehneler - her qrupda ilk sehne qalir, sonrakilar yeniden cekilir."""
    n = len(sim)
    pairs = [(i + 1, j + 1) for i in range(n) for j in range(i + 1, n) if sim[i][j] >= threshold]
    redo: set[int] = set()
    for i, j in pairs:
        if i not in redo:
            redo.add(j)
    return pairs, sorted(redo)


def similarity(paths: list[str]) -> list[list[float]]:
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    model, proc = CLIPModel.from_pretrained(MODEL), CLIPProcessor.from_pretrained(MODEL)
    images = []
    for p in paths:
        with Image.open(p) as im:
            images.append(im.convert("RGB"))
    with torch.no_grad():
        pixels = proc(images=images, return_tensors="pt")["pixel_values"]
        emb = model.visual_projection(model.vision_model(pixel_values=pixels).pooler_output)
    emb = emb / emb.norm(dim=-1, keepdim=True)
    return (emb @ emb.T).tolist()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("istifade: bg_dedupe.py <episode_dir>")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    paths = sorted(glob.glob(os.path.join(sys.argv[1], "bg", "sc*.png")))
    if not paths:
        raise SystemExit("fon yoxdur: " + os.path.join(sys.argv[1], "bg"))
    nums = [int(os.path.basename(p)[2:-4]) for p in paths]       # scNN.png -> NN
    pairs, redo = find_duplicates(similarity(paths))
    print(json.dumps({"pairs": [[nums[i - 1], nums[j - 1]] for i, j in pairs],
                      "redo": [nums[k - 1] for k in redo]}))


if __name__ == "__main__":
    main()
