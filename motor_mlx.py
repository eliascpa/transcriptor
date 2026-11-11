"""Motor para Mac con Apple Silicon: Whisper sobre MLX (GPU de Apple)."""

from __future__ import annotations

import contextlib
import importlib
import types
from typing import Callable

import mlx.core as mx
import mlx_whisper
import numpy as np
import tqdm
from mlx_whisper.audio import N_SAMPLES, load_audio as _load_audio
from mlx_whisper.audio import log_mel_spectrogram, pad_or_trim
from mlx_whisper.decoding import detect_language
from mlx_whisper.transcribe import ModelHolder

# El paquete reexporta la función `transcribe`, que oculta al módulo del mismo
# nombre; import_module devuelve el módulo real.
_mw_transcribe = importlib.import_module("mlx_whisper.transcribe")

NAME = "MLX · GPU Apple Silicon"
MODELS = {
    "preciso": "mlx-community/whisper-large-v3-turbo",
    "equilibrado": "mlx-community/whisper-medium-mlx",
    "rapido": "mlx-community/whisper-small-mlx",
}


def describe() -> str:
    return NAME


def load_audio(path: str) -> np.ndarray:
    """Audio/video → float32 mono 16 kHz (usa ffmpeg)."""
    return np.array(_load_audio(str(path)))


def load_model(model: str) -> None:
    ModelHolder.get_model(model, mx.float16)  # descarga/carga una sola vez


def language_probs(chunk: np.ndarray, model: str) -> dict[str, float]:
    """Probabilidades de idioma para una ventana de hasta 30 s."""
    m = ModelHolder.get_model(model, mx.float16)
    mel = log_mel_spectrogram(pad_or_trim(mx.array(chunk), N_SAMPLES), n_mels=m.dims.n_mels)
    _, probs = detect_language(m, mel[None])
    return probs[0]


@contextlib.contextmanager
def _track(cb: Callable[[float], None]):
    """Redirige la barra tqdm interna de mlx_whisper a `cb` (0..1).

    Solo sustituye la referencia dentro del módulo de mlx_whisper, no tqdm global.
    """

    class _Bar(tqdm.tqdm):
        def update(self, n=1):
            r = super().update(n)
            if self.total:
                cb(min(self.n / self.total, 1.0))
            return r

    original = _mw_transcribe.tqdm
    _mw_transcribe.tqdm = types.SimpleNamespace(tqdm=_Bar)
    try:
        yield
    finally:
        _mw_transcribe.tqdm = original


def transcribe(
    audio: np.ndarray,
    language: str,
    model: str,
    prompt: str | None,
    words: bool,
    cb: Callable[[float], None],
) -> dict:
    with _track(cb):
        out = mlx_whisper.transcribe(
            mx.array(audio),
            path_or_hf_repo=model,
            language=language,
            initial_prompt=prompt or None,
            condition_on_previous_text=False,  # reduce alucinaciones/repeticiones
            word_timestamps=words,
            verbose=False,  # activa la barra interna que redirigimos
        )
    return {
        "language": out["language"],
        "text": out["text"].strip(),
        "segments": [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "words": [
                    {"word": w["word"], "start": w["start"], "end": w["end"]}
                    for w in s.get("words") or []
                ],
            }
            for s in out["segments"]
        ],
    }
