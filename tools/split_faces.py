"""Phase 1 step A: split the expression-bust row and parts rows from faces sheets.

Deterministic rectangle extraction driven by alpha coverage projections.
Outputs cropped cells to a staging dir for VLM/visual verification.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# y-ranges determined by row-band analysis + VLM verification (see reports/phase_01.md)
FACES_LAYOUT = {
    "anna": {"busts": (16, 320), "eyes": (340, 856), "brows": (872, 1032), "mouths": (1092, 1352)},
    "ben": {"busts": (16, 332), "eyes": (336, 916), "brows": (936, 1080), "mouths": (1116, 1380)},
}


def col_bands(alpha, thresh=0.02, min_frac=0.03):
    cov = alpha.mean(axis=0)
    runs, start, n = [], None, len(cov)
    for i, v in enumerate(cov):
        if v > thresh and start is None:
            start = i
        elif v <= thresh and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, n))
    runs = [r for r in runs if r[1] - r[0] >= max(2, int(n * min_frac))]
    if not runs:
        return runs
    # split over-wide merged cells at the deepest coverage valley
    widths = [r[1] - r[0] for r in runs]
    med = float(np.median(widths))
    out = []
    for r in runs:
        if (r[1] - r[0]) > 1.6 * med:
            smooth = np.convolve(cov[r[0]:r[1]], np.ones(15) / 15, mode="same")
            cut = 40 + int(np.argmin(smooth[40:-40]))
            # only accept a real valley
            if smooth[cut] < 0.35:
                out.extend([(r[0], r[0] + cut), (r[0] + cut, r[1])])
                continue
        out.append(r)
    return out


def clean_alpha(arr, lo=64, hi=235):
    """Remap alpha to kill faint debris while preserving anti-aliasing ramp."""
    a = arr[:, :, 3].astype(np.float32)
    a = np.clip((a - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
    arr[:, :, 3] = a
    return arr


def main(pack, out):
    pack, out = Path(pack), Path(out)
    (out / "staging").mkdir(parents=True, exist_ok=True)
    index = {}
    for who in ("anna", "ben"):
        im = Image.open(pack / f"faces/{who}_face_expressions_visemes.png").convert("RGBA")
        W, H = im.size
        arr = np.asarray(im).copy()
        alpha = arr[:, :, 3] > 40
        layout = FACES_LAYOUT[who]

        # --- busts row ---
        y0, y1 = layout["busts"]
        band = alpha[y0:y1]
        cells = []
        for cx0, cx1 in col_bands(band, 0.02, 0.02):
            sub = alpha[y0:y1, cx0:cx1]
            rs = np.where(sub.any(axis=1))[0]
            cs = np.where(sub.any(axis=0))[0]
            if len(rs) == 0:
                continue
            cells.append((cx0 + cs[0], y0 + rs[0], cx0 + cs[-1] + 1, y0 + rs[-1] + 1))
        # keep the 5 largest cells by area (drop tiny debris)
        cells = sorted(cells, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)[:5]
        cells.sort(key=lambda r: r[0])
        names = ["neutral", "happy", "surprised", "thinking", "worried"]
        index[who] = {"busts": []}
        for i, (x0, y0b, x1, y1b) in enumerate(cells):
            cell = arr[y0b:y1b, x0:x1].copy()
            cell = clean_alpha(cell)
            Image.fromarray(cell, "RGBA").save(out / "staging" / f"{who}_bust_{i}_{names[i]}.png")
            index[who]["busts"].append({"name": names[i], "rect": [int(x0), int(y0b), int(x1), int(y1b)]})

        # --- parts rows: dump whole rows as one image each for interactive splitting ---
        for part in ("eyes", "brows", "mouths"):
            ry0, ry1 = layout[part]
            Image.fromarray(arr[ry0:ry1]).save(out / "staging" / f"{who}_row_{part}.png")

    (out / "staging" / "split_index.json").write_text(json.dumps(index, indent=2))
    print(json.dumps(index, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
