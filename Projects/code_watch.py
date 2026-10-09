"""#126 (istifadeci 2026-10-10): pipeline kohne kodla islemesin.
Evvel: kod duzelisi edilende hele isleyen merhele (ve 30 s sonraki retry) kohne kodla davam edirdi - netice
kohne xetani tekrarlayirdi, el ile oldurub --resume etmek lazim gelirdi.
Indi: orkestr kodun barmaq izini izleyir; deyisiklik sabitlesende (redakte bitende) isleyen merhele dayandirilir
ve run ozunu `--resume` ile yeniden acir - butun modullar yeni koddan yuklenir, retry budcesi xerclenmir."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WATCH_ROOTS = (HERE, os.path.join(ROOT, "Remotion", "src"))
WATCH_EXT = (".py", ".ts", ".tsx")
SKIP_DIRS = {"tests", "__pycache__", ".venv", "node_modules"}
DEBOUNCE_S = 20.0           # bir nece fayl redakte olunur - yalniz sabit (bitmis) deyisiklik sayilir
POLL_S = 5.0
CODE_CHANGED = -126         # wait_or_stop: merhele kod deyisdiyi ucun dayandirildi
CODE_CHANGED_MSG = "KOD DEYISDI - run yeni kodla yeniden acilir"


class Relaunch(Exception):
    """run_pipeline -> main: run ozunu --resume ile yeniden acmalidir."""

    def __init__(self, from_stage: str | None):
        super().__init__(from_stage)
        self.from_stage = from_stage


def fingerprint(roots=WATCH_ROOTS) -> str:
    """Izlenen kod fayllarinin mezmun hash-i (testler, venv, cache xaric)."""
    h = hashlib.sha256()
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
            for name in sorted(files):
                if not name.endswith(WATCH_EXT):
                    continue
                p = os.path.join(d, name)
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                h.update(os.path.relpath(p, root).encode("utf-8"))
                h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


class CodeWatch:
    """changed(): kod run baslayandan deyisib VE yeni hali `debounce` saniye sabitdir."""

    def __init__(self, fingerprint=fingerprint, clock=time.monotonic, debounce: float = DEBOUNCE_S):
        self._fp, self._clock, self._debounce = fingerprint, clock, debounce
        self._start = fingerprint()
        self._seen: str | None = None
        self._since = 0.0

    def changed(self) -> bool:
        now = self._fp()
        if now == self._start:
            self._seen = None
            return False
        if now != self._seen:
            self._seen, self._since = now, self._clock()
            return False
        return self._clock() - self._since >= self._debounce

    __call__ = changed


def kill_tree(proc) -> None:
    """Merhele alt-proses agaci (venv launcher + python + render) - Windows-da taskkill /T."""
    if os.name == "nt":
        subprocess.call(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.kill()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass


def wait_or_stop(proc, changed, poll: float = POLL_S, kill=kill_tree) -> int:
    """Proses bitene qeder gozle; kod deyisib sabitleserse onu dayandir ve CODE_CHANGED qaytar."""
    while True:
        try:
            return proc.wait(timeout=poll)
        except subprocess.TimeoutExpired:
            if changed():
                kill(proc)
                return CODE_CHANGED


def relaunch_cmd(run_py: str, slug: str, from_stage: str | None) -> list[str]:
    return [sys.executable, "-u", run_py, "--resume", slug] + (["--from", from_stage] if from_stage else [])
