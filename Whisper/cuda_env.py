"""faster-whisper/ctranslate2 uchun CUDA DLL-lerini (cuBLAS 12, cuDNN 9) PATH-a elave edir.
ctranslate2 DLL-i LoadLibrary ile yukleyir -> os.add_dll_directory kifayet etmir, PATH lazimdir.
Import et: `import cuda_env` (faster_whisper-den EVVEL)."""
import os, sys
from pathlib import Path

_SITE = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
_BIN_DIRS = [_SITE / "cublas" / "bin", _SITE / "cudnn" / "bin"]

def setup_cuda_path() -> list[str]:
    added = []
    for d in _BIN_DIRS:
        if d.is_dir() and str(d) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")
            added.append(str(d))
    missing = [str(d) for d in _BIN_DIRS if not d.is_dir()]
    if missing:
        raise RuntimeError(
            "CUDA DLL qovluqlari tapilmadi: %s\n"
            "Duzelis: uv pip install --python .venv/Scripts/python.exe nvidia-cublas-cu12 'nvidia-cudnn-cu12>=9,<10'"
            % missing)
    return added

setup_cuda_path()
