"""Apariencia de la interfaz, alineada con el Centro de herramientas
(https://eliascpa.dyndns.org/): misma paleta, aviso dorado, cabecera con
degradado azul y tarjetas blancas.

No se cargan fuentes ni recursos externos: la aplicación sigue 100% local.
"""

from __future__ import annotations

import html

import gradio as gr

# Paleta del sitio (variables :root)
INK = "#17243a"
MUTED = "#667085"
LINE = "#e4eaf2"
LINE_SUBTLE = "#edf2f7"
BLUE = "#1769e0"
BLUE_DARK = "#1056bb"
BLUE_SOFT = "#edf5ff"
GOLD = "#b7791f"
GOLD_SOFT = "#fffaf0"
PAGE_BG = "#f6f8fc"
SHADOW = "0 12px 35px rgba(28,48,88,.09)"
SHADOW_SM = "0 2px 5px rgba(16,24,40,.03)"
FONT_STACK = [
    "Inter", "ui-sans-serif", "system-ui", "-apple-system",
    "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif",
]

_blue = gr.themes.Color(
    c50=BLUE_SOFT, c100="#dbeafe", c200="#bad5fa", c300="#8fbaf5",
    c400="#5b98ee", c500=BLUE, c600=BLUE_DARK, c700="#0d4596",
    c800="#102b57", c900="#0b1f40", c950="#071429",
)

THEME = gr.themes.Base(
    primary_hue=_blue,
    secondary_hue=_blue,
    neutral_hue=gr.themes.colors.slate,
    font=FONT_STACK,
    font_mono=FONT_STACK,  # tablas y barra de progreso con la misma letra del sitio
    radius_size=gr.themes.sizes.radius_lg,
).set(
    body_background_fill=PAGE_BG,
    body_text_color=INK,
    body_text_color_subdued=MUTED,
    background_fill_primary="#ffffff",
    background_fill_secondary="#f8fafc",
    border_color_primary=LINE,
    border_color_accent=BLUE,
    color_accent=BLUE,
    color_accent_soft=BLUE_SOFT,
    block_background_fill="#ffffff",
    block_border_color=LINE,
    block_border_width="1px",
    block_radius="14px",
    block_shadow=SHADOW_SM,
    block_label_text_color=MUTED,
    block_label_text_weight="600",
    block_title_text_color=INK,
    block_title_text_weight="600",
    input_background_fill="#ffffff",
    input_border_width="1px",
    input_border_color=LINE,
    input_border_color_focus=BLUE,
    input_shadow_focus="0 0 0 4px rgba(23,105,224,.12)",
    input_radius="12px",
    checkbox_background_color_selected=BLUE,
    checkbox_border_color_selected=BLUE,
    checkbox_label_background_fill_selected=BLUE_SOFT,
    checkbox_label_border_color_selected="#bad5fa",
    checkbox_label_text_color_selected=BLUE_DARK,
    button_large_radius="12px",
    button_medium_radius="10px",
    button_primary_background_fill=BLUE,
    button_primary_background_fill_hover=BLUE_DARK,
    button_primary_text_color="#ffffff",
    button_primary_shadow="0 6px 16px rgba(23,105,224,.22)",
    button_secondary_background_fill=BLUE_SOFT,
    button_secondary_background_fill_hover="#dbeafe",
    button_secondary_text_color=BLUE_DARK,
    button_secondary_border_color="#bad5fa",
    loader_color=BLUE,
    slider_color=BLUE,
)

