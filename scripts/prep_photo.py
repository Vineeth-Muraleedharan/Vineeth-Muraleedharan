#!/usr/bin/env python3
"""
Prep a photo for ASCII conversion (step 3a).

A flatly-lit face converts to a dark, unreadable blob if you skip
straight to ASCII. Three steps fix that:

  1. Remove the background with rembg so the subject is isolated.
  2. Boost local contrast with OpenCV's CLAHE (contrast-limited
     adaptive histogram equalization) — this is what gives a flat
     face real highlights and shadows.
  3. Composite onto pure white so the background maps to the blank
     end of the ASCII ramp (white -> spaces).

Output is a grayscale source-prepped.png.

Usage:
    python scripts/prep_photo.py source-photo.jpg [output.png]
"""

import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

# u2net_human_seg is a ~176MB model purpose-built for people, instead of
# rembg's current default (bria-rmbg-2.0, a ~1GB general model that's
# overkill here and can OOM on a memory-constrained machine).
_SESSION = new_session("u2net_human_seg")


def prep(input_path: str, output_path: str = "source-prepped.png", max_dim: int = 900):
    with open(input_path, "rb") as f:
        input_bytes = f.read()

    # 1. Remove background -> RGBA with subject isolated.
    cutout_bytes = remove(input_bytes, session=_SESSION)
    cutout = Image.open(__import__("io").BytesIO(cutout_bytes)).convert("RGBA")

    # Downscale for speed/consistency before the pixel-level work below.
    if max(cutout.size) > max_dim:
        ratio = max_dim / max(cutout.size)
        cutout = cutout.resize(
            (int(cutout.width * ratio), int(cutout.height * ratio)), Image.LANCZOS
        )

    # 2. Composite onto pure white using the alpha mask, so the
    #    background maps to the blank end of the ASCII ramp.
    white_bg = Image.new("RGBA", cutout.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, cutout).convert("RGB")

    # 3. Boost local contrast with CLAHE on the grayscale version —
    #    this is what gives a flat, evenly-lit face real highlights
    #    and shadows instead of printing as a dark blob.
    gray = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contrasted = clahe.apply(gray)

    # Re-flatten any background noise CLAHE introduced back to white,
    # using the original cutout's alpha as the mask.
    alpha = np.array(cutout.split()[-1])
    alpha_resized = cv2.resize(alpha, (contrasted.shape[1], contrasted.shape[0]))
    background_mask = alpha_resized < 16
    contrasted[background_mask] = 255

    Image.fromarray(contrasted).save(output_path)
    print(f"wrote {output_path} ({contrasted.shape[1]}x{contrasted.shape[0]})")


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/prep_photo.py source-photo.jpg [output.png]")
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "source-prepped.png"
    prep(input_path, output_path)


if __name__ == "__main__":
    main()
