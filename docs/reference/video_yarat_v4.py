"""
VIDEO YARAT v4 - senedli film montaji (tam avtomatik, pulsuz)

Yenilikler (v3 uzerine):
  - animasiyali sehm qrafiki
  - ABS xeritesinde filial animasiyasi
  - qezet basliqlari
  - reqemler sayilaraq qalxir
  - kanal intro karti (cold open-dan sonra)

Qovluqda olmalidir:
  - sekiller: 001.jpg ...     - ses: ses1.mp3, ses2.mp3 ...
  - prompt CSV-si             - metn.txt (fesil basliqlari)
  - ekler.json  (qrafik / xerite / qezet / intro ayarlari)
  - (istege bagli) musiqi.mp3

Ilk defe:  py -m pip install faster-whisper pillow
Isletmek:  py video_yarat_v4.py
"""
import subprocess, sys, os, glob, shutil, tempfile, csv, json, re, difflib, math, random
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
except ImportError:
    sys.exit("XETA: Pillow yoxdur. Bunu yaz:  py -m pip install pillow")

FOLDER = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(FOLDER, "video.mp4")

# ---------------- AYARLAR ----------------
FPS = 30
W, H = 1920, 1080
FADE = 0.6
CARD = 3.5              # fesil karti
INTRO = 4.0             # kanal intro karti
ZOOM = 0.12
MUSIC_VOL = 0.12
WHISPER_MODEL = "small.en"
SUBTITLES = True
NUMBERS = True
CHAPTERS = True
SFX = True
FILM_LOOK = True
SKIP_FIRST_CHAPTER = True
OUTRO_SECONDS = 3.0
LOUDNORM = True
# -----------------------------------------

GREEN = (70, 215, 125)
RED = (235, 70, 60)
GOLD = (255, 192, 72)
BG = (12, 14, 18)


def run(cmd, cwd=None):
    if cmd and cmd[0] == "ffmpeg" and "-nostdin" not in cmd:
        cmd = [cmd[0], "-nostdin"] + list(cmd[1:])
    subprocess.run(cmd, check=True, cwd=cwd)


