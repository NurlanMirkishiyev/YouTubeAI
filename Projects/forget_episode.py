"""Hazir video tesdiqlenende pipeline-in o video barede saxladigi her seyi silir (istifadeci 2026-09-29):
Episodes\\<slug>\\ (skript, fonlar, ses, state, loglar) + Episodes\\_run_*.log(.err) (ilk setri bu epizodu gosterir).
Hazir_Videolar\\<slug>\\ (istifadeciye verilen paket) toxunulmur.
  Projects\\.venv\\Scripts\\python Projects\\forget_episode.py <slug>"""
import argparse
import os
import re
import shutil
import sys

from script_gen import EPISODES

SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _log_episode(path: str) -> str | None:
    """Run loqunun ilk setri: FAZA F: '<movzu>' -> <epizod qovlugu>."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            first = f.readline()
    except OSError:
        return None
    return first.rsplit("->", 1)[1].strip() if first.startswith("FAZA F:") and "->" in first else None


def run_logs(slug: str, episodes: str) -> list[str]:
    """Bu epizoda aid _run_*.log ve eyni adli .err fayllari (qisa adli resume loqlari da)."""
    ep = os.path.normcase(os.path.join(episodes, slug))
    found = []
    for name in os.listdir(episodes):
        if not (name.startswith("_run_") and name.endswith(".log")):
            continue
        path = os.path.join(episodes, name)
        target = _log_episode(path)
        if name == f"_run_{slug}.log" or (target and os.path.normcase(target) == ep):
            found.append(path)
            if os.path.isfile(path + ".err"):
                found.append(path + ".err")
    return found


def forget(slug: str, episodes: str = EPISODES) -> list[str]:
    if not SAFE_SLUG.match(slug or ""):
        raise ValueError(f"tehlukesiz olmayan slug: {slug!r}")
    ep = os.path.join(episodes, slug)
    if not os.path.isdir(ep):
        raise FileNotFoundError(f"epizod yoxdur: {ep}")
    removed = run_logs(slug, episodes)
    for path in removed:
        os.remove(path)
    shutil.rmtree(ep)
    return [ep, *removed]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="hazir videonun pipeline yaddasini sil")
    ap.add_argument("slug")
    a = ap.parse_args(argv)
    for path in forget(a.slug):
        print("silindi:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
