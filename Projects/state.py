"""Episodes\\<slug>\\state.json - merhele statuslari. Yazilis atomikdir (tmp + os.replace);
yenileme yeni dict qaytarir. Hakim hemise fayl sistemidir - bax stages.done/verify."""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_state(topic: str, slug: str, stage_names: list[str]) -> dict:
    return {"topic": topic, "slug": slug, "created": now_iso(),
            "stages": {n: {"status": "pending", "started": None, "finished": None, "error": None}
                       for n in stage_names}}


def read_state(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_state(path: str, state: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def with_stage(state: dict, stage: str, **fields) -> dict:
    new = copy.deepcopy(state)
    new["stages"][stage] = {**new["stages"].get(stage, {}), **fields}
    return new
