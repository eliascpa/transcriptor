# transcriptor

Transcriptor local de audio a texto en español e inglés, con Whisper optimizado para Apple Silicon. Privado: el audio nunca sale de tu equipo.

## Requisitos

- Mac con Apple Silicon (M1 o superior)
- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg`)

## Instalación

```bash
git clone https://github.com/eliascpa/transcriptor.git
cd transcriptor
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

La primera transcripción descarga el modelo `whisper-large-v3-turbo` (~1.6 GB).

## Uso

Interfaz web local:

```bash
.venv/bin/python app.py
```

Abre http://127.0.0.1:7860, sube un audio o video, elige el idioma y transcribe.
Para cerrarla, pulsa Ctrl+C en la Terminal.

### Hablantes

Con **Identificar hablantes** activado, cada intervención se etiqueta como
*Hablante 1, Hablante 2…* (en orden de aparición). Al terminar aparece una
tabla con la primera intervención de cada uno para reconocerlo: escribe su
nombre en la columna **Nombre** y pulsa **Aplicar nombres**. El texto y todos
los archivos descargables se actualizan.

Si sabes cuántas personas hablan, indícalo en **Número de hablantes**: la
separación es más precisa que en modo automático.

La separación usa [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
(segmentación pyannote 3.0 + huellas de voz WeSpeaker), sin cuenta ni token.
Los modelos (~32 MB) se descargan la primera vez a `~/.cache/transcriptor`.

Desde Python:

```python
import transcriptor as tr

r = tr.transcribe("audio.m4a")              # detecta español/inglés
r = tr.transcribe("audio.m4a", "es")        # idioma forzado
r = tr.transcribe("audio.m4a", prompt="Fernández, SUMAC, Hacienda")  # vocabulario
r = tr.transcribe("audio.m4a", speakers=True, num_speakers=3)         # hablantes
print(tr.to_txt(r, names={1: "Lcda. Rivera", 2: "Sr. Gómez"}))
```

Formatos de salida: TXT (con o sin marcas de tiempo), SRT, VTT, JSON y DOCX.

## Notas

- **Idioma:** con "Automático" se decide entre español e inglés. En clips muy cortos o con voces sintéticas puede equivocarse; si conoces el idioma, selecciónalo.
- **Hablantes:** voces muy parecidas (mismo sexo y tono) pueden confundirse; revisa la tabla antes de exportar.
- **Vocabulario:** el campo de vocabulario (nombres propios, términos técnicos) mejora la precisión.
- **Privacidad:** el `.gitignore` excluye audios, videos y transcripciones. No los subas al repositorio.

## Licencia

MIT
