#!/usr/bin/env python3
"""Render a region of a PDF page or image to a PNG, for visual inspection.

Usage:
  render_page.py <input> --out <output.png> [--page N] [--bbox x0,y0,x1,y1] [--zoom Z]

<input> is a PDF or an image (PNG/JPG/etc).

--page selects a 1-indexed page (PDFs only; ignored for single images).

--bbox crops to a region given as FRACTIONS (0.0-1.0) of the page/image
width and height: x0,y0,x1,y1. Omit for the full page/image (an overview).

--zoom (default 1.0) is a multiplier on the source's native resolution.
Requesting more than the source actually has is capped at native
resolution — there is no fake upscaling. The output is also capped at
1568px on its longest edge regardless of --zoom, since that's roughly
the limit of what the vision model uses anyway.

Prints the output path and pixel dimensions on success, e.g.:
  wrote crop.png (1024x731px)
"""
import argparse
import sys
from pathlib import Path

import fitz  # pymupdf
from PIL import Image

MAX_DIM = 1568


def _native_scale(page, rect) -> float:
    """Pixels-per-point of the page's largest embedded image, if any."""
    best_width = 0
    for xref, *_ in page.get_images(full=True):
        try:
            base = page.parent.extract_image(xref)
        except Exception:
            continue
        best_width = max(best_width, base.get("width", 0))
    if best_width and rect.width:
        return best_width / rect.width
    return 1.0


def render_pdf(path, page_num, bbox, zoom, out_path):
    doc = fitz.open(path)
    page = doc[page_num - 1]
    rect = page.rect

    if bbox:
        x0, y0, x1, y1 = bbox
        clip = fitz.Rect(
            rect.x0 + x0 * rect.width, rect.y0 + y0 * rect.height,
            rect.x0 + x1 * rect.width, rect.y0 + y1 * rect.height,
        )
    else:
        clip = rect

    effective_zoom = min(zoom, _native_scale(page, rect))
    out_w, out_h = clip.width * effective_zoom, clip.height * effective_zoom
    longest = max(out_w, out_h)
    if longest > MAX_DIM:
        effective_zoom *= MAX_DIM / longest

    pix = page.get_pixmap(matrix=fitz.Matrix(effective_zoom, effective_zoom), clip=clip)
    pix.save(out_path)
    return pix.width, pix.height


def render_image(path, bbox, zoom, out_path):
    img = Image.open(path)
    w, h = img.size

    if bbox:
        x0, y0, x1, y1 = bbox
        crop = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    else:
        crop = img

    # Native resolution for an image is 1.0 — never upscale beyond it.
    effective_zoom = min(zoom, 1.0)
    if effective_zoom != 1.0:
        crop = crop.resize(
            (max(1, int(crop.width * effective_zoom)), max(1, int(crop.height * effective_zoom))),
            Image.LANCZOS,
        )

    longest = max(crop.width, crop.height)
    if longest > MAX_DIM:
        scale = MAX_DIM / longest
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)

    crop.convert("RGB").save(out_path)
    return crop.size


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--bbox", help="x0,y0,x1,y1 as fractions 0-1")
    parser.add_argument("--zoom", type=float, default=1.0)
    args = parser.parse_args()

    bbox = None
    if args.bbox:
        parts = [float(p) for p in args.bbox.split(",")]
        if len(parts) != 4:
            sys.exit("--bbox must be x0,y0,x1,y1")
        bbox = parts

    if Path(args.input).suffix.lower() == ".pdf":
        w, h = render_pdf(args.input, args.page, bbox, args.zoom, args.out)
    else:
        w, h = render_image(args.input, bbox, args.zoom, args.out)

    print(f"wrote {args.out} ({w}x{h}px)")


if __name__ == "__main__":
    main()
