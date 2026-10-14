# Pipeline-ı sıfırdan bərpa etmək (Windows)

Bu repo pipeline-ın bütün kodunu, bayquş istinad şəkillərini, şriftləri və konfiqləri saxlayır.
Repoda olmayanlar: `.env` (açar), virtual mühitlər (`.venv`), `node_modules`, modellər (ilk run-da avtomatik yüklənir)
və hazırlanmış videolar (`Episodes\`, `Hazir_Videolar\`).

## 1. Lazım olan proqramlar
- Git, [uv](https://docs.astral.sh/uv/) (Python mühitləri üçün), Node.js 24+ (npm ilə), ffmpeg (PATH-da; `ffmpeg`, `ffprobe`)
- NVIDIA GPU + driver (musiqi üçün CUDA 12.8; GPU yoxdursa musiqi CPU-da, çox yavaş işləyir)
- Yoxlanmış versiyalar (2026-10-15): Python 3.11 (Projects), 3.12 (TTS, MusicGen), Node 24.15, ffmpeg 8.1

## 2. Kodu yüklə
```powershell
git clone https://github.com/NurlanMirkishiyev/YouTubeAI.git C:\YouTubeAI
cd C:\YouTubeAI
```
Yol `C:\YouTubeAI` olmalıdır (CLAUDE.md-dəki əmrlər bu yola bağlıdır).

## 3. Açar
`.env.example` → `.env` kopyala və `OPENAI_API_KEY` yaz (gpt-image-2 və GPT üçün).

## 4. Python mühitləri (3 ədəd)
```powershell
uv venv Projects\.venv --python 3.11
uv pip install --python Projects\.venv\Scripts\python.exe -r setup\requirements-projects.txt

uv venv TTS\.venv --python 3.12
uv pip install --python TTS\.venv\Scripts\python.exe -r setup\requirements-tts.txt

uv venv MusicGen\.venv --python 3.12
uv pip install --python MusicGen\.venv\Scripts\python.exe -r setup\requirements-musicgen.txt --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
```

## 5. Remotion
```powershell
cd Remotion; npm ci; npx tsc --noEmit; cd ..
```

## 6. Modellər
- Kokoro (səs) — ilk run-da Hugging Face-dən avtomatik yüklənir.
- Stable Audio Open (`stabilityai/stable-audio-open-1.0`) — **gated** modeldir: Hugging Face-də model səhifəsində
  şərtləri qəbul et, sonra `MusicGen\.venv\Scripts\hf auth login` (və ya `HF_TOKEN` mühit dəyişəni).

## 7. Yoxlama
```powershell
Projects\.venv\Scripts\python -m pytest -q Projects/tests
```
Sonra Claude Code-da: `Video: <ssenari faylı>` (ssenari `Ssenariler\` qovluğunda) — qaydalar `CLAUDE.md`-də.
