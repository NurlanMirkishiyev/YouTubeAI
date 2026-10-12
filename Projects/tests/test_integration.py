"""Oflayn zencir: script -> plan -> images -> owl -> (ses evezine duration) -> captions -> render props.
props.json acarlari Remotion/src/types.ts ile eynidir."""
import io
import json
import os
import re

from PIL import Image

import captions
import images
import owl
import plan
import render
import script

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = """# How Free Apps Make Money

## 0:00 - 0:30 — Hook: Who Pays?
**VISUAL:** A phone on a kitchen table.

**NARRATION:**

Imagine an app that costs nothing. Only 2% of users pay. They pay about five dollars each.
Twenty thousand people pay every day. Advertising brings in the rest of the money.

## 0:30 - 1:00 — Secret #1: Ads
**VISUAL:** A busy city street with billboards.

**NARRATION:**

Advertising brought in about $196 billion of Meta's $201 billion revenue. Users see ads.
Brands pay for attention. The app stays free for you.
"""


def _png(color):
    buf = io.BytesIO()
    im = Image.new("RGB", (64, 80), color)
    if color == (255, 0, 255):
        im.paste((120, 80, 40), (20, 20, 44, 70))
    im.save(buf, "PNG")
    return buf.getvalue()


def _ask(system, user):
    nums = [int(x.split(":")[0]) for x in user.split("SCENE ")[1:]]
    return {"scenes": [{"n": n, "photo_prompt": f"photo {n}", "owl": "waving hello", "anim": [
        {"kind": "percent", "value": 2, "label": "users pay"},
        {"kind": "flow", "steps": ["Users see ads", "Brands pay"]},
        {"kind": "counter", "value": 201, "prefix": "$", "suffix": " billion", "label": "Meta revenue"},
        {"kind": "list", "items": ["Advertising", "attention"]},
        {"kind": "versus", "left": "Users", "right": "Brands"}]} for n in nums]}


def _ts_keys(type_name: str) -> set[str]:
    src = open(os.path.join(ROOT, "Remotion", "src", "types.ts"), encoding="utf-8").read()
    body = re.search(rf"export type {type_name} = \{{(.*?)\}};", src, re.S).group(1)
    return set(re.findall(r"(\w+)\s*:", body)) - {"k"}


def test_offline_chain_produces_props_matching_types_ts(tmp_path):
    md = tmp_path / "s.md"
    md.write_text(SCRIPT, encoding="utf-8")
    ep = tmp_path / "ep"
    ep.mkdir()
    data = plan.plan_scenes(script.build(str(md)), ask=_ask)
    (ep / "scenes.json").write_text(json.dumps(data), encoding="utf-8")

    images.render_photos(str(ep), gen=lambda p: _png((0, 0, 255)), workers=1, limiter=None, rewrite=None)
    owl.render_owls(str(ep), edit=lambda p, r: _png((255, 0, 255)), workers=1, limiter=None, rewrite=None)
    data = json.loads((ep / "scenes.json").read_text(encoding="utf-8"))
    for s in data["scenes"]:
        s["duration"] = 2.5
    (ep / "scenes.json").write_text(json.dumps(data), encoding="utf-8")
    captions.main(str(ep))
    render.main(str(ep), runner=lambda *a, **k: open(a[0][5], "wb").close())

    props = json.loads((ep / "props.json").read_text(encoding="utf-8"))
    assert set(props) == _ts_keys("Props")
    assert all(set(s) == _ts_keys("Scene") for s in props["scenes"])
    assert all(set(c) == _ts_keys("Caption") for c in props["captions"])
    types = [s["type"] for s in props["scenes"]]
    assert "photo" in types and "anim" in types
    for s in props["scenes"]:
        assert (s["img"] is not None) == (s["type"] == "photo")
        assert (ep / "public" / s["owl"]).is_file()
        if s["img"]:
            assert (ep / "public" / s["img"]).is_file()
        if s["type"] == "anim":
            assert s["anim"]["kind"] and "variant" in s["anim"]
    assert props["total"] == props["scenes"][-1]["from"] + props["scenes"][-1]["frames"]
    assert (ep / "video_raw.mp4").exists()
