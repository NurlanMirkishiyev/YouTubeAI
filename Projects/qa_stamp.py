"""Faza 5.3 (istifadeci 2026-10-07): QA hesabatlari skriptin sha256-si ile moherlenir - skript sonradan deyisibse
hesabat kohnedir ve quality_gate onu qebul etmir (math_check/script_qa-daki qayda butun hesabatlara)."""
from __future__ import annotations

import hashlib
import json
import os

KEY = "script_sha256"


def script_sha(ep: str) -> str:
    path = os.path.join(ep, "script.md")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return hashlib.sha256(f.read().strip().encode("utf-8")).hexdigest()


def stamp(ep: str, data: dict) -> dict:
    return {**data, KEY: script_sha(ep)}


def write(ep: str, name: str, data: dict, indent: int = 2) -> str:
    """Hesabati moherleyib yazir (name ep-e nisbi, alt qovluq yaradilir)."""
    path = os.path.join(ep, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stamp(ep, data), f, ensure_ascii=False, indent=indent)
    return path


def is_fresh(ep: str, rep: dict) -> bool:
    sha = script_sha(ep)
    return bool(sha) and rep.get(KEY) == sha
