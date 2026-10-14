"""Sekil cekilisi ucun ortaq: retry, tehlukesizlik reddinde prompt yeniden yazilir, tukenende xeta (evezleme YOX).
Done-fayllari atomik yazilir (*.tmp + os.replace) - yarimciq fayl merheleni bitmis gostermir."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

import llm

ATTEMPTS = 6
SIMPLER = (" [Rejected again: make it a very simple, calm, everyday scene on the same topic - no violence, "
           "no weapons, no real brands or logos, no famous people.]")
T = TypeVar("T")


class GenerationFailed(Exception):
    pass


def with_retry(fn: Callable[[str], T], prompt: str, *, rewrite: Callable[[str], str] | None, label: str,
               attempts: int = ATTEMPTS) -> T:
    last = ""
    safety = 0
    for i in range(attempts):
        try:
            return fn(prompt)
        except Exception as e:  # noqa: BLE001
            if llm.is_balance_error(e):
                raise
            last = str(e)[:160]
            print(f"  {label} cehd {i + 1}/{attempts}: {last}", flush=True)
            if llm.is_safety_error(e) and rewrite and i < attempts - 1:
                safety += 1
                try:
                    prompt = rewrite(prompt + (SIMPLER if safety > 1 else ""))
                    print(f"  {label}: prompt yeniden yazildi - {prompt[:100]}", flush=True)
                except Exception as re_err:  # noqa: BLE001
                    if llm.is_balance_error(re_err):
                        raise
                    print(f"  {label}: prompt yeniden yazilmadi ({str(re_err)[:100]})", flush=True)
    raise GenerationFailed(f"{label}: {attempts} cehdden sonra alinmadi ({last})")


def run_parallel(fn: Callable[[T], None], items: list[T], workers: int) -> None:
    """Hamisi isleyir (alinanlar saxlanir), sonra xeta varsa: balans xetasi onde, yoxsa GenerationFailed.
    Balans bitende novbedeki elementler artiq API-ye getmir."""
    broke: list[BaseException] = []

    def guarded(x: T) -> None:
        if broke:
            raise broke[0]
        try:
            fn(x)
        except Exception as e:  # noqa: BLE001
            if llm.is_balance_error(e):
                broke.append(e)
            raise
    with ThreadPoolExecutor(max(1, workers)) as pool:
        futures = [pool.submit(guarded, x) for x in items]
    errors = [f.exception() for f in futures if f.exception()]
    balance = next((e for e in errors if llm.is_balance_error(e)), None)
    if balance:
        raise balance
    if errors:
        raise GenerationFailed(f"{len(errors)} element alinmadi: " + "; ".join(str(e)[:120] for e in errors[:3]))


def tmp_path(path: str) -> str:
    base, ext = os.path.splitext(path)
    return f"{base}.tmp{ext}"


def atomic_bytes(path: str, data: bytes) -> None:
    tmp = tmp_path(path)
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def atomic_json(path: str, data) -> None:
    tmp = tmp_path(path)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def run_cmd(cmd: list[str], timeout: float, cwd: str | None = None) -> None:
    """Xarici proses (Remotion, Kokoro, Stable Audio, ffmpeg) - ilisib qalmasin: muddet kecende butun proses agaci
    (npx -> node -> chrome) oldurulur ve TimeoutExpired qaldirilir (merhele yeniden cehd edir)."""
    import subprocess
    p = subprocess.Popen(cmd, cwd=cwd)
    try:
        code = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()
        p.wait(timeout=30)
        raise
    if code:
        raise subprocess.CalledProcessError(code, cmd)
