"""Faza 3.1/3.10 (istifadeci 2026-10-07): chart, kart ve overlay komponentlerinde hardcoded muddet ve xetti easing
yoxdur (yalniz motion.ts tokenleri); Ken Burns (Background.tsx) istisnadir. Bayqus komponentleri (Owl.tsx, CardOwl)
DEYISMIR ve hereketsizdir."""
import hashlib
import os
import re

SRC = r"C:\YouTubeAI\Remotion\src"
LINTED = [os.path.join(SRC, "visuals", f) for f in os.listdir(os.path.join(SRC, "visuals")) if f.endswith(".tsx")] \
    + [os.path.join(SRC, "Cards.tsx"), os.path.join(SRC, "Episode.tsx"), os.path.join(SRC, "Text.tsx"),
       os.path.join(SRC, "Effects.tsx")]
OWL_SHA = "2438271b88d26bbe352bfa6f58c388dd0404f5a3a18edaa6b90cf761a3d439dc"
CARD_OWL_SHA = "cbc468ad4276db022a60a54d30052d6e28b092c75651f377edebdca9722609ca"
_CARD_OWL = re.compile(r"const CardOwl: React.FC.*?\n\};\n", re.S)


def _src(path: str) -> str:
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    return _CARD_OWL.sub("", text)              # CardOwl lint-den kenardadir (deyismir)


def _calls(text: str, name: str) -> list[str]:
    out, i = [], 0
    while (i := text.find(name + "(", i)) >= 0:
        depth, j = 0, i + len(name)
        while j < len(text):
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            if depth == 0:
                break
            j += 1
        out.append(text[i:j + 1])
        i = j
    return out


def test_no_linear_interpolation_in_charts_cards_and_overlays():
    bad = []
    for path in LINTED:
        if not os.path.isfile(path):
            continue
        text = _src(path)
        # zamana bagli interpolasiya (frame/t) easing ile olmalidir; spring deyerinin (p) xeritelenmesi azaddir
        bad += [f"{os.path.basename(path)}: {c[:70]}" for c in _calls(text, "interpolate")
                if re.match(r"interpolate\((frame|t)\b", c) and "easing" not in c]
        if "Easing.linear" in text:
            bad.append(f"{os.path.basename(path)}: Easing.linear")
    assert not bad, bad


def test_no_hardcoded_durations_or_spring_configs():
    bad = []
    for path in LINTED:
        if not os.path.isfile(path):
            continue
        text = _src(path)
        bad += [f"{os.path.basename(path)}: {m.group(0)}" for m in re.finditer(r"\d+(?:\.\d+)?\s*\*\s*fps", text)]
        bad += [f"{os.path.basename(path)}: {m.group(0)}" for m in re.finditer(r"config:\s*\{\s*damping", text)]
        bad += [f"{os.path.basename(path)}: {m.group(0)}" for m in re.finditer(r"\b(?:delay|d0|from)\s*[-+]\s*\d+\b", text)]
    assert not bad, bad


def test_owl_components_are_unchanged_and_still():
    owl = open(os.path.join(SRC, "Owl.tsx"), encoding="utf-8").read()
    assert hashlib.sha256(owl.encode()).hexdigest() == OWL_SHA
    cards = open(os.path.join(SRC, "Cards.tsx"), encoding="utf-8").read()
    block = _CARD_OWL.search(cards).group(0)
    assert hashlib.sha256(block.encode()).hexdigest() == CARD_OWL_SHA
    for text in (owl, block):
        assert "spring(" not in text and "Math.sin" not in text and "rotate" not in text


def test_ken_burns_keeps_a_constant_speed():
    """Reyestr #9: inOut easing fonu her kecidde dayandirirdi - Ken Burns zamanla XETTI (easing-siz) hereket edir."""
    text = _src(os.path.join(SRC, "Background.tsx"))
    calls = [c for c in _calls(text, "interpolate") if re.match(r"interpolate\(frame\b", c)]
    assert calls and all("easing" not in c for c in calls)
    assert "Easing." not in text and "spring(" not in text
