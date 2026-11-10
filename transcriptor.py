"""Núcleo de transcripción: Whisper (MLX) local para español e inglés,
con separación opcional de hablantes."""

from __future__ import annotations

import contextlib
import importlib
import json
import subprocess
import tempfile
import types
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import mlx.core as mx
import mlx_whisper
import numpy as np
import tqdm
from mlx_whisper.audio import N_SAMPLES, load_audio, log_mel_spectrogram, pad_or_trim
from mlx_whisper.decoding import detect_language
from mlx_whisper.transcribe import ModelHolder

# El paquete reexporta la función `transcribe`, que oculta al módulo del mismo
# nombre; import_module devuelve el módulo real.
_mw_transcribe = importlib.import_module("mlx_whisper.transcribe")

DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
LANGUAGES = {"Automático": None, "Español": "es", "Inglés": "en"}

# on_progress(fracción 0..1, mensaje)
ProgressFn = Callable[[float, str], None]
# Nombres asignados por el usuario: {1: "Ana", 2: "Luis"}
Names = dict[int, str]


@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: int | None = None  # 1, 2, 3… si se separaron hablantes


@dataclass
class Result:
    language: str
    text: str
    segments: list[Segment]

    @property
    def speakers(self) -> list[int]:
        return sorted({s.speaker for s in self.segments if s.speaker is not None})


def speaker_label(spk: int | None, names: Names | None = None) -> str:
    if spk is None:
        return ""
    name = (names or {}).get(spk, "").strip()
    return name or f"Hablante {spk}"


# ---------- Audio y modelo ----------

