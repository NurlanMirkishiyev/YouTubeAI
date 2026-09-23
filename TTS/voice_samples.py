"""Narrator secimi ucun eyni metni bir nece Kokoro sesi ile render edir -> Output/voice_samples/"""
import time, os
import numpy as np, soundfile as sf
from kokoro import KPipeline

OUT = r"C:\YouTubeAI\Output\voice_samples"
VOICES = ["am_michael", "am_adam", "am_fenrir", "bm_george", "bm_lewis", "af_heart", "af_bella", "bf_emma"]
TEXT = ("Welcome to ELI5 Business. Today we explain the difference between a trademark, "
        "a copyright, and a patent, in the simplest way possible. Think of it like this: "
        "a trademark protects your name, a copyright protects your creative work, "
        "and a patent protects your invention.")

os.makedirs(OUT, exist_ok=True)
pipe = KPipeline(lang_code="a" )
for v in VOICES:
    t = time.time()
    chunks = [audio for _, _, audio in pipe(TEXT, voice=v, speed=1.0)]
    audio = np.concatenate(chunks)
    path = os.path.join(OUT, f"{v}.wav")
    sf.write(path, audio, 24000)
    print(f"{v:12s} {len(audio)/24000:5.1f}s audio  rendered in {time.time()-t:4.1f}s")