def graph_flag():
    out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout
    try:
        major = int(out.split("version ")[1].split(".")[0].lstrip("n"))
    except Exception:
        major = 7
    return "-/filter_complex" if major >= 7 else "-filter_complex_script"


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def ease(x):
    x = max(0.0, min(1.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------- SRIFTLER ----------------
FONT_DIRS = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
             "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype",
             "/Library/Fonts", "/System/Library/Fonts/Supplemental"]
_font_cache = {}


def font(names, size):
    key = (tuple(names), size)
    if key in _font_cache:
        return _font_cache[key]
    for n in list(names) + ["DejaVuSans-Bold.ttf"]:
        for d in FONT_DIRS:
            p = os.path.join(d, n)
            if os.path.exists(p):
                f = ImageFont.truetype(p, size)
                _font_cache[key] = f
                return f
    f = ImageFont.load_default(size)
    _font_cache[key] = f
    return f


F_BOLD = ["arialbd.ttf", "DejaVuSans-Bold.ttf"]
F_BLACK = ["ariblk.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
F_REG = ["arial.ttf", "DejaVuSans.ttf"]
F_SERIF_B = ["timesbd.ttf", "georgiab.ttf", "DejaVuSerif-Bold.ttf"]
F_SERIF_I = ["georgiai.ttf", "timesi.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif.ttf"]
F_MAST = ["OLDENGL.TTF", "georgiab.ttf", "DejaVuSerif-Bold.ttf"]


# ---------------- FAYLLAR ----------------
def find_files():
    imgs = sorted(f for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp")
                  for f in glob.glob(os.path.join(FOLDER, ext)))
    imgs = [f for f in imgs if re.fullmatch(r"\d+", os.path.splitext(os.path.basename(f))[0])]
    voices = sorted(f for f in glob.glob(os.path.join(FOLDER, "ses*.*"))
                    if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac")))
    music = [f for f in glob.glob(os.path.join(FOLDER, "musiqi.*"))
             if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac"))]
    csvs = glob.glob(os.path.join(FOLDER, "*.csv"))
    metn = os.path.join(FOLDER, "metn.txt")
    ekler = os.path.join(FOLDER, "ekler.json")
    if not imgs:
        sys.exit("XETA: sekil tapilmadi (001.jpg, 002.jpg ...).")
    if not voices:
        sys.exit("XETA: ses fayli tapilmadi (ses1.mp3, ses2.mp3 ...).")
    if not csvs:
        sys.exit("XETA: prompt CSV fayli tapilmadi.")
    cfg = {}
    if os.path.exists(ekler):
        with open(ekler, encoding="utf-8-sig") as f:
            cfg = json.load(f)
    return (imgs, voices, music[0] if music else None, csvs[0],
            metn if os.path.exists(metn) else None, cfg)


def merge_voices(voices, tmp):
    lst = os.path.join(tmp, "voices.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for v in voices:
            f.write(f"file '{v.replace(chr(92), '/')}'\n")
    out = os.path.join(tmp, "voice.wav")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", out])
    return out


def read_chunks(csv_path, imgs):
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = {int(float(r["No"])): r["Metn"] for r in csv.DictReader(f)
                if r.get("No") and r.get("Metn")}
    chunks = []
    for img in imgs:
        key = int(os.path.splitext(os.path.basename(img))[0])
        if key not in rows:
            sys.exit(f"XETA: CSV-de {key} nomreli setir yoxdur.")
        chunks.append(rows[key])
    return chunks


def read_chapters(metn_path):
    if not metn_path or not CHAPTERS:
        return []
    with open(metn_path, encoding="utf-8-sig") as f:
        lines = [l.strip() for l in f if l.strip()]
    heads = []
    for i, l in enumerate(lines[:-1]):
        letters = re.sub(r"[^A-Za-z]", "", l)
        nxt = re.sub(r"[^A-Za-z]", "", lines[i + 1])
        if letters and l == l.upper() and len(l) < 50 and nxt and lines[i + 1] != lines[i + 1].upper():
            heads.append((l, lines[i + 1]))
    if SKIP_FIRST_CHAPTER and heads:
        heads = heads[1:]
    return heads


# ---------------- WHISPER ----------------
def transcribe(voice):
    cache = os.path.join(FOLDER, "whisper_cache.json")
    dur = duration(voice)
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            data = json.load(f)
        if abs(data.get("duration", 0) - dur) < 0.5:
            print("Whisper neticesi yaddasdan goturuldu.")
            return data["words"]
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("XETA: Whisper qurulmayib. Bunu yaz:  py -m pip install faster-whisper")
    print(f"Whisper sesi dinleyir ({WHISPER_MODEL})...")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(voice, word_timestamps=True, language="en")
    words = []
    for s in segs:
        for w in s.words:
            if w.word.strip():
                words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
        print(f"  {s.end:5.0f} / {dur:.0f} san", end="\r")
    print()
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"duration": dur, "words": words}, f)
    return words


def fix_names(script_words, words):
    """Whisper bezi xususi adlari sehv yazir (Reicher -> Riker). Ssenaridaki ad ile
    eyni yerde duran, ona oxsar sozu ssenaridekine cevirir (altyazi ucun)."""
    a = [norm(w) for w in script_words]
    b = [norm(w["w"]) for w in words]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    fixed = []
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag != "replace" or (a2 - a1) != (b2 - b1):
            continue
        for ja, kb in zip(range(a1, a2), range(b1, b2)):
            sw = script_words[ja].strip(".,;:!?\"'()")
            mm = re.match(r"^(\W*)(.*?)(\W*)$", words[kb]["w"])
            lead, core, trail = mm.group(1), mm.group(2), mm.group(3)
            if sw[:1].isupper() and sw.isalpha() and core.isalpha() and sw != core:
                if difflib.SequenceMatcher(None, sw.lower(), core.lower()).ratio() >= 0.6:
                    words[kb]["w"] = lead + sw + trail
                    fixed.append((core, sw))
    return fixed


def align(script_words, words):
    a = [norm(w) for w in script_words]
    b = [norm(w["w"]) for w in words]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = [None] * len(a)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = blk.b + k
    known = [j for j in range(len(a)) if m[j] is not None]
    if not known:
        sys.exit("XETA: ses ile metn uygun gelmir.")
    for j in range(len(a)):
        if m[j] is None:
            prev = max([k for k in known if k < j], default=None)
            nxt = min([k for k in known if k > j], default=None)
            if prev is None:
                m[j] = m[nxt]
            elif nxt is None:
                m[j] = m[prev]
            else:
                m[j] = round(m[prev] + (m[nxt] - m[prev]) * (j - prev) / (nxt - prev))
    return m


def cut_at(words, k):
    if k <= 0:
        return 0.0
    k = min(k, len(words) - 1)
    prev_e, cur_s = words[k - 1]["e"], words[k]["s"]
    return (prev_e + cur_s) / 2 if cur_s > prev_e else cur_s


# ---------------- REQEMLER ----------------
NOUNS = {"stores", "restaurants", "locations", "times", "states"}
SCALE = {"million", "billion", "thousand"}


def find_numbers(words):
    out, last = [], -99
    for i, wd in enumerate(words):
        w = wd["w"].strip("\"',.;:!?()")
        nxt = words[i + 1]["w"].strip("\"',.;:!?()").lower() if i + 1 < len(words) else ""
        txt = None
        if re.fullmatch(r"\$\d[\d,.]*", w):
            txt = w + (" " + nxt.upper() if nxt in SCALE else "")
        elif re.fullmatch(r"\d[\d,.]*%", w):
            txt = w
        elif re.fullmatch(r"\d[\d,.]*", w) and nxt == "percent":
            txt = w + "%"
        elif re.fullmatch(r"\d+", w) and nxt == "cents":
            txt = w + "¢"
        elif w.lower() == "fifty" and nxt == "cents":
            txt = "50¢"
        elif (re.fullmatch(r"\d[\d,]*", w) and not re.fullmatch(r"(19|20)\d\d", w)
              and nxt in NOUNS):
            txt = f"{w} {nxt.upper()}"
        if txt and wd["s"] - last > 1.8:
            out.append((wd["s"], txt))
            last = wd["s"]
    return out


# ---------------- SES EFFEKTLERI ----------------
def make_sfx(tmp):
    d = os.path.join(tmp, "sfx")
    os.makedirs(d, exist_ok=True)
    user = os.path.join(FOLDER, "sfx")

    def pick(name, lavfi, af):
        for ext in (".mp3", ".wav"):
            p = os.path.join(user, name + ext)
            if os.path.exists(p):
                return p
        out = os.path.join(d, name + ".wav")
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", lavfi,
             "-af", af + ",aformat=sample_rates=44100:channel_layouts=stereo", out])
        return out

    return {
        "whoosh": pick("whoosh", "anoisesrc=d=0.9:c=pink:a=0.7",
                       "highpass=f=300,lowpass=f=5000,afade=t=in:d=0.5:curve=exp,"
                       "afade=t=out:st=0.5:d=0.4"),
        "boom": pick("boom",
                     "aevalsrc=0.9*sin(2*PI*(58-22*t)*t)*exp(-1.6*t)"
                     "+0.25*(random(0)*2-1)*exp(-14*t):d=2.8:s=44100",
                     "lowpass=f=900"),
        "pop": pick("pop", "anoisesrc=d=0.35:c=pink:a=0.5",
                    "highpass=f=600,lowpass=f=6000,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.23"),
        "slap": pick("slap",
                     "aevalsrc=(random(0)*2-1)*exp(-30*t)+0.6*sin(2*PI*90*t)*exp(-18*t):d=0.5:s=44100",
                     "lowpass=f=3500"),
    }


def make_ticks(tmp, n, dt, vol_name):
    out = os.path.join(tmp, "sfx", f"{vol_name}_{n}_{int(dt*1000)}.wav")
    if not os.path.exists(out):
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             f"aevalsrc=0.7*(random(0)*2-1)*lt(mod(t\\,{dt})\\,0.012):d={n * dt + 0.1:.2f}:s=44100",
             "-af", "highpass=f=1800,aformat=sample_rates=44100:channel_layouts=stereo", out])
    return out


