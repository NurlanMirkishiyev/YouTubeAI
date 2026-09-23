"""ComfyUI heyat dovru. Git Bash-dan .bat isleyir deyil - birbasa venv python ile main.py.
ComfyGuard: pipeline ComfyUI-ni ozu qaldiribsa, artiq lazim olmayanda (TTS/Whisper-den evvel)
dayandirir ki 8 GB VRAM azad olsun. Kenardan acilmis ComfyUI-ye toxunmur."""
from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request

COMFY_DIR = r"C:\YouTubeAI\ComfyUI"
COMFY_PY = r"C:\YouTubeAI\ComfyUI\.venv\Scripts\python.exe"
API = "http://127.0.0.1:8188"
START_TIMEOUT_S = 120


def is_up(timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen(f"{API}/system_stats", timeout=timeout).read()
        return True
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def start(log_path: str) -> subprocess.Popen:
    log = open(log_path, "a", encoding="utf-8")
    return subprocess.Popen([COMFY_PY, "main.py", "--listen", "127.0.0.1", "--port", "8188", "--lowvram"],
                            cwd=COMFY_DIR, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def wait_up(timeout_s: float = START_TIMEOUT_S, poll_s: float = 2.0, probe=is_up, sleep=time.sleep) -> bool:
    waited = 0.0
    while True:
        if probe():
            return True
        if waited + poll_s > timeout_s:
            return False
        sleep(poll_s)
        waited += poll_s


def stop_process(proc, timeout_s: float = 20) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()


class ComfyGuard:
    def __init__(self, log_path: str, probe=is_up, launcher=start):
        self.log_path = log_path
        self.probe = probe
        self.launcher = launcher
        self.proc = None

    def before(self, remaining: list) -> str | None:
        """Novbeti merheleden evvel cagirilir. Xeta mesaji ve ya None qaytarir."""
        if remaining and remaining[0].needs_comfy:
            if self.probe():
                return None
            self.proc = self.launcher(self.log_path)
            if not wait_up(probe=self.probe):
                return f"ComfyUI {START_TIMEOUT_S} s-de qalxmadi - bax: {self.log_path}"
        elif self.proc is not None and not any(s.needs_comfy for s in remaining):
            self.stop()
        return None

    def stop(self) -> None:
        if self.proc is not None:
            stop_process(self.proc)
            self.proc = None
