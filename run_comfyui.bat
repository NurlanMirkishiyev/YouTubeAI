@echo off
cd /d C:\YouTubeAI\ComfyUI
.venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188 --lowvram --preview-method auto