CSS = f"""
:root {{
    --tc-ink: {INK}; --tc-muted: {MUTED}; --tc-line: {LINE};
    --tc-line-subtle: {LINE_SUBTLE}; --tc-blue: {BLUE}; --tc-blue-dark: {BLUE_DARK};
    --tc-blue-soft: {BLUE_SOFT}; --tc-gold: {GOLD}; --tc-gold-soft: {GOLD_SOFT};
    --tc-shadow: {SHADOW}; --tc-shadow-sm: {SHADOW_SM};
}}
body, gradio-app {{ background: {PAGE_BG} !important; -webkit-font-smoothing: antialiased; }}

/* Contenedor (.shell) */
.gradio-container {{
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: 28px 24px 64px !important;
}}
footer {{ display: none !important; }}
/* Gradio añade 12 px de relleno a los bloques HTML: se quita para que el aviso,
   la cabecera y las tarjetas queden alineados como en el sitio */
.html-container:has(.tc-notice), .html-container:has(.tc-hero),
.html-container:has(.tc-card-head) {{ padding: 0 !important; }}

/* Aviso (.notice) */
.tc-notice {{
    margin: 0 0 4px;
    padding: 18px 22px;
    border-left: 5px solid var(--tc-gold);
    border-radius: 10px;
    color: #5b6474;
    background: var(--tc-gold-soft);
    font-size: clamp(0.92rem, 1.3vw, 1.05rem);
    line-height: 1.55;
    box-shadow: var(--tc-shadow-sm);
}}
.tc-notice strong {{ color: #4a3a16; }}

/* Cabecera (.hero) */
.tc-hero {{
    padding: 34px clamp(24px, 5vw, 52px);
    color: #ffffff;
    border-radius: 24px;
    background:
        radial-gradient(circle at 88% 12%, rgba(118,193,255,.35), transparent 30%),
        linear-gradient(120deg, #102b57, #1769e0);
    box-shadow: 0 18px 42px rgba(23,105,224,.22);
}}
.tc-hero .tc-eyebrow {{
    margin: 0 0 10px;
    color: #b9d9ff;
    font-size: .8rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
}}
.tc-hero h1 {{
    max-width: 720px;
    margin: 0;
    color: #ffffff;
    font-size: clamp(2rem, 4vw, 3.1rem);
    line-height: 1.1;
    letter-spacing: -.04em;
}}
.tc-hero .tc-copy {{
    max-width: 650px;
    margin: 12px 0 0;
    color: #e6f1ff;
    font-size: 1.05rem;
}}
.tc-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
.tc-chip {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 12px;
    border: 1px solid rgba(255,255,255,.28);
    border-radius: 99px;
    color: #ffffff;
    background: rgba(255,255,255,.12);
    font-size: .8rem;
    font-weight: 600;
}}

/* Tarjetas (.card) */
.tc-card {{
    padding: 22px !important;
    border: 1px solid var(--tc-line) !important;
    border-radius: 16px !important;
    background: #ffffff !important;
    box-shadow: var(--tc-shadow-sm);
    gap: 14px !important;
    transition: box-shadow .18s ease, border-color .18s ease;
}}
.tc-card:hover, .tc-card:focus-within {{
    border-color: #bad5fa !important;
    box-shadow: var(--tc-shadow);
}}
/* Dentro de una tarjeta, los grupos y bloques no repiten fondo, borde ni sombra */
.tc-card .form, .tc-card .gr-group, .tc-card .styler {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    gap: 14px !important;
}}
.tc-card .block:not(.tc-keep) {{
    border-color: transparent !important;
    box-shadow: none !important;
    background: #ffffff !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}}
.tc-card .tc-keep {{ border-color: var(--tc-line) !important; }}

.tc-card-head {{
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--tc-line-subtle);
}}
.tc-icon {{
    display: grid; place-items: center; flex-shrink: 0;
    width: 44px; height: 44px;
    border-radius: 12px;
    color: var(--tc-blue);
    background: var(--tc-blue-soft);
}}
.tc-icon svg {{ width: 22px; height: 22px; }}
.tc-card-head h3 {{
    margin: 0;
    color: var(--tc-ink);
    font-size: 1.06rem;
    line-height: 1.3;
    letter-spacing: -.015em;
}}
.tc-card-head p {{ margin: 2px 0 0; color: var(--tc-muted); font-size: .88rem; }}
.tc-step {{
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 20px; height: 20px; margin-right: 6px; padding: 0 6px;
    border-radius: 99px;
    color: var(--tc-blue); background: var(--tc-blue-soft);
    font-size: .74rem; font-weight: 700; vertical-align: 2px;
}}

/* Botón principal */
.tc-primary {{ font-weight: 700 !important; }}

@media (max-width: 768px) {{
    .gradio-container {{ padding: 16px 14px 48px !important; }}
    .tc-hero {{ padding: 26px 20px; border-radius: 18px; }}
}}
"""

# El sitio es solo de tema claro: fija ?__theme=light antes de que Gradio arranque.
HEAD = """
<script>
(function () {
  try {
    var u = new URL(window.location.href);
    if (!u.searchParams.get("__theme")) {
      u.searchParams.set("__theme", "light");
      window.history.replaceState(null, "", u.toString());
    }
  } catch (e) {}
})();
</script>
"""

_ICONS = {
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    "text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
}


def notice() -> str:
    return (
        '<aside class="tc-notice"><strong>Aviso:</strong> La transcripción es '
        "automática y puede contener errores; verifícala antes de usarla en "
        "documentos oficiales o escritos judiciales. El audio se procesa en "
        "este equipo y <strong>no se envía a internet</strong>.</aside>"
    )


def hero(motor: str) -> str:
    return (
        '<header class="tc-hero">'
        '<p class="tc-eyebrow">Fernández CPA &amp; Business Consultant, LLC &amp; Law Office</p>'
        "<h1>Transcriptor</h1>"
        '<p class="tc-copy">Transcripción de audio y video a texto en español e '
        "inglés, con identificación de hablantes y exportación a Word, subtítulos "
        "y texto.</p>"
        '<div class="tc-chips">'
        '<span class="tc-chip">🔒 100% local</span>'
        f'<span class="tc-chip">⚙️ {html.escape(motor)}</span>'
        '<span class="tc-chip">🇵🇷 Español · 🇺🇸 Inglés</span>'
        "</div></header>"
    )


def card_head(icon: str, step: int, title: str, subtitle: str) -> str:
    svg = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{_ICONS[icon]}</svg>'
    )
    return (
        f'<div class="tc-card-head"><span class="tc-icon" aria-hidden="true">{svg}</span>'
        f'<div><h3><span class="tc-step">{step}</span>{html.escape(title)}</h3>'
        f"<p>{html.escape(subtitle)}</p></div></div>"
    )
