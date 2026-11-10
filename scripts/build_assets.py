#!/usr/bin/env python3
"""Genera los SVG del README (assets/*.svg) con la paleta del portfolio.

GitHub no carga tipografias dentro de un SVG usado como imagen, asi que el
texto se convierte a trazos con IBM Plex Mono (SIL Open Font License).

Uso (no hay pip en el VPS, corre en Docker desde la raiz del repo):
  docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/repo -w /repo \
    python:3.12-slim sh -c \
    "pip install -q --user fonttools brotli && python scripts/build_assets.py"
"""
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
OUT_DIR = ROOT / "assets"

WIDTH = 840
PAD = 32
META_SIZE = 12.5
META_TRACKING = 0.08

# Mismos valores que src/app/tokens.css del portfolio. El verde senal cambia
# de hex entre temas a proposito (contraste), no unificar.
THEMES = {
    "light": {
        "ink-1": "#0B0D10",
        "ink-3": "#57606A",
        "signal": "#166534",
        "rule": "#787F88",
        "rule-hair": "#D5D9DD",
        "background": "#F6F7F8",
    },
    "dark": {
        "ink-1": "#E6E8EB",
        "ink-3": "#8B949E",
        "signal": "#4ADE80",
        "rule": "#5A636D",
        "rule-hair": "#2A3038",
        "background": "#0B0D10",
    },
}

SECTIONS = [
    ("proyectos", "Qué", "construí"),
    ("stack", "Con qué", "trabajo"),
    ("contacto", "Hablemos", "de lo que necesitás"),
]


class Face:
    def __init__(self, weight):
        self.font = TTFont(FONTS_DIR / f"ibm-plex-mono-latin-{weight}-normal.woff2")
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def text(self, value, x, y, size, fill, tracking=0.0, anchor="start"):
        """Devuelve (path, ancho en px) del texto con la linea de base en y."""
        pen = SVGPathPen(self.glyphs)
        cursor = 0.0
        gap = tracking * self.upm
        for char in value:
            glyph = self.glyphs[self.cmap[ord(char)]]
            glyph.draw(TransformPen(pen, (1, 0, 0, 1, cursor, 0)))
            cursor += glyph.width + gap
        scale = size / self.upm
        width = (cursor - gap) * scale
        if anchor == "middle":
            x -= width / 2
        path = (
            f'<path fill="{fill}" transform="translate({x:.2f} {y:.2f}) '
            f'scale({scale:.5f} {-scale:.5f})" d="{pen.getCommands()}"/>'
        )
        return path, width


REGULAR = Face(400)
MEDIUM = Face(500)
SEMIBOLD = Face(600)


def svg(height, title, body, style=""):
    style_tag = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" '
        f'width="{WIDTH}" height="{height}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{style_tag}{''.join(body)}</svg>\n"
    )


def prompt(colors, label, x, y, body):
    """El `$ ruta` del PanelHeader del portfolio. Devuelve la x donde termina."""
    dollar, dollar_width = REGULAR.text("$", x, y, 13, colors["signal"])
    path, label_width = SEMIBOLD.text(label, x + dollar_width + 8, y, 13, colors["ink-3"])
    body += [dollar, path]
    return x + dollar_width + 8 + label_width


def build_hero(colors):
    height = 236
    body = [
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="4" '
        f'fill="{colors["background"]}" stroke="{colors["rule-hair"]}"/>'
    ]

    prompt_end = prompt(colors, "~", PAD, 31, body)
    body.append(
        f'<rect class="cursor" x="{prompt_end + 3:.2f}" y="19.5" width="7" height="14" '
        f'fill="{colors["ink-3"]}"/>'
    )
    body.append(f'<path d="M1 48.5H{WIDTH - 1}" stroke="{colors["rule"]}"/>')

    name, _ = SEMIBOLD.text("Lautaro Pereira", PAD, 116, 44, colors["ink-1"], tracking=-0.01)
    role, _ = SEMIBOLD.text(
        "DESARROLLADOR DE SOFTWARE  ·  SAN MIGUEL, AR",
        PAD, 146, META_SIZE, colors["ink-3"], tracking=META_TRACKING,
    )
    body += [name, role]
    body.append(f'<path d="M{PAD} 174.5H{WIDTH - PAD}" stroke="{colors["rule-hair"]}"/>')

    baseline = 208
    body.append(
        f'<rect class="ping" x="{PAD}" y="{baseline - 9}" width="6" height="6" fill="{colors["signal"]}"/>'
        f'<rect x="{PAD}" y="{baseline - 9}" width="6" height="6" fill="{colors["signal"]}"/>'
    )
    available, available_width = SEMIBOLD.text(
        "DISPONIBLE", PAD + 16, baseline, META_SIZE, colors["ink-3"], tracking=META_TRACKING
    )
    years_x = PAD + 16 + available_width + 32
    years, years_width = MEDIUM.text("2+", years_x, baseline, 20, colors["ink-1"])
    experience, _ = SEMIBOLD.text(
        "AÑOS DE EXPERIENCIA", years_x + years_width + 8, baseline,
        META_SIZE, colors["ink-3"], tracking=META_TRACKING,
    )
    body += [available, years, experience]

    style = (
        ".cursor{animation:blink 1.1s steps(1) infinite}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 1.6s cubic-bezier(0,0,.2,1) infinite}"
        "@keyframes blink{50%{opacity:0}}"
        "@keyframes ping{0%{opacity:.4}75%,100%{transform:scale(2.4);opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.cursor,.ping{animation:none}.ping{opacity:0}}"
    )
    title = "Lautaro Pereira. Desarrollador de software, San Miguel, AR. Disponible."
    return svg(height, title, body, style)


def build_section(colors, label, strong, soft):
    # Sin marco ni sangria: se alinea con el texto del README que va debajo.
    height = 100
    body = []
    prompt(colors, label, 0, 18, body)
    body.append(f'<path d="M0 34.5H{WIDTH}" stroke="{colors["rule"]}"/>')
    strong_path, strong_width = SEMIBOLD.text(strong, 0, 78, 28, colors["ink-1"], tracking=-0.01)
    soft_path, _ = SEMIBOLD.text(soft, strong_width + 17, 78, 28, colors["ink-3"], tracking=-0.01)
    body += [strong_path, soft_path]
    body.append(f'<path d="M0 97.5H112" stroke="{colors["rule"]}"/>')
    return svg(height, f"{strong} {soft}", body)


def build_footer(colors):
    height = 44
    label = "LAUTARO PEREIRA  ·  SAN MIGUEL, BUENOS AIRES"
    body = [f'<path d="M0 0.5H{WIDTH}" stroke="{colors["rule"]}"/>']
    path, _ = REGULAR.text(
        label, WIDTH / 2, 29, META_SIZE, colors["ink-3"], tracking=META_TRACKING, anchor="middle"
    )
    body.append(path)
    return svg(height, "Lautaro Pereira. San Miguel, Buenos Aires.", body)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for theme, colors in THEMES.items():
        files = {"hero": build_hero(colors), "footer": build_footer(colors)}
        for label, strong, soft in SECTIONS:
            files[f"section-{label}"] = build_section(colors, label, strong, soft)
        for name, content in files.items():
            target = OUT_DIR / f"{name}-{theme}.svg"
            target.write_text(content, encoding="utf-8")
            print(f"{target.relative_to(ROOT)}  {len(content) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
