#!/usr/bin/env python3
"""
Generate info-card.svg — a neofetch-style panel that fades in line by line.

Design:
  - Dark terminal panel (GitHub-dark background) with a title bar
    (traffic-light dots) to read as a terminal window.
  - Rows of LABEL: value, where LABEL is a short all-caps key in the
    accent color and the value wraps onto as many lines as it needs.
  - Each line fades + slides up on a short stagger (CSS keyframes,
    plays once on load, then holds — no looping).
  - STATIC=1 env var emits a frozen final frame (no animation), used
    for local Quick Look previews.

Usage:
    python scripts/make_info_card.py            # animated
    STATIC=1 python scripts/make_info_card.py    # static frame
"""

import os
import textwrap

WIDTH = 490
PAD_X = 28
TITLEBAR_H = 40
ROW_GAP = 10          # gap between the label line and its first value line
LINE_H = 22           # line height within a wrapped value
SECTION_GAP = 22       # gap between one field and the next
FONT = "ui-monospace, SFMono-Regular, 'Cascadia Code', Menlo, Consolas, monospace"
WRAP_CHARS = 46

BG = "#0d1117"
BORDER = "#30363d"
TITLEBAR_BG = "#161b22"
DOT_RED = "#ff5f56"
DOT_YELLOW = "#ffbd2e"
DOT_GREEN = "#27c93f"

# VINE Ecosystem brand accents (locked): teal #14B8A6, emerald #22C55E,
# violet #A78BFA.
LABEL_COLOR = "#A78BFA"    # violet — field keys (NOW/PREV/STACK/HIGHLIGHTS)
VALUE_COLOR = "#c9d1d9"
MUTED = "#8b949e"
PROMPT_COLOR = "#14B8A6"   # teal — the "whoami" prompt line
CURSOR_COLOR = "#22C55E"   # emerald — blinking cursor

PROMPT_TEXT = "vineeth@github ~ $ whoami"
PROMPT_FONT_SIZE = 14
PROMPT_CHAR_W = PROMPT_FONT_SIZE * 0.6

FIELDS = [
    ("now", "Data Scientist & ML Engineer — building Clinical Intelligence"),
    ("prev", "Senior Radiation Therapist (RTT), 9+ yrs — Amrita Institute of Medical Sciences"),
    ("stack", "Python, scikit-learn, TensorFlow, FastAPI, SQL, Tableau/Power BI"),
    ("highlights", "CyberKnife / TomoTherapy / Linac clinical experience, RAG & LLM apps, Founder @ VINE Clinical Intelligence"),
]


def wrap(value, width=WRAP_CHARS):
    return textwrap.wrap(value, width=width) or [""]


def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build(static: bool) -> str:
    # Pre-compute every line (label line + wrapped value lines) with its
    # vertical position, so we know total height up front.
    lines = []  # list of (text, is_label, y)
    y = TITLEBAR_H + 34

    for label, value in FIELDS:
        lines.append((label.upper(), True, y))
        y += ROW_GAP + LINE_H
        for i, vline in enumerate(wrap(value)):
            lines.append((vline, False, y))
            y += LINE_H
        y += SECTION_GAP - LINE_H

    height = y + 8

    # --- animation / per-line styling -------------------------------------
    style_rules = []
    line_svgs = []
    for idx, (text, is_label, ypos) in enumerate(lines):
        cls = f"ln{idx}"
        color = LABEL_COLOR if is_label else VALUE_COLOR
        weight = "600" if is_label else "400"
        prefix = "" if is_label else ""
        if static:
            opacity_style = "opacity:1;"
        else:
            delay = 0.35 + idx * 0.09
            style_rules.append(
                f".{cls}{{opacity:0;animation:fadeInUp .45s ease-out {delay:.2f}s forwards;}}"
            )
            opacity_style = ""
        line_svgs.append(
            f'<text class="{cls}" x="{PAD_X}" y="{ypos}" '
            f'font-family="{FONT}" font-size="15" font-weight="{weight}" '
            f'fill="{color}" style="{opacity_style}">{esc(text)}</text>'
        )

    keyframes = (
        "@keyframes fadeInUp{"
        "0%{opacity:0;transform:translateY(6px);}"
        "100%{opacity:1;transform:translateY(0);}"
        "}"
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">
  <style>
    text {{ dominant-baseline: middle; }}
    {keyframes if not static else ""}
    {" ".join(style_rules)}
  </style>

  <rect x="0" y="0" width="{WIDTH}" height="{height}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>

  <!-- title bar -->
  <path d="M1,11 a9,9 0 0 1 9,-10 h{WIDTH - 20} a9,9 0 0 1 9,10 v{TITLEBAR_H - 11} h-{WIDTH - 2} z"
        fill="{TITLEBAR_BG}" transform="translate(0,0)"/>
  <rect x="1" y="1" width="{WIDTH - 2}" height="{TITLEBAR_H - 1}" rx="9" fill="{TITLEBAR_BG}"/>
  <rect x="1" y="{TITLEBAR_H / 2}" width="{WIDTH - 2}" height="{TITLEBAR_H / 2}" fill="{TITLEBAR_BG}"/>
  <circle cx="24" cy="{TITLEBAR_H/2}" r="6" fill="{DOT_RED}"/>
  <circle cx="44" cy="{TITLEBAR_H/2}" r="6" fill="{DOT_YELLOW}"/>
  <circle cx="64" cy="{TITLEBAR_H/2}" r="6" fill="{DOT_GREEN}"/>
  <text x="{WIDTH/2}" y="{TITLEBAR_H/2}" text-anchor="middle" font-family="{FONT}" font-size="13"
        fill="{MUTED}">neofetch</text>
  <line x1="0" y1="{TITLEBAR_H}" x2="{WIDTH}" y2="{TITLEBAR_H}" stroke="{BORDER}" stroke-width="1"/>

  <text x="{PAD_X}" y="{TITLEBAR_H + 20}" font-family="{FONT}" font-size="{PROMPT_FONT_SIZE}" fill="{PROMPT_COLOR}">{PROMPT_TEXT}</text>
  <rect x="{PAD_X + len(PROMPT_TEXT) * PROMPT_CHAR_W + 2:.2f}" y="{TITLEBAR_H + 20 - PROMPT_FONT_SIZE * 0.78:.2f}" width="{PROMPT_CHAR_W:.2f}" height="{PROMPT_FONT_SIZE:.2f}" fill="{CURSOR_COLOR}">
    <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.5;0.9;1" dur="1.1s" repeatCount="indefinite"/>
  </rect>

  {''.join(line_svgs)}
</svg>
'''
    return svg


def main():
    static = os.environ.get("STATIC") == "1"
    svg = build(static)
    # Run this script from the repo root: `python scripts/make_info_card.py`
    with open("info-card.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote info-card.svg ({len(svg)} bytes, static={static})")


if __name__ == "__main__":
    main()
