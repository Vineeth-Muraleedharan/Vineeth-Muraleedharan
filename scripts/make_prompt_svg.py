#!/usr/bin/env python3
"""
Generate a small "terminal prompt" SVG pill — standing in for the plain
<h3><code>...</code></h3> headers GitHub can't animate (README markdown
strips <style>/<script>, so any motion has to live inside an embedded
SVG instead). Each pill shows "<prefix><command>" with a blinking
block cursor at the end, in VINE's emerald accent.

Usage:
    python scripts/make_prompt_svg.py "vineeth@github ~ $ " "./contributions.sh" prompt-contributions.svg
    python scripts/make_prompt_svg.py "vineeth@github ~ $ " "whoami" prompt-whoami.svg
"""

import sys

FONT = "ui-monospace, SFMono-Regular, 'Cascadia Code', Menlo, Consolas, monospace"
FONT_SIZE = 15
CHAR_W = FONT_SIZE * 0.6
PAD_X = 14
PAD_Y = 9

PILL_BG = "#2d333b"       # GitHub dark-mode inline-<code> background
PREFIX_COLOR = "#8b949e"  # muted gray — "user@host ~ $ "
COMMAND_COLOR = "#14B8A6"  # VINE teal — the command itself
CURSOR_COLOR = "#22C55E"  # VINE emerald — blinking cursor


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(prefix: str, command: str) -> str:
    text_w = (len(prefix) + len(command)) * CHAR_W
    cursor_w = CHAR_W
    width = PAD_X * 2 + text_w + cursor_w + 4
    height = PAD_Y * 2 + FONT_SIZE * 1.3
    baseline = height / 2 + FONT_SIZE * 0.32

    prefix_x = PAD_X
    command_x = PAD_X + len(prefix) * CHAR_W
    cursor_x = command_x + len(command) * CHAR_W + 2
    cursor_y = height / 2 - FONT_SIZE * 0.62

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
  <rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" rx="{height/2:.0f}" fill="{PILL_BG}"/>
  <text x="{prefix_x:.1f}" y="{baseline:.1f}" font-family="{FONT}" font-size="{FONT_SIZE}" fill="{PREFIX_COLOR}">{esc(prefix)}</text>
  <text x="{command_x:.1f}" y="{baseline:.1f}" font-family="{FONT}" font-size="{FONT_SIZE}" font-weight="600" fill="{COMMAND_COLOR}">{esc(command)}</text>
  <rect x="{cursor_x:.1f}" y="{cursor_y:.1f}" width="{cursor_w:.1f}" height="{FONT_SIZE * 1.15:.1f}" fill="{CURSOR_COLOR}">
    <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.5;0.9;1" dur="1.1s" repeatCount="indefinite"/>
  </rect>
</svg>
'''
    return svg


def main():
    if len(sys.argv) < 4:
        print('usage: python scripts/make_prompt_svg.py "<prefix>" "<command>" <output.svg>')
        sys.exit(1)
    prefix, command, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    svg = build(prefix, command)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {output_path} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
