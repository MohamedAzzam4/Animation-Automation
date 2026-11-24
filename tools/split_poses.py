"""Phase 1 step D: extract gesture/conversation figures from poses sheets.

Splits each sheet into a grid via alpha row/col coverage (with valley-splitting for
merged cells), cleans alpha, tight-crops, and writes a labeled atlas for VLM QC.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SHEETS = {
    # sheet -> (character, cols, rows, col_thresh, row_thresh) from coverage profiles + VLM
    "anna_gestures": ("anna", 3, 2, 0.15, 0.02),
    "ben_gestures": ("ben", 2, 3, 0.15, 0.02),
    "anna_conversation": ("anna", 2, 3, 0.15, 0.02),
    "ben_conversation": ("ben", 3, 2, 0.15, 0.02),
}


def clean_alpha(arr, lo=64, hi=235):
    a = arr[:, :, 3].astype(np.float32)
    arr[:, :, 3] = np.clip((a - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
    return arr


def bands(cov, thresh, n):
    runs, start = [], None
    for i, v in enumerate(cov):
        if v > thresh and start is None:
            start = i
        elif v <= thresh and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, n))
    return [r for r in runs if r[1] - r[0] >= max(3, int(n * 0.06))]


def split_grid(alpha, cols, rows_n, col_thresh=0.15, row_thresh=0.02):
    h, w = alpha.shape
    rowcov = alpha.mean(axis=1)
    colcov = alpha.mean(axis=0)
    rb = bands(rowcov, row_thresh, h)
    cb = bands(colcov, col_thresh, w)
    def fit(bs, want):
        if len(bs) == want:
            return bs
        if len(bs) > want:
            while len(bs) > want:
                gaps = [(bs[i + 1][0] - bs[i][1], i) for i in range(len(bs) - 1)]
                g, i = min(gaps)
                bs = bs[:i] + [(bs[i][0], bs[i + 1][1])] + bs[i + 2:]
            return bs
        # fewer than wanted: valley-split the widest band at its deepest partial valley
        while len(bs) < want:
            widths = [(b[1] - b[0], i) for i, b in enumerate(bs)]
            wi, i = max(widths)
            b = bs[i]
            seg = colcov if want == cols else rowcov
            smooth = np.convolve(seg[b[0]:b[1]], np.ones(15) / 15, mode="same")
            cut = 30 + int(np.argmin(smooth[30:-30]))
            bs = bs[:i] + [(b[0], b[0] + cut), (b[0] + cut, b[1])] + bs[i + 1:]
        return bs
    return fit(cb, cols), fit(rb, rows_n)


def main(pack, stage):
    pack, stage = Path(pack), Path(stage)
    index = {}
    for sheet, (who, cols, rows_n, ct, rt) in SHEETS.items():
        im = Image.open(pack / f"poses/{sheet}.png").convert("RGBA")
        arr = clean_alpha(np.asarray(im).copy())
        alpha = arr[:, :, 3] > 40
        cb, rb = split_grid(alpha, cols, rows_n, ct, rt)
        cells = []
        for ri, (y0, y1) in enumerate(rb):
            for ci, (x0, x1) in enumerate(cb):
                sub = alpha[y0:y1, x0:x1]
                ys, xs = np.where(sub)
                if len(ys) < 400:
                    continue
                cells.append({"name": f"{sheet}_{ri}_{ci}",
                              "rect": [int(x0 + xs.min()), int(y0 + ys.min()),
                                       int(x0 + xs.max()) + 1, int(y0 + ys.max()) + 1]})
        index[sheet] = cells
        for c in cells:
            x0, y0, x1, y1 = c["rect"]
            Image.fromarray(arr[y0:y1, x0:x1]).save(stage / f"{c['name']}.png")
        # atlas
        tiles = [(c, Image.open(stage / f"{c['name']}.png")) for c in cells]
        tw = max(t.height for _, t in tiles)  # portrait-ish
        cw = max(t.width for _, t in tiles) + 16
        chh = tw + 40
        ncols = min(6, len(tiles))
        nrows = (len(tiles) + ncols - 1) // ncols
        atlas = Image.new("RGB", (ncols * cw, nrows * chh + 20), (120, 120, 126))
        d = ImageDraw.Draw(atlas)
        d.text((6, 3), sheet, fill=(255, 255, 90))
        for k, (c, t) in enumerate(tiles):
            x, y = (k % ncols) * cw, (k // ncols) * chh + 20
            bg = Image.new("RGBA", (t.width + 8, t.height + 8), (255, 255, 255, 255))
            for yy in range(0, bg.height, 14):
                for xx in range(0, bg.width, 14):
                    if (xx // 14 + yy // 14) % 2:
                        bg.paste(Image.new("RGBA", (14, 14), (185, 185, 190, 255)), (xx, yy))
            bg.alpha_composite(t, (4, 4))
            atlas.paste(bg.convert("RGB"), (x + 4, y))
            d.text((x + 6, y + chh - 18), c["name"], fill=(255, 255, 90))
        atlas.save(stage / f"{sheet}_atlas.jpg", quality=90)
        print(sheet, "->", len(cells), "cells", [c["name"] for c in cells])
    (stage / "poses_index.json").write_text(json.dumps(index, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
