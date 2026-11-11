"""Motor para Windows (y Linux / Mac Intel): faster-whisper (CTranslate2).

Usa la GPU NVIDIA (CUDA) si está disponible y, si no, el procesador (CPU).
Se puede forzar con la variable de entorno TRANSCRIPTOR_DEVICE=cpu o =cuda.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

import numpy as np


def _add_nvidia_dlls() -> None:
    """En Windows, hace visibles las DLL de CUDA instaladas con pip
    (nvidia-cublas-cu12 / nvidia-cudnn-cu12, ver instalar-gpu.bat)."""
    if sys.platform != "win32":
        return
    try:
        import nvidia  # paquete de espacio de nombres creado por esas ruedas
    except ImportError:
        return
    for base in getattr(nvidia, "__path__", []):
        for sub in ("cublas", "cudnn", "cuda_nvrtc"):
            d = Path(base) / sub / "bin"
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


_add_nvidia_dlls()

import ctranslate2  # noqa: E402
from faster_whisper import WhisperModel, decode_audio  # noqa: E402

MODELS = {
    "maximo": "large-v3",
    "preciso": "large-v3-turbo",
    "equilibrado": "medium",
    "rapido": "small",
}


def _initial_device() -> str:
    forced = os.environ.get("TRANSCRIPTOR_DEVICE", "auto").lower()
    if forced in ("cpu", "cuda"):
        return forced
    try:
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


_device = _initial_device()
_models: dict[tuple[str, str], WhisperModel] = {}


def describe() -> str:
    return "faster-whisper · " + ("GPU NVIDIA (CUDA)" if _device == "cuda" else "CPU")


def _get(model: str) -> WhisperModel:
    global _device
    key = (model, _device)
    if key not in _models:
        try:
            if _device == "cuda":
                m = WhisperModel(model, device="cuda", compute_type="float16")
            else:
                m = WhisperModel(
                    model, device="cpu", compute_type="int8",
                    cpu_threads=os.cpu_count() or 4,
                )
        except Exception:
            if _device != "cuda":
                raise
            _device = "cpu"  # sin CUDA utilizable: seguir en CPU
            return _get(model)
        _models[key] = m
    return _models[key]


def _fallback_cpu(exc: Exception) -> bool:
    """Si falla la GPU (p. ej. falta cuDNN), cambia a CPU y permite reintentar."""
    global _device
    if _device == "cuda":
        print(f"[transcriptor] GPU no disponible ({exc}); usando CPU.", file=sys.stderr)
        _device = "cpu"
        return True
    return False


def load_audio(path: str) -> np.ndarray:
    """Audio/video → float32 mono 16 kHz (PyAV, no requiere ffmpeg instalado)."""
    return decode_audio(str(path), sampling_rate=16000)


def load_model(model: str) -> None:
    _get(model)


def language_probs(chunk: np.ndarray, model: str) -> dict[str, float]:
    """Probabilidades de idioma para una ventana de hasta 30 s."""
    try:
        _, _, probs = _get(model).detect_language(audio=chunk)
    except RuntimeError as e:
        if not _fallback_cpu(e):
            raise
        _, _, probs = _get(model).detect_language(audio=chunk)
    return dict(probs)


def _run(audio, language, model, prompt, words, cb) -> dict:
    segments, info = _get(model).transcribe(
        audio,
        language=language,
        initial_prompt=prompt or None,
        condition_on_previous_text=False,  # reduce alucinaciones/repeticiones
        word_timestamps=words,
        beam_size=5,
    )
    out = []
    for s in segments:  # generador: se transcribe a medida que se itera
        out.append(
            {
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end}
                    for w in (s.words or [])
                ],
            }
        )
        if info.duration:
            cb(min(s.end / info.duration, 1.0))
    cb(1.0)
    return {
        "language": info.language,
        "text": "".join(s["text"] for s in out).strip(),
        "segments": out,
    }


def transcribe(
    audio: np.ndarray,
    language: str,
    model: str,
    prompt: str | None,
    words: bool,
    cb: Callable[[float], None],
) -> dict:
    try:
        return _run(audio, language, model, prompt, words, cb)
    except RuntimeError as e:
        if not _fallback_cpu(e):
            raise
        return _run(audio, language, model, prompt, words, cb)