# ---------------- ASS ----------------
def ass_time(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ass_escape(s):
    return s.replace("{", "(").replace("}", ")")


HILITE = "&H00FFA33B&"   # ass reng BGR formatinda - achiq goy/mavi
RESET = "&H00FFFFFF&"


def word_bound(a, b):
    return (a["e"] + b["s"]) / 2 if b["s"] > a["e"] else b["s"]


ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Arial,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,120,120,60,1
Style: Num,Arial Black,130,&H0040C8FF,&H0040C8FF,&H00000000,&H90000000,0,0,0,0,100,100,2,0,1,5,3,5,40,40,40,1
Style: Card,Georgia,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,4,0,1,0,0,5,40,40,40,1
Style: Small,Georgia,34,&H00A0A0A0,&H00A0A0A0,&H00000000,&H00000000,0,0,0,0,100,100,8,0,1,0,0,5,40,40,40,1
Style: Logo,Georgia,128,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,10,0,1,0,0,5,40,40,40,1
Style: Hook,Arial Black,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,0,0,5,130,130,100,1
Style: HookNum,Arial Black,50,&H0040C8FF,&H0040C8FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,0,0,5,130,130,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def subtitle_groups(words, cuts):
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_sent = w["w"][-1:] in ".?!"
        gap = nxt and nxt["s"] - w["e"] > 0.5
        crosses = nxt and any(w["e"] <= c <= nxt["s"] for c in cuts)
        if len(cur) >= 7 or end_sent or gap or crosses or nxt is None \
                or (cur[-1]["e"] - cur[0]["s"] > 3.2):
            groups.append(cur)
            cur = []
    return groups


def srt_time(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path, groups, shift):
    lines = []
    for i, g in enumerate(groups, 1):
        a, b = shift(g[0]["s"]), shift(g[-1]["e"]) + 0.3
        text = " ".join(w["w"] for w in g)
        lines.append(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_chapters(path, cards, project_title):
    lines = [f"0:00 {project_title}"]
    for c in sorted(cards, key=lambda c: c["new"]):
        label = c["title"] if c["kind"] == "chapter" else project_title
        t = c["new"] + c["dur"]
        m, s = divmod(int(round(t)), 60)
        h, m = divmod(m, 60)
        ts = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        if label != lines[-1].split(" ", 1)[-1]:
            lines.append(f"{ts} {label}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def make_outro(tmp, channel, sub):
    out = os.path.join(tmp, "outro.mp4")
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W / 2, H / 2 - 40), "SUBSCRIBE", font=font(F_BLACK, 90), fill=(255, 255, 255), anchor="mm")
    if channel:
        d.text((W / 2, H / 2 + 60), channel, font=font(F_BOLD, 40), fill=(150, 155, 165), anchor="mm")
    if sub:
        d.text((W / 2, H / 2 + 110), sub, font=font(F_REG, 28), fill=(110, 115, 125), anchor="mm")
    png = os.path.join(tmp, "outro.png")
    img.save(png)
    frames = round(OUTRO_SECONDS * FPS)
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-vf", "fade=t=in:st=0:d=0.5,format=yuv420p", "-r", str(FPS), "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{OUTRO_SECONDS}", "-shortest", out])
    return out


def counter_events(a, txt, steps=14, run_t=0.7, hold=2.4):
    """reqem 0-dan sayilaraq qalxir"""
    m = re.fullmatch(r"(\$?)(\d[\d,]*(?:\.\d+)?)(.*)", txt)
    if not m:
        return [f"Dialogue: 1,{ass_time(a)},{ass_time(a + hold)},Num,,0,0,0,,"
                "{\\pos(960,420)\\fad(120,350)}" + ass_escape(txt)]
    pre, num, suf = m.groups()
    val = float(num.replace(",", ""))
    dec = len(num.split(".")[1]) if "." in num else 0
    commas = "," in num
    ev = []
    dt = run_t / steps
    for k in range(1, steps + 1):
        v = val * ease_out(k / steps)
        s = f"{v:,.{dec}f}" if commas else f"{v:.{dec}f}"
        sc = int(75 + 25 * ease_out(k / steps))
        t0 = a + (k - 1) * dt
        t1 = a + k * dt if k < steps else a + hold
        fx = f"{{\\pos(960,420)\\fscx{sc}\\fscy{sc}"
        fx += "\\fad(120,0)}" if k == 1 else ("\\fad(0,350)}" if k == steps else "}")
        ev.append(f"Dialogue: 1,{ass_time(t0)},{ass_time(t1)},Num,,0,0,0,,{fx}{ass_escape(pre + s + suf)}")
    return ev


# ---------------- KAMERA HEREKETI ----------------
KINDS = ["zoom_in", "pan_right", "zoom_out", "pan_left", "zoom_in", "pan_up", "zoom_out", "pan_down"]


def motion(kind, frames):
    d = max(frames - 1, 1)
    e = f"(0.5-0.5*cos(PI*on/{d}))"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if kind == "zoom_in":
        return f"1+{ZOOM}*{e}", cx, cy
    if kind == "zoom_out":
        return f"1+{ZOOM}-{ZOOM}*{e}", cx, cy
    z = f"{1 + ZOOM}"
    if kind == "pan_right":
        return z, f"(iw-iw/zoom)*{e}", cy
    if kind == "pan_left":
        return z, f"(iw-iw/zoom)*(1-{e})", cy
    if kind == "pan_down":
        return z, cx, f"(ih-ih/zoom)*{e}"
    return z, cx, f"(ih-ih/zoom)*(1-{e})"


# ---------------- QRAFIK ----------------
CHART_PATH = [(0, 20), (0.03, 48), (0.08, 41), (0.16, 46), (0.24, 39), (0.33, 49), (0.42, 43),
              (0.5, 47), (0.58, 45), (0.62, 44), (0.72, 26), (0.82, 11), (0.9, 3), (1.0, 0.5)]
CRASH_X = 0.62


class Chart:
    def __init__(self, spec, t):
        self.spec, self.t = spec, t
        self.x0, self.x1, self.y0, self.y1 = 180, 1740, 230, 860
        self.ymax = 55
        base = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(base)
        for v in range(0, 60, 10):
            y = self.py(v)
            d.line([(self.x0, y), (self.x1, y)], fill=(32, 36, 44), width=2)
            d.text((self.x0 - 20, y), f"${v}", font=font(F_REG, 26), fill=(110, 115, 125), anchor="rm")
        d.text((self.x0, 110), spec.get("title", "SHARE PRICE"), font=font(F_BOLD, 46), fill=(235, 235, 235))
        d.text((self.x0, 168), "illustrative", font=font(F_REG, 24), fill=(100, 105, 115))
        d.text((self.x0, self.y1 + 40), spec.get("from_year", ""), font=font(F_BOLD, 30), fill=(150, 155, 165), anchor="lm")
        d.text((self.x1, self.y1 + 40), spec.get("to_year", ""), font=font(F_BOLD, 30), fill=(150, 155, 165), anchor="rm")
        self.base = base

    def px(self, x):
        return self.x0 + x * (self.x1 - self.x0)

    def py(self, v):
        return self.y1 - v / self.ymax * (self.y1 - self.y0)

    def value_at(self, x):
        for (xa, va), (xb, vb) in zip(CHART_PATH, CHART_PATH[1:]):
            if x <= xb:
                return va + (vb - va) * (x - xa) / (xb - xa)
        return CHART_PATH[-1][1]

    def progress(self, t):
        ts, tp, tc = self.t["start"], self.t["peak"], self.t["crash"]
        if t < ts:
            return 0.0
        if t < tp + 0.6:
            return 0.03 * ease((t - ts) / max(0.6, tp + 0.6 - ts))
        if t < tc:
            return 0.03 + (CRASH_X - 0.03) * ease((t - tp - 0.6) / max(0.5, (tc - tp - 0.6) * 0.9))
        return CRASH_X + (1 - CRASH_X) * ease((t - tc) / 2.5)

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img)
        p = self.progress(t)
        pts = [(x, v) for x, v in CHART_PATH if x <= p] + [(p, self.value_at(p))]
        for (xa, va), (xb, vb) in zip(pts, pts[1:]):
            col = GREEN if xb <= CRASH_X + 1e-6 else RED
            d.line([(self.px(xa), self.py(va)), (self.px(xb), self.py(vb))], fill=col, width=7)
        v = self.value_at(p)
        col = GREEN if p <= CRASH_X + 1e-6 else RED
        cx, cy = self.px(p), self.py(v)
        d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=tuple(c // 4 for c in col))
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=col)
        d.text((self.x1, 125), f"${v:,.2f}", font=font(F_BLACK, 84), fill=col, anchor="rm")
        f = font(F_BOLD, 34)
        if p > 0.005:
            d.text((self.px(0) + 14, self.py(20) + 34), "$20 IPO", font=f, fill=(200, 200, 205), anchor="lm")
        if p >= 0.03:
            d.text((self.px(0.03), self.py(48) - 34), "$48 DAY ONE", font=f, fill=GREEN, anchor="lm")
        if p >= 0.999:
            d.text((self.px(1.0) - 10, self.py(0.5) - 50), "$0.50", font=font(F_BLACK, 64), fill=RED, anchor="rs")
        return img


