"""FAZA F giris noqtesi:  python run.py "Movzu"   |   python run.py --resume <slug>
Hansi python ile cagirilsa da, ozunu Projects\\.venv ile yeniden isledir."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, "Projects", ".venv", "Scripts", "python.exe")

if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(VENV_PY):
    raise SystemExit(subprocess.call([VENV_PY, os.path.abspath(__file__), *sys.argv[1:]]))

sys.path.insert(0, os.path.join(ROOT, "Projects"))
from pipeline import main  # noqa: E402

raise SystemExit(main())
