"""Ken Burns hereket novleri + kecid novbesi (FAZA F 3.3, 3.4).
Fon 3840x2160 menbeden kesilir: 1 px giris titremesi cixisda ~0.5 px olur - hamar hereket.
(5120x2880 olculdu: 0.6 fps - 10 deq video ucun ~8 saat. 3840 spec-in fallback-idir, A6 odenir.)
Sekil BIR DEFE dekod olunur ve olculenir, sonra `loop` filtri kadri yaddasda tekrarlayir -
`-loop 1` giris her kadrda PNG-ni yeniden acirdi ve buferler dolub qraf ilisirdi."""
from __future__ import annotations

from dataclasses import dataclass

FPS = 30
W, H = 1920, 1080
KB_W, KB_H = 3840, 2160
VIGNETTE = "vignette=angle=PI/5"
TRANSITIONS = ("fade", "slideleft", "wipeleft", "dissolve")


@dataclass(frozen=True)
class Motion:
    z0: float    # baslangic zoom
    z1: float    # son zoom
    px0: float   # ufuqi movqe 0 = sol, 1 = sag
    px1: float


MOTIONS: dict[str, Motion] = {
    "zoom_in": Motion(1.00, 1.10, 0.5, 0.5),
    "zoom_out": Motion(1.10, 1.00, 0.5, 0.5),
    "pan_lr": Motion(1.08, 1.10, 0.0, 1.0),
    "pan_rl": Motion(1.08, 1.10, 1.0, 0.0),
}
ORDER = ("zoom_in", "pan_lr", "zoom_out", "pan_rl")


def motion_for(i: int) -> str:
    return ORDER[i % len(ORDER)]


def still(dur: float) -> str:
    """Tek kadrlik girisi dur+1 saniyelik FPS axinina cevirir (dekod bir defe)."""
    return f"loop=loop={round((dur + 1) * FPS) - 1}:size=1:start=0,setpts=N/{FPS}/TB"


def kenburns(idx: int, dur: float, motion: str, out: str) -> str:
    """[idx:v] -> [out]: smoothstep easing ile zoom + pan, yumsaq vignette."""
    m = MOTIONS[motion]
    frames = max(2, round(dur * FPS))
    p = f"min(on/{frames - 1},1)"
    e = f"({p})*({p})*(3-2*({p}))"
    z = f"{m.z0}+({m.z1 - m.z0:.4f})*{e}"
    x = f"(iw-iw/zoom)*({m.px0}+({m.px1 - m.px0:.4f})*{e})"
    y = "(ih-ih/zoom)/2"
    return (f"[{idx}:v]scale={KB_W}:{KB_H}:force_original_aspect_ratio=increase,crop={KB_W}:{KB_H},"
            f"{still(dur)},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},{VIGNETTE},"
            f"format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[{out}]")


def transitions_for(sections: list[str]) -> list[str]:
    """Klipler arasi kecidler: bolme deyisende 'fade', bolme daxilinde novbe ile."""
    return ["fade" if sections[i] != sections[i + 1] else TRANSITIONS[i % len(TRANSITIONS)]
            for i in range(len(sections) - 1)]
