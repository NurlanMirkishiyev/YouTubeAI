"""Sekil siyahisi + narration (+ SRT, + musiqi, + personaj sprite) -> 1080p30 MP4. Ken Burns + xfade kecidler.
Istifade:
  python montage.py --images a.png b.png ... --durations 6 5 ... --audio narr.wav
                    [--sprites front@right:0.7 - thinking@left ...] [--srt subs.srt] [--music bg.mp3] --out out.mp4
Her sekil ucun zoom-in / zoom-out novbelesir; kecid 0.5 s (xfade 'fade').
--sprites: her sehne ucun bir token (images ile eyni sayda): `-` = sprite yoxdur,
  `<ad>[@left|right|center][:<hund>]` = Character/ELI5_Owl/sprites/<ad>.png, hund = sprite hundurluyu / 1080 (default 0.70).
  Sprite fonun USTUNDE sabit durur (Ken Burns ona tesir etmir) ve yungul "bob" ile nefes alir — personaj 100% orijinaldir.
"""
import argparse, subprocess, os
from dataclasses import dataclass

FPS = 30
W, H = 1920, 1080
XFADE = 0.5
ZOOM_MAX = 1.12
MUSIC_DB = -20  # fon musiqisinin seviyyesi (narrationa nisbeten)
SPRITE_DIR = r"C:\YouTubeAI\Character\ELI5_Owl\sprites"
SPRITE_H = 0.70       # default hundurluk (1080-e nisbeten)
SPRITE_MARGIN_X = 110
SPRITE_MARGIN_Y = 40
BOB_PX, BOB_PERIOD = 7, 2.6   # nefes animasiyasi


@dataclass(frozen=True)
class Sprite:
    path: str
    pos: str = "right"
    height: float = SPRITE_H

    @staticmethod
    def parse(token: str) -> "Sprite | None":
        """'front@right:0.7' -> Sprite; '-' -> None"""
        if token == "-":
            return None
        name, _, rest = token.partition("@")
        pos, _, h = rest.partition(":") if rest else ("right", "", "")
        pos = pos or "right"
        if pos not in ("left", "right", "center"):
            raise SystemExit("sprite pos left|right|center olmalidir: " + token)
        path = os.path.join(SPRITE_DIR, f"{name}.png")
        if not os.path.isfile(path):
            raise SystemExit("sprite tapilmadi: " + path)
        return Sprite(path, pos, float(h) if h else SPRITE_H)

    def x_expr(self) -> str:
        return {"left": str(SPRITE_MARGIN_X), "right": f"W-w-{SPRITE_MARGIN_X}", "center": "(W-w)/2"}[self.pos]


def sprite_overlay(idx: int, in_idx: int, spr: Sprite) -> str:
    """[v{idx}] uzerine sprite girisi in_idx: lanczos ile olcule, asagi kenara yerlesdir, bob ver."""
    h = int(H * spr.height)
    y = f"H-h-{SPRITE_MARGIN_Y}+{BOB_PX}*sin(2*PI*t/{BOB_PERIOD})"
    return (f"[{in_idx}:v]scale=-1:{h}:flags=lanczos,format=rgba[s{idx}];"
            f"[b{idx}][s{idx}]overlay=x={spr.x_expr()}:y='{y}':eof_action=pass,format=yuv420p[v{idx}]")

def esc(p: str) -> str:
    """ffmpeg filter arqumenti ucun Windows yolu: C:/x -> C\\:/x"""
    return p.replace("\\", "/").replace(":", "\\:")

def kenburns(idx: int, dur: float, zoom_in: bool, out: str) -> str:
    frames = int(dur * FPS)
    step = (ZOOM_MAX - 1.0) / frames
    z = f"min(zoom+{step:.6f},{ZOOM_MAX})" if zoom_in else f"max({ZOOM_MAX}-on*{step:.6f},1.0)"
    return (f"[{idx}:v]scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
            f"format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[{out}]")

def build_filter(n: int, durs: list[float], srt: str | None, sprites: list["Sprite | None"]) -> tuple[str, float]:
    """sprites[i] varsa fon [b{i}] -> overlay -> [v{i}]; yoxdursa fon birbasa [v{i}].
    Giris sirasi: sekiller 0..n-1, sprite-ler n.., sonra audio (ve musiqi)."""
    parts = []
    spr_in = n
    for i in range(n):
        spr = sprites[i]
        parts.append(kenburns(i, durs[i], i % 2 == 0, f"b{i}" if spr else f"v{i}"))
        if spr:
            parts.append(sprite_overlay(i, spr_in, spr))
            spr_in += 1
    prev, offset = "v0", 0.0
    for i in range(1, n):
        offset += durs[i - 1] - XFADE
        out = f"x{i}" if i < n - 1 else "vout"
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[{out}]")
        prev = out
    if n == 1:
        parts.append("[v0]null[vout]")
    total = sum(durs) - XFADE * (n - 1)
    if srt:
        parts.append(f"[vout]subtitles='{esc(srt)}':force_style='FontName=Arial,FontSize=20,Bold=1,Outline=2,Shadow=0,MarginV=40'[vsub]")
    return ";".join(parts), total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--durations", nargs="+", type=float, required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--sprites", nargs="+", help="her sehne ucun token: - | ad[@pos][:hund]")
    ap.add_argument("--srt")
    ap.add_argument("--music")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if len(a.images) != len(a.durations):
        raise SystemExit("images ve durations sayi eyni olmalidir")
    for p in a.images + [a.audio] + ([a.srt] if a.srt else []) + ([a.music] if a.music else []):
        if not os.path.isfile(p):
            raise SystemExit("fayl tapilmadi: " + p)

    n = len(a.images)
    sprites = [Sprite.parse(t) for t in a.sprites] if a.sprites else [None] * n
    if len(sprites) != n:
        raise SystemExit("sprites sayi images sayina beraber olmalidir (sprite-siz sehne ucun '-')")
    fc, total = build_filter(n, a.durations, a.srt, sprites)
    vlabel = "[vsub]" if a.srt else "[vout]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for img, d in zip(a.images, a.durations):
        cmd += ["-loop", "1", "-t", f"{d + 1:.2f}", "-i", img]
    for spr, d in zip(sprites, a.durations):
        if spr:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d + 1:.2f}", "-i", spr.path]
    cmd += ["-i", a.audio]
    ai = n + sum(1 for s in sprites if s)
    if a.music:
        cmd += ["-stream_loop", "-1", "-i", a.music]
        fc += f";[{ai}:a]volume=1.0[na];[{ai+1}:a]volume={MUSIC_DB}dB[ma];[na][ma]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        alabel = "[aout]"
    else:
        alabel = f"{ai}:a"
    cmd += ["-filter_complex", fc, "-map", vlabel, "-map", alabel,
            # PNG girisleri RGB oldugu ucun ffmpeg oz-ozune yuv444p (High 4:4:4) secir --
            # bunu Windows pleyerleri, telefonlar ve YouTube acmir. yuv420p mecburidir.
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", a.out]
    print("video length %.1fs, %d scenes" % (total, n))
    subprocess.run(cmd, check=True)
    print("OK ->", a.out)

if __name__ == "__main__":
    main()