# ---------------- XERITE ----------------
US = [(-124.7, 48.4), (-122.8, 49.0), (-95.2, 49.0), (-89.6, 48.0), (-84.5, 46.5), (-83.5, 46.1),
      (-82.4, 43.0), (-83.1, 42.0), (-82.5, 41.7), (-79.8, 42.2), (-79.0, 43.3), (-76.3, 43.5),
      (-75.0, 44.8), (-71.5, 45.0), (-70.0, 46.7), (-69.2, 47.4), (-67.8, 47.1), (-67.0, 44.8),
      (-70.2, 43.6), (-70.8, 42.5), (-70.0, 41.8), (-71.5, 41.3), (-73.9, 40.6), (-74.0, 39.6),
      (-75.0, 38.9), (-76.0, 37.0), (-75.5, 35.2), (-77.9, 33.9), (-79.9, 32.7), (-81.4, 30.5),
      (-80.0, 26.7), (-80.4, 25.2), (-81.8, 26.1), (-82.6, 27.8), (-83.0, 29.1), (-84.3, 30.0),
      (-85.4, 29.7), (-86.8, 30.4), (-88.5, 30.4), (-89.6, 30.2), (-89.4, 29.0), (-90.5, 29.1),
      (-92.0, 29.6), (-94.0, 29.7), (-95.0, 29.1), (-97.2, 27.6), (-97.2, 25.9), (-99.5, 27.5),
      (-101.4, 29.8), (-103.1, 29.0), (-104.5, 29.6), (-106.5, 31.8), (-108.2, 31.8), (-111.1, 31.3),
      (-114.8, 32.5), (-117.1, 32.5), (-118.4, 34.0), (-120.6, 34.6), (-121.9, 36.6), (-122.5, 37.8),
      (-123.8, 39.8), (-124.4, 42.0), (-124.1, 44.5), (-124.0, 46.3)]


def in_poly(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class USMap:
    def __init__(self, spec, t):
        self.spec, self.t = spec, t
        k = math.cos(math.radians(38))
        lon0, lon1, lat0, lat1 = -125, -66.5, 24.8, 49.5
        s = min(1500 / ((lon1 - lon0) * k), 640 / (lat1 - lat0))
        mw, mh = (lon1 - lon0) * k * s, (lat1 - lat0) * s
        ox, oy = (W - mw) / 2, 250 + (640 - mh) / 2
        self.proj = lambda lon, lat: (ox + (lon - lon0) * k * s, oy + (lat1 - lat) * s)
        poly = [self.proj(*p) for p in US]
        base = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(base)
        d.polygon(poly, fill=(24, 28, 35), outline=(75, 85, 98), width=3)
        d.text((150, 110), spec.get("title", "LOCATIONS"), font=font(F_BOLD, 46), fill=(235, 235, 235))
        self.base = base
        rnd = random.Random(7)
        n = max([spec.get("from", 0)] + [k[1] for k in spec.get("keys", [])]) + 5
        self.dots = []
        while len(self.dots) < n:
            lon, lat = rnd.uniform(lon0, lon1), rnd.uniform(lat0, lat1)
            if in_poly(lon, lat, US) and rnd.random() < 0.3 + 0.7 * (lon - lon0) / (lon1 - lon0):
                self.dots.append(self.proj(lon, lat))

    def count(self, t):
        c = self.spec.get("from", 0)
        label = ""
        ks = self.t["keys"]
        for i, (tk, val, lab) in enumerate(ks):
            if t >= tk:
                c = c + (val - c) * ease((t - tk) / 2.0)
                label = lab
        return c, label

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img)
        c, label = self.count(t)
        prev, _ = self.count(t - 0.5)
        n = int(round(c))
        for i, (x, y) in enumerate(self.dots[:n]):
            r = 4
            if n > prev and i >= int(prev):
                r = 7
            d.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4], fill=(70, 52, 20))
            d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD)
        if prev > c:
            for x, y in self.dots[n:int(round(prev))]:
                d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=RED)
        d.text((W - 150, 150), f"{n:,}", font=font(F_BLACK, 110), fill=GOLD, anchor="rm")
        d.text((W - 150, 225), "LOCATIONS", font=font(F_BOLD, 30), fill=(170, 170, 175), anchor="rm")
        if label:
            d.text((150, 185), label, font=font(F_BOLD, 38), fill=(150, 155, 165))
        return img


