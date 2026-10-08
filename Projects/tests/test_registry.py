"""Faza 5.4 (istifadeci 2026-10-07): progress.md "Problemler reyestri"-ndeki HER setir movcud bir teste istinad edir
(`test_<fayl>.py::test_<ad>`). Istinadsiz ve ya movcud olmayan teste gedən setir -> test xetasi."""
import os
import re

PROGRESS = r"C:\YouTubeAI\progress.md"
TESTS = os.path.dirname(os.path.abspath(__file__))
REF = re.compile(r"(test_\w+\.py)::(test_\w+)")
ROW = re.compile(r"^\|\s*(\d+|—)\s*\|")


def _rows() -> list[str]:
    lines = open(PROGRESS, encoding="utf-8").read().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## Problemlər reyestri"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    return [ln for ln in lines[start:end] if ROW.match(ln)]


def test_registry_is_not_empty():
    assert len(_rows()) >= 80


def test_every_registry_row_references_a_test():
    missing = [ROW.match(r).group(1) for r in _rows() if not REF.search(r)]
    assert not missing, f"istinadsiz reyestr setirleri: {missing}"


def test_every_reference_points_to_an_existing_test():
    bad = []
    cache: dict[str, str] = {}
    for row in _rows():
        for path, name in REF.findall(row):
            full = os.path.join(TESTS, path)
            if path not in cache:
                cache[path] = open(full, encoding="utf-8").read() if os.path.isfile(full) else ""
            if not re.search(rf"^def {name}\(", cache[path], re.M):
                bad.append(f"#{ROW.match(row).group(1)}: {path}::{name}")
    assert not bad, bad
