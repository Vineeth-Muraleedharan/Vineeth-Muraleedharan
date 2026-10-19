#!/usr/bin/env python3
"""
Render data/contributions.json as an animated contribution heatmap SVG —
the classic 53-week x 7-day grid of rounded, colored boxes, revealed once
with a diagonal slide-down on load (then frozen — no looping "glow"),
plus a Less->More legend and a stats footer.

Usage:
    python scripts/render_heatmap_svg.py
"""

import json
import datetime

CELL = 11
GAP = 3
STEP = CELL + GAP
WEEKDAY_LABEL_W = 28
LEFT_PAD = 8
RIGHT_PAD = 16
TOP_PAD = 8
MONTH_LABEL_H = 20
GRID_H = 7 * STEP - GAP
LEGEND_H = 24
STATS_H = 30
BOTTOM_PAD = 12

BG = "#0d1117"
BORDER = "#30363d"
TEXT_MUTED = "#8b949e"
TEXT_STRONG = "#c9d1d9"
FONT = "ui-monospace, SFMono-Regular, 'Cascadia Code', Menlo, Consolas, monospace"

# VINE Ecosystem brand accents (locked): teal #14B8A6, emerald #22C55E,
# violet #A78BFA. none -> level1..4 ramps from dark teal up to emerald;
# index 5 (violet) is reserved for the single best day, not a regular bucket.
PALETTE = ["#161b22", "#0d3b36", "#116659", "#14B8A6", "#22C55E", "#A78BFA"]

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def load_data(path="data/contributions.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_weeks(days):
    """Group days into weeks (Sunday-start columns), padding the first
    week with Nones so day-of-week rows line up."""
    if not days:
        return []
    parsed = [
        {**d, "_date": datetime.date.fromisoformat(d["date"])} for d in days
    ]
    first = parsed[0]["_date"]
    pad = (first.weekday() + 1) % 7  # Python Monday=0..Sunday=6 -> Sunday-start pad
    weeks = []
    current = [None] * pad
    for d in parsed:
        current.append(d)
        if len(current) == 7:
            weeks.append(current)
            current = []
    if current:
        current += [None] * (7 - len(current))
        weeks.append(current)
    return weeks


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_date(iso):
    d = datetime.date.fromisoformat(iso)
    day = d.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{MONTH_NAMES[d.month - 1]} {day}{suffix}, {d.year}"


def build(data: dict) -> str:
    days = data.get("days", [])
    weeks = build_weeks(days)
    n_weeks = len(weeks)
    best_day = (data.get("stats") or {}).get("best_day")
    best_date = best_day["date"] if best_day else None

    grid_w = n_weeks * STEP - GAP
    width = WEEKDAY_LABEL_W + LEFT_PAD + grid_w + RIGHT_PAD
    height = TOP_PAD + MONTH_LABEL_H + GRID_H + LEGEND_H + STATS_H + BOTTOM_PAD

    origin_x = WEEKDAY_LABEL_W + LEFT_PAD
    origin_y = TOP_PAD + MONTH_LABEL_H

    # --- month labels (only when the month changes vs. the previous column) ---
    month_labels = []
    last_month = None
    for wi, week in enumerate(weeks):
        first_real = next((d for d in week if d is not None), None)
        if first_real is None:
            continue
        m = first_real["_date"].month
        if m != last_month:
            x = origin_x + wi * STEP
            month_labels.append(
                f'<text x="{x}" y="{TOP_PAD + 14}" font-family="{FONT}" '
                f'font-size="11" fill="{TEXT_MUTED}">{MONTH_NAMES[m - 1]}</text>'
            )
            last_month = m

    # --- weekday labels (Mon / Wed / Fri, GitHub-style) ---
    weekday_labels = []
    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = origin_y + row * STEP + CELL - 2
        weekday_labels.append(
            f'<text x="0" y="{y}" font-family="{FONT}" font-size="10" '
            f'fill="{TEXT_MUTED}">{label}</text>'
        )

    # --- the cells themselves, staggered diagonally by (week + day) ---
    style_rules = []
    cell_svgs = []
    max_delay_unit = n_weeks + 6
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            if day is None:
                continue
            x = origin_x + wi * STEP
            y = origin_y + di * STEP
            level = day.get("level", 0)
            color = PALETTE[level] if 0 <= level < 5 else PALETTE[4]
            if best_date and day["date"] == best_date and day.get("count", 0) > 0:
                color = PALETTE[5]
            title = f'{day.get("count", 0)} contributions on {fmt_date(day["date"])}'
            cls = f"c{wi}_{di}"
            delay = 0.15 + (wi + di) * (0.9 / max_delay_unit)
            style_rules.append(
                f".{cls}{{opacity:0;transform:translateY(-6px);"
                f"animation:dropIn .35s ease-out {delay:.3f}s forwards;}}"
            )
            cell_svgs.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" ry="2" fill="{color}"><title>{esc(title)}</title></rect>'
            )

    # --- legend ---
    legend_y = origin_y + GRID_H + 20
    legend_x = origin_x + grid_w - (5 * 14 + 70)
    legend_svgs = [
        f'<text x="{legend_x - 34}" y="{legend_y + 8}" font-family="{FONT}" '
        f'font-size="10" fill="{TEXT_MUTED}">Less</text>'
    ]
    for i, color in enumerate(PALETTE[:5]):
        lx = legend_x + i * 14
        legend_svgs.append(
            f'<rect x="{lx}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{color}"/>'
        )
    legend_svgs.append(
        f'<text x="{legend_x + 5 * 14 + 6}" y="{legend_y + 8}" font-family="{FONT}" '
        f'font-size="10" fill="{TEXT_MUTED}">More</text>'
    )

    # --- stats footer ---
    stats = data.get("stats", {})
    total = data.get("total_contributions", sum(d.get("count", 0) for d in days))
    streak = stats.get("current_streak", 0)
    longest = stats.get("longest_streak", 0)
    stats_y = legend_y + STATS_H
    stats_text = (
        f"{total:,} contributions in the last year"
        f"  ·  current streak {streak}d  ·  longest streak {longest}d"
    )
    stats_svg = (
        f'<text x="{origin_x}" y="{stats_y}" font-family="{FONT}" font-size="12" '
        f'fill="{TEXT_STRONG}">{esc(stats_text)}</text>'
    )

    keyframes = (
        "@keyframes dropIn{0%{opacity:0;transform:translateY(-6px);}"
        "100%{opacity:1;transform:translateY(0);}}"
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    {keyframes}
    {" ".join(style_rules)}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="10" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  {''.join(month_labels)}
  {''.join(weekday_labels)}
  {''.join(cell_svgs)}
  {''.join(legend_svgs)}
  {stats_svg}
</svg>
'''
    return svg


def main():
    data = load_data()
    svg = build(data)
    with open("contrib-heatmap.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote contrib-heatmap.svg ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
