"""Explore sheet structure: project alpha coverage to find regions (interactive QC tool)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def bands(cov, thresh, min_frac):
    runs, start = [], None
    n = len(cov)
    for i, v in enumerate(cov):
        if v > thresh and start is None:
            start = i
        elif v <= thresh and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, n))
    return [r for r in runs if r[1] - r[0] >= max(2, int(n * min_frac))]


def main(path, downscale=4):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    sw, sh = w // downscale, h // downscale
    small = np.asarray(im.resize((sw, sh))).astype(np.uint8)
    alpha = small[:, :, 3] > 40
    colcov = alpha.mean(axis=0)
    rowcov = alpha.mean(axis=1)
    print(f"{path}: {w}x{h} (analysis {sw}x{sh})")
    print("col bands (orig px):", [(b[0] * downscale, b[1] * downscale) for b in bands(colcov, 0.02, 0.03)])
    print("row bands (orig px):", [(b[0] * downscale, b[1] * downscale) for b in bands(rowcov, 0.02, 0.03)])
    # fine: coverage values sampled
    print("rowcov profile:", " ".join(f"{v:.2f}" for v in rowcov[:: max(1, sh // 40)]))


if __name__ == "__main__":
    main(sys.argv[1])
