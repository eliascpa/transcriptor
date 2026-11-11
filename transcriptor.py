"""Núcleo de transcripción local para español e inglés, con separación
opcional de hablantes.

Motor según el equipo:
- Mac con Apple Silicon → MLX (motor_mlx.py)
- Windows / Linux / Mac Intel → faster-whisper (motor_faster.py)
Se puede forzar con TRANSCRIPTOR_MOTOR=mlx o =faster.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


def _pick_motor():
    forced = os.environ.get("TRANSCRIPTOR_MOTOR", "").lower()
    apple = sys.platform == "darwin" and platform.machine() == "arm64"
    if forced == "faster" or (not forced and not apple):
        import motor_faster as m
        return m
    try:
        import motor_mlx as m
    except ImportError:
        if forced == "mlx":
            raise
        import motor_faster as m
    return m


motor = _pick_motor()

LANGUAGES = {"Automático": None, "Español": "es", "Inglés": "en"}
QUALITIES = {
    "Máxima precisión (large-v3-turbo)": "preciso",
    "Equilibrado (medium)": "equilibrado",
    "Rápido (small)": "rapido",
}
DEFAULT_QUALITY = "preciso"
SAMPLE_RATE = 16000
WINDOW = 30 * SAMPLE_RATE  # 30 s, la ventana de Whisper

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


def detect_es_en(audio, model: str) -> str:
    """Decide entre 'es' y 'en' promediando hasta 3 ventanas de 30 s.

    Restringir la detección a los dos idiomas de interés evita errores de la
    autodetección general de Whisper (p. ej. confundir español con otro idioma).
    """
    last = max(len(audio) - WINDOW, 0)
    es = en = 0.0
    for st in sorted({0, last // 2, last}):
        probs = motor.language_probs(audio[st : st + WINDOW], model)
        es += probs.get("es", 0.0)
        en += probs.get("en", 0.0)
    return "es" if es >= en else "en"


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
    quality: str = DEFAULT_QUALITY,
    prompt: str | None = None,
    on_progress: ProgressFn | None = None,
    speakers: bool = False,
    num_speakers: int | None = None,
) -> Result:
    """Transcribe un archivo. language: 'es', 'en' o None (autodetectar).

    quality: 'preciso', 'equilibrado' o 'rapido' (tamaño del modelo).
    prompt: vocabulario/nombres propios para mejorar la precisión.
    on_progress: callback opcional (fracción 0..1, mensaje) para mostrar avance.
    speakers: separar hablantes (Hablante 1, 2, 3…).
    num_speakers: número de hablantes si se conoce (mejora la separación).
    """
    cb = on_progress or (lambda f, msg: None)
    model = motor.MODELS[quality]
    hi = 0.75 if speakers else 0.99

    cb(0.0, "Leyendo audio…")
    audio = motor.load_audio(str(path))
    cb(0.03, "Cargando modelo…")
    motor.load_model(model)  # descarga/carga una sola vez
    if language is None:
        cb(0.06, "Detectando idioma…")
        language = detect_es_en(audio, model)
    cb(0.10, "Transcribiendo…")
    out = motor.transcribe(
        audio,
        language,
        model,
        prompt,
        words=speakers,  # marcas por palabra: necesarias para cortar por hablante
        cb=lambda f: cb(0.10 + (hi - 0.10) * f, "Transcribiendo…"),
    )

    if speakers:
        import diarizacion

        cb(hi, "Identificando hablantes…")
        turns = diarizacion.diarize(
            audio,
            num_speakers,
            on_progress=lambda f: cb(
                hi + (0.99 - hi) * f, "Identificando hablantes…"
            ),
        )
        segments = _assign_speakers(out["segments"], turns)
    else:
        segments = [
            Segment(s["start"], s["end"], s["text"].strip()) for s in out["segments"]
        ]
    cb(1.0, "Listo")
    return Result(out["language"], out["text"], segments)


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
