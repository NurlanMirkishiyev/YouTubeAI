"""Test importlari: Projects, Projects/_ffmpeg, Projects/sprites sys.path-e elave olunur."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
for p in (PROJ, os.path.join(PROJ, "_ffmpeg"), os.path.join(PROJ, "sprites")):
    if p not in sys.path:
        sys.path.insert(0, p)
