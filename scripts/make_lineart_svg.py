#!/usr/bin/env python3
"""
Convert the prepped photo into a self-drawing line-art portrait SVG.

Unlike the ASCII pipeline (character density -> typing reveal), this
extracts actual contour lines from the photo (edge detection +
simplification) and animates each stroke being drawn in — the classic
"sketched by hand" effect — via stroke-dasharray/stroke-dashoffset
(SMIL <animate>, which GitHub plays fine inside README SVGs even
though it strips <script>). Major outlines draw first, finer detail
fills in after, then everything freezes. No looping.

Usage:
    python scripts/make_lineart_svg.py [source-prepped.png] [output.svg]
"""

import sys
import math

import cv2
import numpy as np

TARGET_MAX_DIM = 640      # working resolution for edge detection
MIN_CONTOUR_LEN = 26       # drop tiny noise contours (px, at working res) — higher = less fabric-texture noise
APPROX_EPSILON = 1.6       # cv2.approxPolyDP simplification strength
BLUR_KSIZE = 5
BILATERAL = True           # edge-preserving smoothing: kills fabric weave, keeps real edges crisp
CANNY_LO, CANNY_HI = 50, 140

STROKE_COLOR = "#14B8A6"   # VINE teal
BG_COLOR = "#0d1117"
STROKE_WIDTH = 1.6

DRAW_SPEED = 2600.0        # px of path per second (bigger contours take longer)
MIN_DUR = 0.12
STAGGER_BASE = 0.025       # extra delay per contour index, on top of draw time


def load_and_edges(path: str):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"could not read {path}")
    h, w = img.shape
    scale = TARGET_MAX_DIM / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    if BILATERAL:
        # Edge-preserving smoothing: flattens fine texture (fabric weave,
        # skin pores) while keeping real structural edges sharp — plain
        # Gaussian blur softens both equally, which is what let fabric
        # noise through as little zigzag contours.
        smoothed = cv2.bilateralFilter(img, d=9, sigmaColor=60, sigmaSpace=60)
    else:
        smoothed = cv2.GaussianBlur(img, (BLUR_KSIZE, BLUR_KSIZE), 0)
    edges = cv2.Canny(smoothed, CANNY_LO, CANNY_HI)
    # Close small gaps so contours trace continuous lines.
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    return edges, img.shape[1], img.shape[0]


def extract_paths(edges):
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    paths = []
    for c in contours:
        length = cv2.arcLength(c, False)
        if length < MIN_CONTOUR_LEN:
            continue
        approx = cv2.approxPolyDP(c, APPROX_EPSILON, False)
        pts = approx.reshape(-1, 2)
        if len(pts) < 2:
            continue
        paths.append((pts, length))
    # Largest/major contours first, fine detail after.
    paths.sort(key=lambda p: -p[1])
    return paths


def path_d(pts) -> str:
    d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f} "
    d += " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts[1:])
    return d


def build(paths, width, height) -> str:
    pad = 12
    vb_w, vb_h = width + pad * 2, height + pad * 2

    defs_style = []
    path_svgs = []
    t = 0.15  # running start-time cursor across the stagger
    for i, (pts, length) in enumerate(paths):
        dur = max(MIN_DUR, length / DRAW_SPEED)
        delay = t
        t += STAGGER_BASE
        cls = f"p{i}"
        d = path_d(pts)
        defs_style.append(
            f".{cls}{{stroke-dasharray:{length:.1f};stroke-dashoffset:{length:.1f};"
            f"animation:draw{i} {dur:.2f}s linear {delay:.2f}s forwards;}}"
            f"@keyframes draw{i}{{to{{stroke-dashoffset:0;}}}}"
        )
        path_svgs.append(
            f'<path class="{cls}" d="{d}" fill="none" stroke="{STROKE_COLOR}" '
            f'stroke-width="{STROKE_WIDTH}" stroke-linecap="round" stroke-linejoin="round" '
            f'transform="translate({pad},{pad})"/>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w}" height="{vb_h}" viewBox="0 0 {vb_w} {vb_h}">
  <style>
    {" ".join(defs_style)}
  </style>
  <rect x="0" y="0" width="{vb_w}" height="{vb_h}" fill="{BG_COLOR}"/>
  {''.join(path_svgs)}
</svg>
'''
    return svg


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "portrait.svg"
    edges, w, h = load_and_edges(input_path)
    paths = extract_paths(edges)
    svg = build(paths, w, h)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    total_dur = 0.15 + len(paths) * STAGGER_BASE + (max((l for _, l in paths), default=0) / DRAW_SPEED)
    print(f"wrote {output_path}: {len(paths)} contours, ~{total_dur:.1f}s total draw time, {len(svg)} bytes")


if __name__ == "__main__":
    main()