# ---------------- QEZET ----------------
def wrap(text, fnt, width, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=fnt) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def newspaper(spec, bg_img, photo_img, out):
    bg = ImageOps.fit(Image.open(bg_img).convert("RGB"), (W, H))
    bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(14))).enhance(0.3)
    pw, ph = 1180, 800
    paper = Image.new("RGB", (pw, ph), (234, 226, 206))
    noise = Image.effect_noise((pw, ph), 40).convert("RGB")
    paper = Image.blend(paper, noise, 0.07)
    d = ImageDraw.Draw(paper)
    ink = (28, 26, 24)
    d.text((pw / 2, 62), spec.get("paper", "The American Ledger"), font=font(F_MAST, 64), fill=ink, anchor="mm")
    d.line([(40, 108), (pw - 40, 108)], fill=ink, width=3)
    d.text((pw / 2, 126), spec.get("date", "").upper(), font=font(F_SERIF_B, 20), fill=ink, anchor="mm")
    d.line([(40, 144), (pw - 40, 144)], fill=ink, width=1)
    hf = font(F_SERIF_B, 76)
    y = 170
    for line in wrap(spec.get("headline", "").upper(), hf, pw - 100, d):
        d.text((pw / 2, y), line, font=hf, fill=ink, anchor="ma")
        y += 84
    sf = font(F_SERIF_I, 32)
    y += 10
    for line in wrap(spec.get("sub", ""), sf, pw - 160, d):
        d.text((pw / 2, y), line, font=sf, fill=(55, 50, 45), anchor="ma")
        y += 40
    y += 20
    d.line([(40, y), (pw - 40, y)], fill=ink, width=1)
    y += 24
    photo = ImageOps.grayscale(ImageOps.fit(Image.open(photo_img).convert("RGB"), (520, ph - y - 40)))
    photo = ImageOps.autocontrast(photo, cutoff=2).convert("RGB")
    paper.paste(photo, (50, y))
    rnd = random.Random(len(spec.get("headline", "")))
    for col_x in (600, 890):
        yy = y
        while yy < ph - 50:
            wdt = 250 if rnd.random() > 0.15 else rnd.randint(80, 200)
            d.rectangle([col_x, yy, col_x + wdt, yy + 7], fill=(150, 144, 132))
            yy += 17
    card = paper.convert("RGBA").rotate(-2.5, expand=True, resample=Image.BICUBIC)
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 170), mask=card.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    x, y0 = (W - card.width) // 2, (H - card.height) // 2 - 50
    out_img = bg.convert("RGBA")
    out_img.alpha_composite(shadow, (x + 18, y0 + 24))
    out_img.alpha_composite(card, (x, y0))
    out_img.convert("RGB").save(out, quality=95)


# ---------------- KLIP RENDER ----------------
import threading
_prog = {"done": 0, "total": 0}
_prog_lock = threading.Lock()


def _tick(name):
    with _prog_lock:
        _prog["done"] += 1
        print(f"  [{_prog['done']}/{_prog['total']}] hazir: {name}", flush=True)


def encode_frames(out, frames, draw_fn, t0):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out],
                         stdin=subprocess.PIPE)
    for f in range(frames):
        p.stdin.write(draw_fn(t0 + f / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg render xetasi")


def make_clip(job):
    i, kind, payload, frames, t0, tmp = job
    out = os.path.join(tmp, f"clip_{i:04d}.mp4")
    if kind == "black":
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             f"color=c=black:s={W}x{H}:r={FPS}", "-frames:v", str(frames),
             "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", out])
        _tick("kart")
        return out
    if kind == "anim":
        encode_frames(out, frames, payload.frame, t0)
        _tick(f"animasiya ({type(payload).__name__}, {frames / FPS:.0f} san)")
        return out
    img, mkind = payload
    z, x, y = motion(mkind, frames)
    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img, "-vf", vf,
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", out])
    _tick(f"{os.path.basename(img)} ({frames / FPS:.0f} san)")
    return out


