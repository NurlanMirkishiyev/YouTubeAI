"""Addim 09: plan.md 2.2 - eyni personaj 10 sehnede. Netice: Output/consistency_test/"""
import subprocess, shutil, sys, os
BASE = "cute 3D cartoon owl mascot, brown and cream feathers, big round black glasses, navy blue business suit, white shirt, yellow tie, {scene}, Pixar style 3D render, soft studio lighting"
SCENES = {
 "01_board":   "standing beside a whiteboard, explaining a bar chart, pointing with one wing, friendly teaching expression",
 "02_laptop":  "sitting at a desk working on a laptop, focused expression, modern office",
 "03_contract":"holding a signed contract document with a pen, proud expression",
 "04_thinking":"thinking pose with wing on chin, question marks floating above head, curious expression",
 "05_happy":   "jumping with joy, wings raised, big smile, confetti in the air",
 "06_teaching":"standing in front of a small audience of business people in a classroom, lecturing, confident expression",
 "07_calc":    "using a large calculator at a desk with coins and receipts, concentrating",
 "08_building":"standing in front of a modern glass office building, waving, sunny day",
 "09_ai":      "presenting a glowing AI neural network diagram on a screen, explaining, futuristic office",
 "10_two":     "explaining a topic to two small business owners at a cafe table, friendly conversation",
}
PY = r"C:\YouTubeAI\ComfyUI\.venv\Scripts\python.exe"
OUT = r"C:\YouTubeAI\Output\consistency_test"
for key, scene in SCENES.items():
    r = subprocess.run([PY, r"C:\YouTubeAI\Projects\run_workflow.py", r"C:\YouTubeAI\Projects\_workflows\owl_ipadapter_v2_api.json",
                        "--set", "POS=" + BASE.format(scene=scene), "--set", "SEED=7", "--set", f"PREFIX=ct_{key}", "--wait"],
                       capture_output=True, text=True)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    fn = line.split("-> ")[-1] if "-> " in line else None
    if fn:
        shutil.copyfile(fr"C:\YouTubeAI\ComfyUI\output\{fn}", fr"{OUT}\{key}.png")
    print(key, line, flush=True)
