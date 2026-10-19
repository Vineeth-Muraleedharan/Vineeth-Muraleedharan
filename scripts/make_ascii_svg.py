#!/usr/bin/env python3
"""
Convert the prepped grayscale photo into a self-typing monochrome ASCII SVG
(step 3b).

The prepped image is downsampled to a character grid, and each pixel's
brightness picks a glyph from a density ramp — sparse characters for
bright areas, dense ones for dark. Two choices keep it clean instead of
noisy: one light-gray monochrome fill (no per-character rainbow —
that's what makes most ASCII portraits look like static), and high
contrast so a busy background washes out to the space glyph and only
the subject prints.

Each row is wrapped in a clip that wipes left-to-right (a small block
"cursor" rides the wipe edge, via SMIL <animate> — GitHub runs SMIL
inside README SVGs even though it strips <script>), staggered top to
bottom. The whole portrait prints once and freezes; no looping.

Usage:
    python scripts/make_ascii_svg.py [source-prepped.png] [output.svg]
"""

import sys

from PIL import Image

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense); leading space clears bg

COLS = 100
CHAR_ASPECT = 0.52       # glyph width:height for the monospace font below
CHAR_W = 3.6             # px per column
CHAR_H = CHAR_W / CHAR_ASPECT
FONT_SIZE = CHAR_H * 0.92
PAD = 6

FILL = "#9aa4ad"          # single light-gray monochrome fill
CURSOR_FILL = "#22C55E"   # VINE emerald — accent cursor riding the wipe edge
FONT = "ui-monospace, SFMono-Regular, 'Cascadia Code', Menlo, Consolas, monospace"

ROW_STAGGER = 0.045       # extra seconds of delay per row
ROW_DUR = 0.16            # seconds each row takes to type in
START_DELAY = 0.1


def image_to_rows(path: str):
    img = Image.open(path).convert("L")
    w, h = img.size
    rows = max(1, round(COLS * (h / w) * CHAR_ASPECT))
    small = img.resize((COLS, rows), Image.LANCZOS)
    pixels = small.load()

    ramp_len = len(RAMP) - 1
    lines = []
    for y in range(rows):
        chars = []
        for x in range(COLS):
            brightness = pixels[x, y]  # 0 (black) .. 255 (white)
            idx = round((255 - brightness) / 255 * ramp_len)
            chars.append(RAMP[idx])
        lines.append("".join(chars))
    return lines


def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build(lines) -> str:
    n_rows = len(lines)
    width = PAD * 2 + COLS * CHAR_W
    height = PAD * 2 + n_rows * CHAR_H

    defs = []
    rows_svg = []
    for r, line in enumerate(lines):
        # Trim trailing spaces for the wipe width (space is invisible
        # anyway) but keep at least one char so empty rows don't break.
        trimmed = line.rstrip(" ") or " "
        row_w = len(trimmed) * CHAR_W
        y_baseline = PAD + (r + 1) * CHAR_H - CHAR_H * 0.22
        clip_y = PAD + r * CHAR_H
        clip_id = f"clip{r}"
        delay = START_DELAY + r * ROW_STAGGER

        defs.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="{PAD}" y="{clip_y:.2f}" width="0" height="{CHAR_H:.2f}">'
            f'<animate attributeName="width" from="0" to="{row_w:.2f}" '
            f'begin="{delay:.3f}s" dur="{ROW_DUR}s" fill="freeze" calcMode="linear"/>'
            f'</rect></clipPath>'
        )

        rows_svg.append(
            f'<text x="{PAD}" y="{y_baseline:.2f}" font-family="{FONT}" '
            f'font-size="{FONT_SIZE:.2f}" fill="{FILL}" xml:space="preserve" '
            f'clip-path="url(#{clip_id})">{esc(trimmed)}</text>'
        )

        # Small block cursor riding the reveal edge, then vanishing.
        cursor_y = clip_y + CHAR_H * 0.08
        cursor_h = CHAR_H * 0.78
        vanish = delay + ROW_DUR
        rows_svg.append(
            f'<rect x="{PAD}" y="{cursor_y:.2f}" width="{CHAR_W:.2f}" height="{cursor_h:.2f}" '
            f'fill="{CURSOR_FILL}">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + row_w:.2f}" '
            f'begin="{delay:.3f}s" dur="{ROW_DUR}s" fill="freeze" calcMode="linear"/>'
            f'<animate attributeName="opacity" from="1" to="0" '
            f'begin="{vanish:.3f}s" dur="0.08s" fill="freeze"/>'
            f'</rect>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
  <defs>
    {''.join(defs)}
  </defs>
  <rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="#0d1117"/>
  {''.join(rows_svg)}
</svg>
'''
    return svg


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "ascii-portrait.svg"
    lines = image_to_rows(input_path)
    svg = build(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {output_path} ({len(lines)} rows x {COLS} cols, {len(svg)} bytes)")


if __name__ == "__main__":
    main()
