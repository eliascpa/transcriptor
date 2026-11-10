"""Interfaz web local (Gradio). Ejecutar: python app.py"""

from pathlib import Path
import tempfile

import gradio as gr

import transcriptor as tr

OUT_DIR = Path(tempfile.mkdtemp(prefix="transcriptor_"))
TABLE_HEADERS = ["Hablante", "Nombre", "Primera intervención"]


def _names_from_table(table) -> tr.Names:
    """Lee la tabla editable → {1: "Ana", 2: "Luis"}."""
    rows = table.values.tolist() if hasattr(table, "values") else (table or [])
    names: tr.Names = {}
    for row in rows:
        if not row or not str(row[0]).strip():
            continue
        try:
            spk = int(str(row[0]).split()[-1])  # "Hablante 2" → 2
        except ValueError:
            continue
        names[spk] = str(row[1] or "").strip()
    return names


def _render(res: tr.Result, stem: str, con_tiempos: bool, names: tr.Names):
    """Genera el texto en pantalla y los archivos descargables."""
    files = []
    for ext, content in (
        ("txt", tr.to_txt(res, con_tiempos, names)),
        ("srt", tr.to_srt(res, names)),
        ("vtt", tr.to_vtt(res, names)),
        ("json", tr.to_json(res, names)),
    ):
        p = OUT_DIR / f"{stem}.{ext}"
        p.write_text(content, encoding="utf-8")
        files.append(str(p))
    files.append(str(tr.to_docx(res, OUT_DIR / f"{stem}.docx", con_tiempos, names)))
    return tr.to_txt(res, con_tiempos, names), files


def run(audio, idioma, vocab, con_tiempos, hablantes, num_hablantes,
        progress=gr.Progress()):
    if audio is None:
        raise gr.Error("Sube un archivo de audio o video.")
    n = int(num_hablantes) if num_hablantes and num_hablantes > 0 else None
    res = tr.transcribe(
        audio,
        tr.LANGUAGES[idioma],
        prompt=vocab,
        on_progress=lambda f, msg: progress(f, desc=msg),
        speakers=hablantes,
        num_speakers=n,
    )
    progress(1.0, desc="Generando archivos…")
    stem = Path(audio).stem
    texto, files = _render(res, stem, con_tiempos, {})

    firsts = tr.first_lines(res)
    table = [[f"Hablante {s}", "", firsts.get(s, "")] for s in res.speakers]
    hay = bool(table)
    return (
        texto,
        res.language,
        files,
        {"res": res, "stem": stem},
        gr.update(value=table or None, visible=hay),
        gr.update(visible=hay),
    )


def aplicar_nombres(estado, tabla, con_tiempos):
    if not estado:
        raise gr.Error("Primero transcribe un audio.")
    names = _names_from_table(tabla)
    return _render(estado["res"], estado["stem"], con_tiempos, names)


with gr.Blocks(title="Transcriptor") as demo:
    gr.Markdown("# Transcriptor\nAudio a texto, 100% local (Whisper + MLX).")
    estado = gr.State(None)
    with gr.Row():
        with gr.Column():
            audio = gr.File(
                label="Audio o video",
                file_types=["audio", "video"],
                type="filepath",
            )
            idioma = gr.Radio(list(tr.LANGUAGES), value="Automático", label="Idioma")
            vocab = gr.Textbox(
                label="Vocabulario (opcional)",
                placeholder="Nombres propios, términos técnicos…",
            )
            with gr.Row():
                hablantes = gr.Checkbox(value=True, label="Identificar hablantes")
                num_hablantes = gr.Number(
                    value=0,
                    precision=0,
                    minimum=0,
                    maximum=20,
                    label="Número de hablantes (0 = automático)",
                )
            tiempos = gr.Checkbox(value=True, label="Incluir marcas de tiempo")
            btn = gr.Button("Transcribir", variant="primary")

            tabla = gr.Dataframe(
                headers=TABLE_HEADERS,
                datatype=["str", "str", "str"],
                interactive=True,
                static_columns=[0, 2],
                wrap=True,
                label="Nombres de los hablantes (escribe en la columna «Nombre»)",
                visible=False,
            )
            btn_nombres = gr.Button("Aplicar nombres", visible=False)
        with gr.Column():
            texto = gr.Textbox(label="Transcripción", lines=22, buttons=["copy"])
            detectado = gr.Textbox(label="Idioma detectado")
            descargas = gr.File(label="Descargas", file_count="multiple")

    btn.click(
        run,
        [audio, idioma, vocab, tiempos, hablantes, num_hablantes],
        [texto, detectado, descargas, estado, tabla, btn_nombres],
    )
    btn_nombres.click(aplicar_nombres, [estado, tabla, tiempos], [texto, descargas])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1")
