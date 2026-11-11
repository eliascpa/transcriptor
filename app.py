"""Interfaz web local (Gradio). Ejecutar: python app.py"""

from pathlib import Path
import tempfile

import gradio as gr

import estilo
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


def run(audio, idioma, calidad, vocab, con_tiempos, hablantes, num_hablantes,
        progress=gr.Progress()):
    if audio is None:
        raise gr.Error("Sube un archivo de audio o video.")
    n = int(num_hablantes) if num_hablantes and num_hablantes > 0 else None
    res = tr.transcribe(
        audio,
        tr.LANGUAGES[idioma],
        quality=tr.QUALITIES[calidad],
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
    idioma_txt = {"es": "Español", "en": "Inglés"}.get(res.language, res.language)
    return (
        texto,
        idioma_txt,
        files,
        {"res": res, "stem": stem},
        table or None,
        gr.update(visible=bool(table)),
    )


def aplicar_nombres(estado, tabla, con_tiempos):
    if not estado:
        raise gr.Error("Primero transcribe un audio.")
    names = _names_from_table(tabla)
    return _render(estado["res"], estado["stem"], con_tiempos, names)


with gr.Blocks(title="Transcriptor | Fernández CPA & Law") as demo:
    estado = gr.State(None)

    gr.HTML(estilo.notice(), padding=False, container=False)
    gr.HTML(estilo.hero(tr.motor.describe()), padding=False, container=False)

    with gr.Row(equal_height=False):
        # --- Tarjeta 1: audio y opciones ---
        with gr.Column(scale=5, elem_classes="tc-card"):
            gr.HTML(
                estilo.card_head("upload", 1, "Audio y opciones",
                                 "Sube el archivo y ajusta la transcripción."),
                padding=False,
            )
            audio = gr.File(
                label="Audio o video",
                file_types=["audio", "video"],
                type="filepath",
                elem_classes="tc-keep",
            )
            idioma = gr.Radio(list(tr.LANGUAGES), value="Automático", label="Idioma")
            calidad = gr.Dropdown(
                list(tr.QUALITIES),
                value=next(k for k, v in tr.QUALITIES.items() if v == tr.DEFAULT_QUALITY),
                label="Modelo",
                info="En equipos sin tarjeta gráfica, «Equilibrado» o «Rápido» tardan menos.",
            )
            vocab = gr.Textbox(
                label="Vocabulario (opcional)",
                placeholder="Nombres propios, términos técnicos…",
            )
            with gr.Row():
                hablantes = gr.Checkbox(value=True, label="Identificar hablantes")
                tiempos = gr.Checkbox(value=True, label="Incluir marcas de tiempo")
            num_hablantes = gr.Number(
                value=0,
                precision=0,
                minimum=0,
                maximum=20,
                label="Número de hablantes (0 = automático)",
            )
            btn = gr.Button("Transcribir", variant="primary", size="lg",
                            elem_classes="tc-primary")

        # --- Tarjeta 2: resultado ---
        with gr.Column(scale=7, elem_classes="tc-card"):
            gr.HTML(
                estilo.card_head("text", 2, "Transcripción",
                                 "Revisa el texto y descarga los archivos."),
                padding=False,
            )
            texto = gr.Textbox(label="Texto", lines=20, buttons=["copy"])
            with gr.Row():
                detectado = gr.Textbox(label="Idioma detectado", scale=1)
            descargas = gr.File(
                label="Descargas (TXT · SRT · VTT · JSON · DOCX)",
                file_count="multiple",
                elem_classes="tc-keep",
            )

    # --- Tarjeta 3: nombres de los hablantes (aparece al terminar) ---
    with gr.Column(visible=False, elem_classes="tc-card") as panel_nombres:
        gr.HTML(
            estilo.card_head("users", 3, "Nombres de los hablantes",
                             "Escribe el nombre de cada persona en la columna «Nombre» "
                             "y pulsa «Aplicar nombres»."),
            padding=False,
        )
        tabla = gr.Dataframe(
            headers=TABLE_HEADERS,
            datatype=["str", "str", "str"],
            interactive=True,
            static_columns=[0, 2],
            column_widths=["16%", "30%", "54%"],
            wrap=True,
            show_label=False,
            elem_classes="tc-keep",
        )
        btn_nombres = gr.Button("Aplicar nombres", variant="primary",
                                elem_classes="tc-primary")

    btn.click(
        run,
        [audio, idioma, calidad, vocab, tiempos, hablantes, num_hablantes],
        [texto, detectado, descargas, estado, tabla, panel_nombres],
        show_progress_on=[texto],  # una sola barra, sobre el texto
    )
    btn_nombres.click(aplicar_nombres, [estado, tabla, tiempos], [texto, descargas])

# Apariencia (en Gradio 6 el tema y el CSS se pasan a launch)
LAUNCH_STYLE = dict(theme=estilo.THEME, css=estilo.CSS, head=estilo.HEAD)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", inbrowser=True, **LAUNCH_STYLE)
