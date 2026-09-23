import time
import cuda_env  # noqa: F401  -- cuBLAS/cuDNN DLL-lerini PATH-a elave edir (faster_whisper-den evvel)
from faster_whisper import WhisperModel

t = time.time()
m = WhisperModel("small", device="cuda", compute_type="float16")
segs, info = m.transcribe(r"C:\YouTubeAI\Temp\tts_test_am_michael.wav", word_timestamps=True)
for s in segs:
    print("[%.2f -> %.2f] %s" % (s.start, s.end, s.text))
    for w in (s.words or [])[:5]:
        print("    word %.2f-%.2f %s" % (w.start, w.end, w.word))
print("whisper ok in %.1fs (lang=%s)" % (time.time() - t, info.language))