# ---------------- ESAS ----------------
def main():
    imgs, voices, music, csv_path, metn, cfg = find_files()
    chunks = read_chunks(csv_path, imgs)
    chapters = read_chapters(metn)
    tmp = tempfile.mkdtemp()
    try:
        voice = merge_voices(voices, tmp)
        dur = duration(voice)
        words = transcribe(voice)

        script_words, starts = [], []
        for c in chunks:
            starts.append(len(script_words))
            script_words += c.split()
        fixed = fix_names(script_words, words)
        if fixed:
            print("Altyazida adlar duzeldildi: " + ", ".join(f"{x}->{y}" for x, y in fixed[:15]), flush=True)
        m = align(script_words, words)
        s_norm = [norm(w) for w in script_words]

        def phrase_time(phrase):
            p = [norm(w) for w in phrase.split()]
            p = [w for w in p if w]
            for j in range(len(s_norm) - len(p) + 1):
                if s_norm[j:j + len(p)] == p:
                    return cut_at(words, m[j]) if j > 0 else 0.0
            print(f"  DIQQET: '{phrase}' metnde tapilmadi, oturulur.")
            return None

        # sekil sehnleri
        T = [0.0] + [cut_at(words, m[j]) for j in starts[1:]]
        for i in range(1, len(T)):
            T[i] = max(T[i], T[i - 1] + 1.5)

        # kartlar (intro + fesiller)
        cards = []
        for title, body in chapters:
            c = phrase_time(" ".join(body.split()[:6]))
            if not c:
                continue
            near = min(range(1, len(T)), key=lambda i: abs(T[i] - c))
            if abs(T[near] - c) < 2.5:
                T[near] = c
            cards.append({"t": c, "kind": "chapter", "title": title, "dur": CARD})
        cards.sort(key=lambda c: c["t"])
        for n, c in enumerate(cards, 1):
            c["n"] = n
        if cfg.get("intro", True) and cfg.get("channel"):
            t_intro = cards[0]["t"] if cards else 0.0
            cards.insert(0, {"t": t_intro, "kind": "intro", "title": cfg["channel"],
                             "sub": cfg.get("title", ""), "dur": INTRO})
        cut_times = sorted(set(c["t"] for c in cards))

        # ekler (qrafik / xerite / qezet)
        inserts = []
        for spec in cfg.get("inserts", []):
            s = phrase_time(spec["start"])
            if s is None:
                continue
            if spec["type"] == "newspaper":
                e = s + float(spec.get("seconds", 6))
            else:
                e = phrase_time(spec["end"]) if spec.get("end") else None
                if e is None or e <= s + 2:
                    e = s + 12
                e = min(e, s + 30.0)
            keyt = {"start": s}
            if spec["type"] == "chart":
                keyt["peak"] = phrase_time(spec.get("peak", "")) or s + 2
                keyt["crash"] = phrase_time(spec.get("crash", "")) or e - 4
            if spec["type"] == "map":
                keyt["keys"] = [(phrase_time(p) or s, v, lab) for p, v, lab in spec.get("keys", [])]
            inserts.append({"spec": spec, "s": s, "e": min(e, dur), "t": keyt})
        inserts.sort(key=lambda x: x["s"])
        for a, b in zip(inserts, inserts[1:]):
            a["e"] = min(a["e"], b["s"])

        # zaman parcalari (orijinal vaxt)
        bset = set(T[1:]) | set(cut_times)
        for ins in inserts:
            bset |= {ins["s"], ins["e"]}
        bounds = sorted(b for b in bset if 0 < b < dur)
        edges = [0.0] + bounds + [dur]

        def source(tm):
            for k, ins in enumerate(inserts):
                if ins["s"] <= tm < ins["e"]:
                    return ("ins", k)
            i = max(j for j in range(len(T)) if T[j] <= tm)
            return ("img", i)

        pieces = []
        for a, b in zip(edges, edges[1:]):
            if b - a < 1e-3:
                continue
            src = source((a + b) / 2)
            if pieces and pieces[-1]["src"] == src and a not in cut_times:
                pieces[-1]["b"] = b
            else:
                pieces.append({"src": src, "a": a, "b": b})
        merged = []
        for p in pieces:
            if merged and p["b"] - p["a"] < 1.2 and p["src"][0] == "img" and p["a"] not in cut_times:
                merged[-1]["b"] = p["b"]
            else:
                merged.append(p)
        pieces = merged

        MAX_IMG = 16.0
        split_pieces = []
        for p in pieces:
            L = p["b"] - p["a"]
            if p["src"][0] == "img" and L > MAX_IMG:
                n_sub = int(math.ceil(L / MAX_IMG))
                print(f"  DIQQET: {os.path.basename(imgs[p['src'][1]])} {L:.0f} san uzundur, "
                      f"{n_sub} hisseye bolunur (ses ve metn uygunsuzlugu ola biler).")
                step = L / n_sub
                for k in range(n_sub):
                    split_pieces.append({"src": p["src"], "a": p["a"] + k * step,
                                         "b": p["a"] + (k + 1) * step})
            else:
                split_pieces.append(p)
        pieces = split_pieces

        def _shift0(t, strict=False):
            return t + sum(c["dur"] for c in cards if (c["t"] < t if strict else c["t"] <= t))

        hook_lines = cfg.get("hook", [])
        if isinstance(hook_lines, str):
            hook_lines = [hook_lines]
        HOOK_DT = 0.05                              # herf yazilma suretli (saniye)
        HOOK_GAP = float(cfg.get("hook_gap", 2.0))  # setirler arasi fasile (saniye)
        HOOK_FS, HOOK_PITCH, HOOK_EXTRA = 64, 96, 30
        hook_layout = []
        HOOK_TOTAL = 0.0
        if hook_lines:
            _wf = font(F_BLACK, HOOK_FS)
            _d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            wrapped = [wrap(l.upper(), _wf, 1500, _d0) for l in hook_lines]
            n_sub = sum(len(w) for w in wrapped)
            block_h = n_sub * HOOK_PITCH + (len(wrapped) - 1) * HOOK_EXTRA
            y_cur = 540 - block_h / 2 + HOOK_PITCH / 2
            t_cur = 0.7
            for w in wrapped:
                chars = sum(len(x) for x in w)
                ys = []
                for _k in range(len(w)):
                    ys.append(int(y_cur))
                    y_cur += HOOK_PITCH
                y_cur += HOOK_EXTRA
                hook_layout.append({"subs": w, "ys": ys, "t0": t_cur, "chars": chars})
                t_cur += chars * HOOK_DT + HOOK_GAP
            HOOK_TOTAL = (t_cur - HOOK_GAP) + 1.8

        def shift(t, strict=False):
            return HOOK_TOTAL + _shift0(t, strict)

        segs = []
        for c in sorted(cards, key=lambda c: (c["t"], c["kind"] != "intro")):
            c["new"] = shift(c["t"], strict=True) + acc_same(cards, c)
            segs.append(("black", None, c["new"], None))
        for p in pieces:
            segs.append((p["src"][0], p, shift(p["a"]), p["a"]))
        segs.sort(key=lambda s: s[2])
        total = dur + sum(c["dur"] for c in cards) + HOOK_TOTAL
        fr = [round(s[2] * FPS) for s in segs] + [round(total * FPS)]
        ov = round(FADE * FPS)
        print(f"{len(imgs)} sekil, {len(inserts)} elave, {len(cards)} kart, ses {dur:.0f} san")

        # render isleri
        anim_objs = {}
        jobs, mk = [], 0
        for i, (kind, p, st, t0) in enumerate(segs):
            frames = fr[i + 1] - fr[i] + (ov if i < len(segs) - 1 else 0)
            if kind == "black":
                jobs.append((i, "black", None, frames, 0, tmp))
            elif kind == "img":
                jobs.append((i, "img", (imgs[p["src"][1]], KINDS[mk % len(KINDS)]), frames, 0, tmp))
                mk += 1
            else:
                k = p["src"][1]
                ins = inserts[k]
                typ = ins["spec"]["type"]
                if typ == "newspaper":
                    if k not in anim_objs:
                        png = os.path.join(tmp, f"news_{k}.jpg")
                        ii = source(max(0, ins["s"] - 0.1))
                        base_img = imgs[ii[1]] if ii[0] == "img" else imgs[0]
                        newspaper(ins["spec"], base_img, base_img, png)
                        anim_objs[k] = png
                    jobs.append((i, "img", (anim_objs[k], "zoom_in"), frames, 0, tmp))
                else:
                    if k not in anim_objs:
                        anim_objs[k] = Chart(ins["spec"], ins["t"]) if typ == "chart" else USMap(ins["spec"], ins["t"])
                    jobs.append((i, "anim", anim_objs[k], frames, t0, tmp))
        _prog["done"] = 0
        _prog["total"] = len(jobs) + (1 if HOOK_TOTAL > 0 else 0)
        print(f"Klipler hazirlanir ({_prog['total']} klip)...", flush=True)
        with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) // 2)) as ex:
            clips = list(ex.map(make_clip, jobs))

        if HOOK_TOTAL > 0:
            hook_clip = make_clip((-1, "black", None, round(HOOK_TOTAL * FPS) + ov, 0, tmp))
            clips = [hook_clip] + clips
            fr = [0] + fr
            print(f"Hook ({len(hook_lines)} setir, {HOOK_TOTAL:.1f} san) elave olundu.")

        print("Ses hazirlanir...", flush=True)
        # danisiq sesi (kartlarda sukut)
        voice_tl = os.path.join(tmp, "voice_tl.wav")
        e2 = [0.0] + cut_times + [dur]
        parts, labels = [], []
        for i in range(len(e2) - 1):
            parts.append(f"[0:a]atrim=start={e2[i]:.3f}:end={e2[i+1]:.3f},asetpts=PTS-STARTPTS[p{i}]")
            labels.append(f"[p{i}]")
            if i < len(e2) - 2:
                sil = sum(c["dur"] for c in cards if abs(c["t"] - e2[i + 1]) < 1e-6)
                parts.append(f"aevalsrc=0|0:d={sil}:s=44100[z{i}]")
                labels.append(f"[z{i}]")
        if len(labels) == 1:
            parts.append("[p0]anull[raw]" if LOUDNORM else "[p0]anull[out]")
        else:
            parts.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1" + ("[raw]" if LOUDNORM else "[out]"))
        if LOUDNORM:
            parts.append("[raw]loudnorm=I=-16:TP=-1.5:LRA=11[out]")
        run(["ffmpeg", "-y", "-v", "error", "-i", voice, "-filter_complex", ";".join(parts),
             "-map", "[out]", "-ar", "44100", "-ac", "2", voice_tl])

        # ASS
        ev = []
        if SUBTITLES:
            groups = subtitle_groups(words, cut_times)
            for gi, g in enumerate(groups):
                n = len(g)
                bounds = [shift(g[0]["s"])]
                for k in range(n - 1):
                    bounds.append(shift(word_bound(g[k], g[k + 1])))
                end_b = shift(g[-1]["e"]) + 0.2
                if gi + 1 < len(groups):
                    end_b = min(end_b, shift(groups[gi + 1][0]["s"]))
                bounds.append(end_b)
                plain = [ass_escape(w["w"]) for w in g]
                for i in range(n):
                    a, b = bounds[i], bounds[i + 1]
                    if b <= a:
                        continue
                    parts = list(plain)
                    parts[i] = "{\\c" + HILITE + "}" + plain[i] + "{\\c" + RESET + "}"
                    ev.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Sub,,0,0,0,,"
                              + " ".join(parts))
        hook_meta = []
        for hl in hook_layout:
            off = 0
            for ln, y in zip(hl["subs"], hl["ys"]):
                L = len(ln)
                for c in range(1, L + 1):
                    t_on = hl["t0"] + (off + c - 1) * HOOK_DT
                    t_off = hl["t0"] + (off + c) * HOOK_DT if c < L else HOOK_TOTAL
                    fx = "{\\pos(960," + str(y) + ")" + ("\\fad(0,350)}" if c == L else "}")
                    ev.append(f"Dialogue: 2,{ass_time(t_on)},{ass_time(t_off)},Hook,,0,0,0,,"
                              f"{fx}{ass_escape(ln[:c])}{{\\alpha&HFF&}}{ass_escape(ln[c:])}")
                off += L
            hook_meta.append((hl["t0"], hl["chars"]))

        nums = []
        if NUMBERS:
            for t, txt in find_numbers(words):
                if any(ins["s"] - 0.5 <= t < ins["e"] for ins in inserts):
                    continue
                nums.append((t, txt))
                ev += counter_events(shift(t), txt)
        dt = 0.07
        for c in cards:
            s0 = c["new"]
            if c["kind"] == "intro":
                ev.append(f"Dialogue: 2,{ass_time(s0 + 0.2)},{ass_time(s0 + INTRO - 0.1)},Logo,,0,0,0,,"
                          "{\\pos(960,500)\\fad(700,400)\\fsp34\\t(0,2200,\\fsp10)}" + ass_escape(c["title"]))
                ev.append(f"Dialogue: 2,{ass_time(s0 + 0.8)},{ass_time(s0 + INTRO - 0.1)},Small,,0,0,0,,"
                          "{\\an5\\pos(960,590)\\fad(600,400)\\1c&H3C46E6&\\p1}m 0 0 l 520 0 l 520 4 l 0 4{\\p0}")
                if c.get("sub"):
                    ev.append(f"Dialogue: 2,{ass_time(s0 + 1.2)},{ass_time(s0 + INTRO - 0.1)},Small,,0,0,0,,"
                              "{\\pos(960,650)\\fad(600,400)\\fs40}" + ass_escape(c["sub"]))
                continue
            ev.append(f"Dialogue: 2,{ass_time(s0 + 0.3)},{ass_time(s0 + CARD - 0.1)},Small,,0,0,0,,"
                      f"{{\\pos(960,440)\\fad(400,300)}}CHAPTER {c['n']}")
            title, L, t0 = c["title"], len(c["title"]), s0 + 0.5
            # uzun basliq bir setirde sigsin: hecmi avtomatik kicilt
            _gf = font(["georgiab.ttf", "DejaVuSerif-Bold.ttf"], 96)
            _dm = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            _w96 = _dm.textlength(title, font=_gf) + 4 * L
            fsz = int(min(96, 96 * 1550 / max(_w96, 1)))
            for k in range(1, L + 1):
                a = t0 + (k - 1) * dt
                b = t0 + k * dt if k < L else s0 + CARD - 0.1
                fx = "{\\pos(960,540)\\fs" + str(fsz) + ("\\fad(0,300)}" if k == L else "}")
                ev.append(f"Dialogue: 2,{ass_time(a)},{ass_time(b)},Card,,0,0,0,,"
                          f"{fx}{ass_escape(title[:k])}{{\\alpha&HFF&}}{ass_escape(title[k:])}")
        with open(os.path.join(tmp, "subs.ass"), "w", encoding="utf-8") as f:
            f.write(ASS_HEAD + "\n".join(ev) + "\n")

        fonts = os.path.join(tmp, "fonts")
        os.makedirs(fonts, exist_ok=True)
        for fn in ("arial.ttf", "arialbd.ttf", "ariblk.ttf", "georgia.ttf", "georgiab.ttf"):
            src = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", fn)
            if os.path.exists(src):
                shutil.copy(src, fonts)

        print("Ses effektleri hazirlanir...", flush=True)
        # ses effektleri
        sfx_path = None
        if SFX:
            lib = make_sfx(tmp)
            events = []
            for c in cards:
                s0 = c["new"]
                events.append((lib["boom"], s0, 1.0))
                events.append((lib["whoosh"], s0 + c["dur"] - 0.55, 0.6))
                if c["kind"] == "chapter":
                    events.append((make_ticks(tmp, len(c["title"]), dt, "type"), s0 + 0.5, 0.5))
            for t, _ in nums:
                events.append((lib["pop"], shift(t) - 0.05, 0.35))
                events.append((make_ticks(tmp, 14, 0.05, "tick"), shift(t), 0.22))
            for a_h, nch in hook_meta:
                events.append((make_ticks(tmp, nch, HOOK_DT, "type"), a_h, 0.45))
            for ins in inserts:
                typ = ins["spec"]["type"]
                events.append((lib["slap"] if typ == "newspaper" else lib["whoosh"],
                               shift(ins["s"]) + (0.05 if typ == "newspaper" else -0.4), 0.8))
                if typ == "chart":
                    events.append((lib["boom"], shift(ins["t"]["crash"]), 0.8))
            if events:
                ins_, parts = [], []
                for i, (p, t, v) in enumerate(events):
                    ins_ += ["-i", p]
                    ms = max(0, int(t * 1000))
                    parts.append(f"[{i}:a]volume={v},adelay={ms}|{ms}[e{i}]")
                parts.append("".join(f"[e{i}]" for i in range(len(events)))
                             + f"amix=inputs={len(events)}:normalize=0:duration=longest,"
                               f"apad,atrim=0:{total:.3f}[out]")
                sfx_path = os.path.join(tmp, "sfx.wav")
                g = os.path.join(tmp, "sfx_graph.txt")
                with open(g, "w") as f:
                    f.write(";\n".join(parts))
                run(["ffmpeg", "-y", "-v", "error", *ins_, graph_flag(), g,
                     "-map", "[out]", "-ar", "44100", "-ac", "2", sfx_path])

        # yekun montaj
        inputs, parts, last = [], [], "[0:v]"
        for c in clips:
            inputs += ["-i", c]
        for i in range(1, len(clips)):
            parts.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE}:"
                         f"offset={fr[i] / FPS:.3f}[x{i}]")
            last = f"[x{i}]"
        look = ("eq=contrast=1.06:saturation=0.9:gamma=0.97,vignette=angle=PI/5,"
                "noise=alls=3:allf=t," if FILM_LOOK else "")
        subs = "subtitles=subs.ass" + (":fontsdir=fonts" if os.listdir(fonts) else "") + ","
        parts.append(f"{last}{look}{subs}fade=t=in:st=0:d=1,"
                     f"fade=t=out:st={total - 1.5:.3f}:d=1.5,format=yuv420p[v]")
        n = len(clips)
        inputs += ["-i", voice_tl]
        hd_ms = round(HOOK_TOTAL * 1000)
        voice_pre = f"adelay={hd_ms}|{hd_ms}," if hd_ms > 0 else ""
        mix = [f"[{n}:a]{voice_pre}aformat=channel_layouts=stereo,asplit=2[vo][vk]"]
        streams, idx = ["[vo]"], n + 1
        if sfx_path:
            inputs += ["-i", sfx_path]
            streams.append(f"[{idx}:a]")
            idx += 1
        if music:
            inputs += ["-stream_loop", "-1", "-i", music]
            mix.append(f"[{idx}:a]aformat=channel_layouts=stereo,volume={MUSIC_VOL},"
                       f"atrim=0:{total:.3f},afade=t=out:st={total - 3:.3f}:d=3[m];"
                       f"[m][vk]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=500[duck]")
            streams.append("[duck]")
            print("Arxa fon musiqisi elave olunur.")
        else:
            mix.append("[vk]anullsink")
        mix.append("".join(streams) + f"amix=inputs={len(streams)}:duration=first:normalize=0[a]")
        parts += mix
        graph = os.path.join(tmp, "graph.txt")
        with open(graph, "w", encoding="utf-8") as f:
            f.write(";\n".join(parts))
        print("Montaj edilir...")
        main_out = os.path.join(tmp, "main.mp4") if cfg.get("outro", True) else OUTPUT
        run(["ffmpeg", "-y", "-v", "error", "-stats", *inputs, graph_flag(), graph,
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             "-t", f"{total:.3f}", main_out], cwd=tmp)

        # altyazi (.srt) ve fesil siyahisi (.txt)
        groups_srt = subtitle_groups(words, cut_times)
        write_srt(os.path.splitext(OUTPUT)[0] + ".srt", groups_srt, shift)
        write_chapters(os.path.splitext(OUTPUT)[0] + "-fesiller.txt", cards, cfg.get("title", "VIDEO"))
        print("Altyazi (.srt) ve fesil siyahisi (.txt) hazirlandi.")

        # outro karti
        if cfg.get("outro", True):
            outro = make_outro(tmp, cfg.get("channel", ""), cfg.get("outro_sub", "Subscribe for more"))
            lst = os.path.join(tmp, "final_concat.txt")
            with open(lst, "w", encoding="utf-8") as f:
                f.write(f"file '{main_out.replace(chr(92), '/')}'\nfile '{outro.replace(chr(92), '/')}'\n")
            try:
                run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                     "-c", "copy", OUTPUT])
            except Exception:
                print("  DIQQET: outro birbasa birlesmedi, yenidencodlastiriliir...")
                run(["ffmpeg", "-y", "-v", "error", "-i", main_out, "-i", outro, "-filter_complex",
                     "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                     "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", OUTPUT])

        # thumbnail
        try:
            cand = total * 0.08
            for g1, g2 in zip(groups_srt, groups_srt[1:]):
                e1, s2 = shift(g1[-1]["e"]), shift(g2[0]["s"])
                if s2 - e1 > 1.2 and e1 > total * 0.04:
                    cand = e1 + (s2 - e1) / 2
                    break
            thumb_t = min(cand, total - 0.5)
            fr_png = os.path.join(tmp, "thumb_raw.png")
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{thumb_t:.2f}", "-i", OUTPUT,
                 "-frames:v", "1", fr_png])
            im = Image.open(fr_png).convert("RGB")
            d = ImageDraw.Draw(im)
            grad = Image.new("L", (1, H), 0)
            for y in range(H):
                grad.putpixel((0, y), int(180 * max(0, (y - H * 0.55) / (H * 0.45))))
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow.putalpha(grad.resize((W, H)))
            im = Image.alpha_composite(im.convert("RGBA"), shadow).convert("RGB")
            d = ImageDraw.Draw(im)
            ttl = cfg.get("thumb_title", cfg.get("title", ""))
            if ttl:
                f1 = font(F_BLACK, 130)
                lines = wrap(ttl.upper(), f1, W - 160, d)
                y = H - 70 - 140 * len(lines)
                for line in lines:
                    d.text((80, y), line, font=f1, fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
                    y += 140
            im.save(os.path.splitext(OUTPUT)[0] + "-thumbnail.jpg", quality=95)
            print("Thumbnail hazirlandi.")
        except Exception as e:
            print(f"  DIQQET: thumbnail yaradilmadi ({e})")

        print(f"\nHAZIRDIR: {OUTPUT}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def acc_same(cards, c):
    """eyni anda olan kartlardan evvelkilerin muddeti (intro fesil kartindan evvel)"""
    same = [x for x in sorted(cards, key=lambda x: x["kind"] != "intro") if abs(x["t"] - c["t"]) < 1e-6]
    total = 0.0
    for x in same:
        if x is c:
            break
        total += x["dur"]
    return total


if __name__ == "__main__":
    main()
