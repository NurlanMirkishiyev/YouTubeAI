"""ComfyUI upscale modeli ile sekil boyutme (4x-UltraSharp fonlar, RealESRGAN anime sprite-ler).
ComfyUI serveri isleyir olmalidir; ImageUpscaleWithModel 8 GB VRAM-da ozu tile-layir."""
from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_workflow import submit, wait  # noqa: E402

COMFY_IN = r"C:\YouTubeAI\ComfyUI\input"
COMFY_OUT = r"C:\YouTubeAI\ComfyUI\output"
WORKFLOW = r"C:\YouTubeAI\Projects\_workflows\upscale_4x_api.json"


API = "http://127.0.0.1:8188"


def require_server() -> None:
    try:
        urllib.request.urlopen(f"{API}/system_stats", timeout=5).read()
    except (urllib.error.URLError, TimeoutError) as e:
        raise SystemExit(f"ComfyUI cavab vermir ({API}) - run_comfyui.bat isledin.  {e}")


def build_workflow(image_name: str, model: str, prefix: str) -> dict:
    with open(WORKFLOW, encoding="utf-8") as f:
        text = f.read()
    text = (text.replace("__IMAGE__", image_name).replace("__MODEL__", model)
                .replace("__PREFIX__", prefix))
    return json.loads(text)


def upscale_file(src: str, model: str, prefix: str, timeout_s: int = 900) -> str:
    """src -> ComfyUI/input/<prefix>.png -> upscale -> ComfyUI/output-daki fayl yolu."""
    name = f"{prefix}.png"
    shutil.copyfile(src, os.path.join(COMFY_IN, name))
    files = wait(submit(build_workflow(name, model, prefix)), timeout_s=timeout_s)
    out = os.path.join(COMFY_OUT, files[-1])
    if not os.path.isfile(out):
        raise RuntimeError("upscale cixisi tapilmadi: " + out)
    return out
