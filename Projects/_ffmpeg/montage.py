"""Sekil siyahisi + narration (+ SRT, + musiqi, + personaj sprite, + bolme basligi) -> 1080p30 MP4.
Istifade:
  python montage.py --images a.png b.png ... --durations 6 5 ... --audio narr.wav
                    [--sprites front@right - thinking@left ...] [--lower-thirds - lt.png ...]
                    [--transitions fade slideleft ...] [--audio-delay 4] [--srt subs.srt --fontsdir DIR]
                    [--music bg.mp3] --out out.mp4
--sprites: her klip ucun token: `-` = sprite yoxdur, `<ad>[@left|right|center][:<hund>]`
  = <sprite-dir>/<ad>.png (+ <ad>_shadow.png), hund = ekran hundurluyu / 1080 (default 0.42).
  Sprite hec vaxt boyudulmur (A5). Kolge sabit durur, sprite ustunde yungul "bob" edir.
  Kolgesi olmayan sprite bust-dur (ayaqsiz) - kadrin alt kenarina yapisir.
Audio: 48 kHz stereo, musiqi ducking, iki kecidli loudnorm -14 LUFS.
Filter qrafi fayla yazilir (-/filter_complex): 30+ sehnede Windows emr limiti (32767) asilir.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio_master import loudnorm_apply, measure, mix_graph  # noqa: E402
from imaging import cut_side  # noqa: E402
from motion import FPS, H, W, kenburns, motion_for, still  # noqa: E402

XFADE = 0.5
SPRITE_DIR = r"C:\YouTubeAI\Character\ELI5_Owl\sprites_hd"
SPRITE_H = 0.42
SPRITE_MARGIN_X = 90
SPRITE_MARGIN_Y = 30
SHADOW_INSET = 0.02            # kolge merkezi ayaq xettinden bu qeder (sprite hundurluyu payi) yuxarida
BOB_PX, BOB_PERIOD = 4, 2.6
LT_IN, LT_OUT, LT_FADE = 0.3, 3.3, 0.4
# libass SRT ucun PlayResY=288: FontSize 13 ~ 49 px, MarginV 24 ~ 90 px (1080p).
# BorderStyle=3 qutusunu OutlineColour ile cekir.
SUB_STYLE = ("FontName=Montserrat SemiBold,FontSize=13,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H80000000,BackColour=&H80000000,BorderStyle=3,Outline=6,"
             "Shadow=0,MarginV=24,Alignment=2")


@dataclass(frozen=True)
class Sprite:
    path: str
    shadow: str | None
    pos: str
    height: float
    src_w: int
    src_h: int
    shadow_w: int = 0
    shadow_h: int = 0
    flip: bool = False     # bust-un kesik yani ekran kenarina baxsin deye guzgu kimi cevrilir

    @property
    def bust(self) -> bool:
        return self.shadow is None

    @staticmethod
    def parse(token: str, sprite_dir: str = SPRITE_DIR) -> "Sprite | None":
        """'front@right:0.42' -> Sprite; '-' -> None"""
        if token == "-":
            return None
        name, _, rest = token.partition("@")
        pos, _, h = rest.partition(":") if rest else ("right", "", "")
        pos = pos or "right"
        if pos not in ("left", "right", "center"):
            raise SystemExit("sprite pos left|right|center olmalidir: " + token)
        path = os.path.join(sprite_dir, f"{name}.png")
        if not os.path.isfile(path):
            raise SystemExit(f"sprite tapilmadi: {path} - upscale_sprites.py isledin")
        shadow = os.path.join(sprite_dir, f"{name}_shadow.png")
        sw = sh = 0
        if os.path.isfile(shadow):
            with Image.open(shadow) as im:
                sw, sh = im.size
        with Image.open(path) as im:
            src_w, src_h = im.size
            side = cut_side(im) if not sw else None
        flip = (pos == "left" and side == "right") or (pos == "right" and side == "left")
        return Sprite(path, shadow if sw else None, pos, float(h) if h else SPRITE_H,
                      src_w, src_h, sw, sh, flip)

    def size(self) -> tuple[int, int]:
        h = round(H * self.height)
        if h > self.src_h:
            raise SystemExit(f"sprite boyudulmeli olardi ({self.src_h} -> {h} px): {self.path} (A5)")
        return round(self.src_w * h / self.src_h), h

    def x(self) -> int:
        """Bust ekranin yan kenarina yapisir (kesik yani gorunmesin), tam beden kenardan araliqda."""
        w = self.size()[0]
        m = 0 if self.bust else SPRITE_MARGIN_X
        return {"left": m, "right": W - w - m, "center": (W - w) // 2}[self.pos]

    def y(self) -> int:
        """Tam beden: ayaqlar kadrin altindan SPRITE_MARGIN_Y yuxarida (kolge ile).
        Bust (kolgesiz): alt kenar kadrin altinda - bob yuxari qalxanda da kesik gorunmur."""
        h = self.size()[1]
        return H - h + BOB_PX if self.shadow is None else H - h - SPRITE_MARGIN_Y

    def shadow_size(self) -> tuple[int, int] | None:
        if not self.shadow:
            return None
        w = self.size()[0]
        return w, round(self.shadow_h * w / self.shadow_w)

    def shadow_y(self) -> int:
        h = self.size()[1]
        return self.y() + h - round(h * SHADOW_INSET) - self.shadow_size()[1] // 2


@dataclass(frozen=True)
class Clip:
    image: str
    duration: float
    sprite: Sprite | None
    lower_third: str | None


def esc(p: str) -> str:
    """ffmpeg filter arqumenti ucun Windows yolu: C:\\x -> C\\:/x"""
    return p.replace("\\", "/").replace(":", "\\:")


def _still_input(path: str) -> list[str]:
    """Tek kadr giris: -loop 1 YOX - her kadrda PNG yeniden dekod olunurdu (0.6 fps) ve
    buferler dolub qraf ilisirdi. Tekrar motion.still() loop filtri ile yaddasda edilir."""
    return ["-i", path]


def input_args(clips: list[Clip]) -> tuple[list[str], list[dict[str, int]]]:
    """ffmpeg giris arqumentleri + her klip ucun giris indeksleri (bg/shadow/sprite/lt)."""
    args: list[str] = []
    table: list[dict[str, int]] = []
    count = 0
    for c in clips:
        paths = {"bg": c.image,
                 "shadow": c.sprite.shadow if c.sprite else None,
                 "sprite": c.sprite.path if c.sprite else None,
                 "lt": c.lower_third}
        row: dict[str, int] = {}
        for key, path in paths.items():
            if path:
                args += _still_input(path)
                row[key] = count
                count += 1
        table.append(row)
    return args, table


def _sprite_parts(i: int, spr: Sprite, row: dict[str, int], cur: str, dur: float) -> tuple[list[str], str]:
    w, h = spr.size()
    x, y = spr.x(), spr.y()
    parts = []
    if "shadow" in row:
        parts.append(f"[{row['shadow']}:v]scale={w}:-1:flags=lanczos,format=rgba,{still(dur)}[sh{i}];"
                     f"[{cur}][sh{i}]overlay=x={x}:y={spr.shadow_y()}:eof_action=pass[c{i}]")
        cur = f"c{i}"
    bob = f"{y}+{BOB_PX}*sin(2*PI*t/{BOB_PERIOD})"
    flip = ",hflip" if spr.flip else ""
    parts.append(f"[{row['sprite']}:v]scale={w}:{h}:flags=lanczos{flip},format=rgba,{still(dur)}[s{i}];"
                 f"[{cur}][s{i}]overlay=x={x}:y='{bob}':eof_action=pass[d{i}]")
    return parts, f"d{i}"


def clip_chain(i: int, clip: Clip, row: dict[str, int]) -> list[str]:
    """Bir klip: Ken Burns fon -> (kolge + sprite) -> (bolme basligi) -> [v{i}]."""
    parts = [kenburns(row["bg"], clip.duration, motion_for(i), f"b{i}")]
    cur = f"b{i}"
    if clip.sprite:
        more, cur = _sprite_parts(i, clip.sprite, row, cur, clip.duration)
        parts += more
    if "lt" in row:
        parts.append(f"[{row['lt']}:v]format=rgba,{still(clip.duration)},"
                     f"fade=t=in:st={LT_IN}:d={LT_FADE}:alpha=1,"
                     f"fade=t=out:st={LT_OUT}:d={LT_FADE}:alpha=1[l{i}];"
                     f"[{cur}][l{i}]overlay=0:0:eof_action=pass[e{i}]")
        cur = f"e{i}"
    parts.append(f"[{cur}]format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
    return parts


def video_graph(clips: list[Clip], table: list[dict[str, int]], transitions: list[str] | None,
                srt: str | None, fontsdir: str | None) -> tuple[str, float]:
    n = len(clips)
    trans = transitions or ["fade"] * (n - 1)
    if len(trans) != n - 1:
        raise SystemExit(f"transitions sayi {len(trans)} != klip sayi - 1 ({n - 1})")
    parts = [p for i, c in enumerate(clips) for p in clip_chain(i, c, table[i])]
    prev, offset = "v0", 0.0
    for i in range(1, n):
        offset += clips[i - 1].duration - XFADE
        out = f"x{i}" if i < n - 1 else "vout"
        parts.append(f"[{prev}][v{i}]xfade=transition={trans[i - 1]}:duration={XFADE}:offset={offset:.3f}[{out}]")
        prev = out
    if n == 1:
        parts.append("[v0]null[vout]")
    if srt:
        fd = f":fontsdir='{esc(fontsdir)}'" if fontsdir else ""
        parts.append(f"[vout]subtitles='{esc(srt)}'{fd}:force_style='{SUB_STYLE}'[vsub]")
    return ";".join(parts), sum(c.duration for c in clips) - XFADE * (n - 1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--durations", nargs="+", type=float, required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--sprites", nargs="+", help="her klip ucun token: - | ad[@pos][:hund]")
    ap.add_argument("--lower-thirds", nargs="+", help="her klip ucun: - | seffaf 1920x1080 PNG")
    ap.add_argument("--transitions", nargs="+", help="klip sayi - 1 eded xfade kecidi")
    ap.add_argument("--audio-delay", type=float, default=0.0, help="narration bu qeder saniye gec baslayir")
    ap.add_argument("--srt")
    ap.add_argument("--fontsdir")
    ap.add_argument("--music")
    ap.add_argument("--sprite-dir", default=SPRITE_DIR)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verbose", action="store_true", help="ffmpeg loglevel info (font secimi gorunur)")
    return ap.parse_args(argv)


def load_clips(a: argparse.Namespace) -> list[Clip]:
    n = len(a.images)
    sprites = a.sprites or ["-"] * n
    lts = a.lower_thirds or ["-"] * n
    if not len(a.durations) == len(sprites) == len(lts) == n:
        raise SystemExit("images, durations, sprites, lower-thirds sayi eyni olmalidir")
    extra = [a.audio] + [p for p in (a.srt, a.music) if p] + [p for p in lts if p != "-"]
    for p in a.images + extra:
        if not os.path.isfile(p):
            raise SystemExit("fayl tapilmadi: " + p)
    return [Clip(img, d, Sprite.parse(tok, a.sprite_dir), None if lt == "-" else lt)
            for img, d, tok, lt in zip(a.images, a.durations, sprites, lts)]


def main(argv: list[str] | None = None) -> None:
    a = parse_args(argv)
    clips = load_clips(a)
    vin, table = input_args(clips)
    vgraph, total = video_graph(clips, table, a.transitions, a.srt, a.fontsdir)
    audio_in = ["-i", a.audio] + (["-stream_loop", "-1", "-i", a.music] if a.music else [])
    narr_idx = sum(len(r) for r in table)
    measured = measure(audio_in, mix_graph(0, 1 if a.music else None, a.audio_delay, total), total)
    fc = ";".join([vgraph, mix_graph(narr_idx, narr_idx + 1 if a.music else None, a.audio_delay, total),
                   loudnorm_apply(measured)])
    fc_path = a.out + ".filter.txt"
    with open(fc_path, "w", encoding="utf-8") as f:
        f.write(fc)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info" if a.verbose else "error",
           *vin, *audio_in, "-/filter_complex", fc_path,
           "-map", "[vsub]" if a.srt else "[vout]", "-map", "[aout]",
           # PNG girisleri RGB oldugu ucun ffmpeg oz-ozune yuv444p (High 4:4:4) secir --
           # bunu Windows pleyerleri, telefonlar ve YouTube acmir. yuv420p mecburidir.
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-t", f"{total:.3f}", "-movflags", "+faststart", a.out]
    print("video length %.1fs, %d clips, loudnorm input %s LUFS" % (total, len(clips), measured["input_i"]),
          flush=True)
    subprocess.run(cmd, check=True)
    os.remove(fc_path)
    print("OK ->", a.out)


if __name__ == "__main__":
    main()
