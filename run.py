"""python run.py "<ssenari faylı>"  |  python run.py --resume <slug>   (Projects\.venv-e ozu kecir)"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, "Projects", ".venv", "Scripts", "python.exe")

if os.path.abspath(sys.executable).lower() != VENV.lower() and os.path.isfile(VENV):
    raise SystemExit(subprocess.call([VENV, "-u", __file__, *sys.argv[1:]]))
sys.path.insert(0, os.path.join(ROOT, "Projects"))
import pipeline  # noqa: E402

pipeline.main(sys.argv[1:])