def _to_wav(src: Path, dst: Path) -> None:
    """Convierte cualquier audio/video a WAV 16 kHz mono con ffmpeg."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
        check=True,
        capture_output=True,
    )


def detect_es_en(audio: mx.array, model: str) -> str:
    """Decide entre 'es' y 'en' promediando hasta 3 ventanas de 30 s.

    Restringir la detección a los dos idiomas de interés evita errores de la
    autodetección general de Whisper (p. ej. confundir español con otro idioma).
    """
    m = ModelHolder.get_model(model, mx.float16)
    last = max(len(audio) - N_SAMPLES, 0)
    starts = sorted({0, last // 2, last})
    es = en = 0.0
    for st in starts:
        chunk = audio[st : st + N_SAMPLES]
        mel = log_mel_spectrogram(pad_or_trim(chunk, N_SAMPLES), n_mels=m.dims.n_mels)
        _, probs = detect_language(m, mel[None])
        es += probs[0].get("es", 0.0)
        en += probs[0].get("en", 0.0)
    return "es" if es >= en else "en"


@contextlib.contextmanager
def _track_whisper(cb: ProgressFn, lo: float, hi: float):
    """Redirige la barra tqdm interna de mlx_whisper a `cb`, en el rango [lo, hi].

    Solo sustituye la referencia dentro del módulo de mlx_whisper, no tqdm global.
    """

    class _Bar(tqdm.tqdm):
        def update(self, n=1):
            r = super().update(n)
            if self.total:
                f = min(self.n / self.total, 1.0)
                cb(lo + (hi - lo) * f, f"Transcribiendo… {f:.0%}")
            return r

    original = _mw_transcribe.tqdm
    _mw_transcribe.tqdm = types.SimpleNamespace(tqdm=_Bar)
    try:
        yield
    finally:
        _mw_transcribe.tqdm = original


# ---------- Asignación de hablantes ----------

def _speaker_at(start: float, end: float, turns) -> int | None:
    """Hablante con mayor solapamiento con [start, end]; si ninguno, el más cercano."""
    if not turns:
        return None
    best, best_ov = None, 0.0
    for t in turns:
        ov = min(end, t.end) - max(start, t.start)
        if ov > best_ov:
            best, best_ov = t.speaker, ov
    if best is not None:
        return best
    mid = (start + end) / 2
    return min(turns, key=lambda t: min(abs(mid - t.start), abs(mid - t.end))).speaker


def _assign_speakers(whisper_segments: list[dict], turns) -> list[Segment]:
    """Asigna hablante por palabra y corta segmentos donde cambia la voz."""
    out: list[Segment] = []
    for seg in whisper_segments:
        words = seg.get("words") or []
        if not words:
            spk = _speaker_at(seg["start"], seg["end"], turns)
            out.append(Segment(seg["start"], seg["end"], seg["text"].strip(), spk))
            continue
        cur: Segment | None = None
        for w in words:
            spk = _speaker_at(w["start"], w["end"], turns)
            if cur is None or spk != cur.speaker:
                if cur and cur.text.strip():
                    cur.text = cur.text.strip()
                    out.append(cur)
                cur = Segment(w["start"], w["end"], "", spk)
            cur.text += w["word"]
            cur.end = w["end"]
        if cur and cur.text.strip():
            cur.text = cur.text.strip()
            out.append(cur)
    return out


# ---------- Transcripción ----------

def transcribe(
    path: str | Path,
    language: str | None = None,
    model: str = DEFAULT_MODEL,
    prompt: str | None = None,
    on_progress: ProgressFn | None = None,
    speakers: bool = False,
    num_speakers: int | None = None,
) -> Result:
    """Transcribe un archivo. language: 'es', 'en' o None (autodetectar).

    prompt: vocabulario/nombres propios para mejorar la precisión.
    on_progress: callback opcional (fracción 0..1, mensaje) para mostrar avance.
    speakers: separar hablantes (Hablante 1, 2, 3…).
    num_speakers: número de hablantes si se conoce (mejora la separación).
    """
    cb = on_progress or (lambda f, msg: None)
    whisper_hi = 0.75 if speakers else 0.99
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        cb(0.0, "Convirtiendo audio…")
        _to_wav(Path(path), wav)
        audio = load_audio(str(wav))
        cb(0.03, "Cargando modelo…")
        ModelHolder.get_model(model, mx.float16)  # descarga/carga una sola vez
        if language is None:
            cb(0.06, "Detectando idioma…")
            language = detect_es_en(audio, model)
        cb(0.10, "Transcribiendo… 0%")
        with _track_whisper(cb, 0.10, whisper_hi):
            out = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=model,
                language=language,
                initial_prompt=prompt or None,
                condition_on_previous_text=False,  # reduce alucinaciones/repeticiones
                word_timestamps=speakers,  # necesario para cortar por hablante
                verbose=False,  # activa la barra interna que redirigimos
            )

    if speakers:
        import diarizacion

        cb(whisper_hi, "Identificando hablantes… 0%")
        turns = diarizacion.diarize(
            np.array(audio),
            num_speakers,
            on_progress=lambda f: cb(
                whisper_hi + (0.99 - whisper_hi) * f,
                f"Identificando hablantes… {f:.0%}",
            ),
        )
        segments = _assign_speakers(out["segments"], turns)
    else:
        segments = [
            Segment(s["start"], s["end"], s["text"].strip()) for s in out["segments"]
        ]
    cb(1.0, "Listo")
    return Result(out["language"], out["text"].strip(), segments)


# ---------- Exportación ----------

def _ts(t: float, sep: str) -> str:
    h, rem = divmod(int(t * 1000), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def _paragraphs(r: Result) -> list[Segment]:
    """Une segmentos consecutivos del mismo hablante en un párrafo."""
    out: list[Segment] = []
    for s in r.segments:
        if out and s.speaker is not None and s.speaker == out[-1].speaker:
            out[-1] = Segment(out[-1].start, s.end, f"{out[-1].text} {s.text}", s.speaker)
        else:
            out.append(Segment(s.start, s.end, s.text, s.speaker))
    return out


def _prefix(s: Segment, names: Names | None) -> str:
    label = speaker_label(s.speaker, names)
    return f"{label}: " if label else ""


def to_txt(r: Result, timestamps: bool = True, names: Names | None = None) -> str:
    has_spk = bool(r.speakers)
    if not timestamps and not has_spk:
        return r.text
    blocks = _paragraphs(r) if has_spk else r.segments
    sep = "\n\n" if has_spk else "\n"
    lines = []
    for s in blocks:
        ts = f"[{_ts(s.start, '.')[:-4]}] " if timestamps else ""
        lines.append(f"{ts}{_prefix(s, names)}{s.text}")
    return sep.join(lines)


def to_srt(r: Result, names: Names | None = None) -> str:
    return "\n".join(
        f"{i}\n{_ts(s.start, ',')} --> {_ts(s.end, ',')}\n{_prefix(s, names)}{s.text}\n"
        for i, s in enumerate(r.segments, 1)
    )


def to_vtt(r: Result, names: Names | None = None) -> str:
    body = "\n".join(
        f"{_ts(s.start, '.')} --> {_ts(s.end, '.')}\n{_prefix(s, names)}{s.text}\n"
        for s in r.segments
    )
    return "WEBVTT\n\n" + body


def to_json(r: Result, names: Names | None = None) -> str:
    segs = []
    for s in r.segments:
        d = asdict(s)
        if s.speaker is not None:
            d["speaker_name"] = speaker_label(s.speaker, names)
        segs.append(d)
    return json.dumps(
        {"language": r.language, "text": r.text, "segments": segs},
        ensure_ascii=False,
        indent=2,
    )


def to_docx(
    r: Result, dst: Path, timestamps: bool = True, names: Names | None = None
) -> Path:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(12)
    doc.add_heading("Transcripción", level=1)
    blocks = _paragraphs(r) if r.speakers else r.segments
    for s in blocks:
        p = doc.add_paragraph()
        if timestamps:
            p.add_run(f"[{_ts(s.start, '.')[:-4]}] ")
        label = speaker_label(s.speaker, names)
        if label:
            p.add_run(f"{label}: ").bold = True
        p.add_run(s.text)
    doc.save(dst)
    return dst


def first_lines(r: Result, max_chars: int = 80) -> dict[int, str]:
    """Primera intervención de cada hablante, para reconocerlo en la tabla."""
    out: dict[int, str] = {}
    for s in _paragraphs(r):
        if s.speaker is not None and s.speaker not in out:
            t = s.text
            out[s.speaker] = t if len(t) <= max_chars else t[: max_chars - 1] + "…"
    return out
