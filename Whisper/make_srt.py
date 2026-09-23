"""Audio -> SRT (cumle seviyyesi) + word-level JSON.
Istifade: python make_srt.py <audio.wav> [out_basename]  -> out_basename.srt, out_basename.words.json
"""
import sys, json, time, os
import cuda_env  # noqa: F401
from faster_whisper import WhisperModel

MAX_CHARS = 42      # bir subtitle setrinin max uzunlugu (YouTube ucun rahat oxunur)
MAX_DUR = 5.0       # bir subtitle blokunun max muddeti (san)

def fmt(t: float) -> str:
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def chunk_words(words):
    """Sozleri MAX_CHARS / MAX_DUR / durgu isaresine gore bloklara bolur."""
    blocks, cur = [], []
    for w in words:
        cur.append(w)
        text = "".join(x["word"] for x in cur).strip()
        too_long = len(text) > MAX_CHARS or (cur[-1]["end"] - cur[0]["start"]) > MAX_DUR
        ends_sentence = w["word"].rstrip().endswith((".", "?", "!"))
        if too_long and len(cur) > 1:
            blocks.append(cur[:-1]); cur = [w]
        elif ends_sentence:
            blocks.append(cur); cur = []
    if cur: blocks.append(cur)
    return blocks

def main():
    audio = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(audio)[0]
    t = time.time()
    model = WhisperModel("small", device="cuda", compute_type="float16")
    segs, info = model.transcribe(audio, word_timestamps=True, language="en",
                                  initial_prompt="ELI5 Business. Trademark, copyright, patent, SaaS, B2B, ROI.")
    words = [{"word": w.word, "start": w.start, "end": w.end} for s in segs for w in (s.words or [])]
    if not words:
        raise SystemExit("Whisper hec bir soz tapmadi: " + audio)
    with open(base + ".words.json", "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    with open(base + ".srt", "w", encoding="utf-8") as f:
        for i, b in enumerate(chunk_words(words), 1):
            f.write(f"{i}\n{fmt(b[0]['start'])} --> {fmt(b[-1]['end'])}\n{''.join(w['word'] for w in b).strip()}\n\n")
    print(f"{len(words)} words, srt -> {base}.srt  ({time.time()-t:.1f}s)")

if __name__ == "__main__":
    main()
