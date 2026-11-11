# transcriptor

Transcriptor local de audio a texto en español e inglés, con Whisper. Funciona en **Mac (Apple Silicon)** y **Windows 11**. Privado: el audio nunca sale de tu equipo.

- Transcripción con marcas de tiempo y detección de idioma (español / inglés)
- Identificación de hablantes (*Hablante 1, 2, 3…*) con nombres editables
- Barra de progreso
- Exporta a TXT, DOCX, SRT, VTT y JSON

## Qué versión usar

| Equipo | Motor | Velocidad aproximada |
|---|---|---|
| Mac con chip M1, M2, M3, M4… | MLX (GPU de Apple) | Mucho más rápido que el tiempo real |
| Windows 11 con tarjeta NVIDIA | faster-whisper + CUDA | Mucho más rápido que el tiempo real |
| Windows 11 sin tarjeta NVIDIA | faster-whisper en CPU | Cerca del tiempo real con el modelo de máxima precisión*; más rápido con «Equilibrado» o «Rápido» |

\* Medido en un procesador de 8 núcleos; varía según el equipo.

La aplicación elige el motor sola. La primera transcripción descarga el modelo
(~1.6 GB con el modelo recomendado).

### Modelos

| Modelo | Tamaño | Cuándo usarlo |
|---|---|---|
| **Alta precisión** (large-v3-turbo) · recomendado | ~1.6 GB | Uso general |
| **Máxima precisión** (large-v3) | ~3 GB | Audio con ruido o acentos difíciles; tarda el doble |
| **Equilibrado** (medium) | ~1.5 GB | Equipos sin tarjeta gráfica |
| **Rápido** (small) | ~0.5 GB | Borradores rápidos |

Todos se ejecutan en el equipo; ninguno envía el audio a internet.

---

## Windows 11

### Requisitos
- Windows 11 de 64 bits (x64). Los equipos con procesador ARM (Snapdragon) no están soportados.
- [Python 3.12](https://www.python.org/downloads/windows/). Al instalarlo, marca **"Add python.exe to PATH"**.

No hace falta instalar ffmpeg.

### Instalación
1. Descarga el proyecto: botón verde **Code → Download ZIP** en GitHub, y descomprímelo.
   (O con git: `git clone https://github.com/eliascpa/transcriptor.git`)
2. Doble clic en **`instalar.bat`**. Tarda unos minutos.
3. *(Opcional, solo con tarjeta NVIDIA)* Doble clic en **`instalar-gpu.bat`** para usar la tarjeta gráfica.

### Uso
- **Abrir:** doble clic en **`iniciar.bat`**. Se abre el navegador en http://127.0.0.1:7860.
- **Cerrar:** cierra la ventana negra (consola).

Si Windows muestra *"Windows protegió su PC"* al abrir un `.bat`, pulsa
**Más información → Ejecutar de todas formas**.

---

## Mac (Apple Silicon)

### Requisitos
- Mac con chip M1 o superior, Python 3.10+
- [ffmpeg](https://ffmpeg.org/): `brew install ffmpeg`

### Instalación
```bash
git clone https://github.com/eliascpa/transcriptor.git
cd transcriptor
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Uso
```bash
.venv/bin/python app.py
```
Se abre el navegador en http://127.0.0.1:7860. Para cerrar, pulsa **Ctrl+C** en la Terminal.

---

## Cómo se usa

1. Sube un audio o video.
2. Elige el **idioma** (o «Automático») y el **modelo**.
3. Opcional: escribe en **Vocabulario** nombres propios o términos técnicos; mejora la precisión.
4. Pulsa **Transcribir**.

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
Los modelos (~32 MB) se descargan la primera vez a `~/.cache/transcriptor`
(en Windows: `C:\Users\<usuario>\.cache\transcriptor`).

### Desde Python

```python
import transcriptor as tr

r = tr.transcribe("audio.m4a")                       # detecta español/inglés
r = tr.transcribe("audio.m4a", "es", quality="rapido")
r = tr.transcribe("audio.m4a", prompt="Fernández, SUMAC, Hacienda")
r = tr.transcribe("audio.m4a", speakers=True, num_speakers=3)
print(tr.to_txt(r, names={1: "Lcda. Rivera", 2: "Sr. Gómez"}))
```

---

## Notas

- **Idioma:** con «Automático» se decide entre español e inglés. En clips muy cortos o con voces sintéticas puede equivocarse; si conoces el idioma, selecciónalo.
- **Hablantes:** voces muy parecidas (mismo sexo y tono) pueden confundirse; revisa la tabla antes de exportar.
- **GPU en Windows:** si la tarjeta NVIDIA falla al transcribir, la aplicación sigue sola con el procesador. Para forzar el procesador: `set TRANSCRIPTOR_DEVICE=cpu` antes de `iniciar.bat`.
- **Forzar motor** (pruebas): `TRANSCRIPTOR_MOTOR=faster` o `=mlx`.
- **Privacidad:** el `.gitignore` excluye audios, videos y transcripciones. No los subas al repositorio.

## Estructura

| Archivo | Función |
|---|---|
| `app.py` | Interfaz (Gradio) |
| `estilo.py` | Apariencia: paleta y diseño del Centro de herramientas |
| `transcriptor.py` | Núcleo: idioma, hablantes, exportación; elige el motor |
| `motor_mlx.py` | Motor Mac (MLX) |
| `motor_faster.py` | Motor Windows / Linux (faster-whisper, CUDA o CPU) |
| `diarizacion.py` | Separación de hablantes (sherpa-onnx) |
| `instalar.bat`, `instalar-gpu.bat`, `iniciar.bat` | Instalación y arranque en Windows |

## Licencia

MIT
