"""Separación de hablantes (diarización) local con sherpa-onnx.

Usa el modelo de segmentación de pyannote 3.0 (ONNX) y huellas de voz de
WeSpeaker. No requiere cuenta ni token: los modelos se descargan una vez desde
las versiones públicas de sherpa-onnx a ~/.cache/transcriptor.
"""

from __future__ import annotations

import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import sherpa_onnx

MODELS_DIR = Path.home() / ".cache" / "transcriptor"
_BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
SEG_DIR = MODELS_DIR / "sherpa-onnx-pyannote-segmentation-3-0"
SEG_MODEL = SEG_DIR / "model.onnx"
SEG_URL = f"{_BASE}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
EMB_MODEL = MODELS_DIR / "wespeaker_en_voxceleb_resnet34_LM.onnx"
# (sic) "recongition" es el nombre real de la versión publicada
EMB_URL = f"{_BASE}/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx"

# Distancia para agrupar voces cuando no se indica el número de hablantes.
# Más alto = menos hablantes; más bajo = más hablantes.
CLUSTER_THRESHOLD = 0.5


@dataclass
class Turn:
    start: float
    end: float
    speaker: int  # 1, 2, 3… en orden de aparición


def ensure_models() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not SEG_MODEL.exists():
        tmp = MODELS_DIR / "seg.tar.bz2"
        urllib.request.urlretrieve(SEG_URL, tmp)
        with tarfile.open(tmp) as tf:
            try:
                tf.extractall(MODELS_DIR, filter="data")
            except TypeError:  # Python < 3.12 sin el parámetro filter
                tf.extractall(MODELS_DIR)
        tmp.unlink()
    if not EMB_MODEL.exists():
        tmp = EMB_MODEL.with_suffix(".part")
        urllib.request.urlretrieve(EMB_URL, tmp)
        tmp.rename(EMB_MODEL)


_cache: dict[int, sherpa_onnx.OfflineSpeakerDiarization] = {}


def _engine(num_speakers: int | None) -> sherpa_onnx.OfflineSpeakerDiarization:
    key = num_speakers or -1
    if key not in _cache:
        ensure_models()
        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=str(SEG_MODEL)
                ),
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(EMB_MODEL)),
            clustering=sherpa_onnx.FastClusteringConfig(
                num_clusters=key, threshold=CLUSTER_THRESHOLD
            ),
            min_duration_on=0.3,
            min_duration_off=0.5,
        )
        if not config.validate():
            raise RuntimeError("Configuración de diarización inválida.")
        _cache[key] = sherpa_onnx.OfflineSpeakerDiarization(config)
    return _cache[key]


def diarize(
    audio: np.ndarray,
    num_speakers: int | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> list[Turn]:
    """audio: float32 mono a 16 kHz. Devuelve turnos con hablantes 1, 2, 3…"""
    sd = _engine(num_speakers)
    if sd.sample_rate != 16000:
        raise RuntimeError(f"El modelo espera {sd.sample_rate} Hz.")

    def cb(done: int, total: int) -> int:
        if on_progress and total:
            on_progress(done / total)
        return 0

    raw = sd.process(np.ascontiguousarray(audio, dtype=np.float32), callback=cb)
    turns = raw.sort_by_start_time()

    # Renumera por orden de aparición: quien habla primero es "Hablante 1".
    order: dict[int, int] = {}
    out = []
    for t in turns:
        order.setdefault(t.speaker, len(order) + 1)
        out.append(Turn(t.start, t.end, order[t.speaker]))
    return out
