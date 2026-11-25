#!/usr/bin/env python3
"""Build labeled contact sheets from phase stills (one image to inspect many)."""
import glob
import os
import sys

from PIL import Image, ImageDraw

src_dir = sys.argv[1]
pattern = sys.argv[2]
out_path = sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 5
cell_w, cell_h = 320, 180

paths = sorted(glob.glob(os.path.join(src_dir, pattern)))
if not paths:
    sys.exit(f"no files match {pattern} in {src_dir}")

rows = (len(paths) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + 18)), (20, 20, 24))
draw = ImageDraw.Draw(sheet)
for i, p in enumerate(paths):
    img = Image.open(p).convert("RGB")
    img.thumbnail((cell_w, cell_h))
    x = (i % cols) * cell_w
    y = (i // cols) * (cell_h + 18)
    sheet.paste(img, (x + (cell_w - img.width) // 2, y + (cell_h - img.height) // 2))
    label = os.path.basename(p).replace(".png", "")
    draw.text((x + 4, y + cell_h + 2), label, fill=(230, 230, 230))
sheet.save(out_path)
print("saved", out_path, sheet.size, "cells:", len(paths))
