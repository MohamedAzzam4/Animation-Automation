"""Phase 1 step B: extract individual part sprites (eyes/mouths) from faces-sheet part rows.

Uses connected components on cleaned alpha; groups by size; emits a labeled atlas
so each sprite can be identified and named deterministically afterwards.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

FACES_LAYOUT = {
    "anna": {"busts": (16, 320), "eyes": (340, 856), "brows": (872, 1032), "mouths": (1092, 1352)},
    "ben": {"busts": (16, 332), "eyes": (336, 916), "brows": (936, 1080), "mouths": (1116, 1380)},
}


def clean(arr, lo=64, hi=235):
    a = arr[:, :, 3].astype(np.float32)
    arr[:, :, 3] = np.clip((a - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
    return arr


def components_in_row(arr, y0, y1, min_area=250, max_area=60000):
    """Find opaque blobs inside a row band; merge horizontally overlapping fragments."""
    band = arr[y0:y1]
    mask = band[:, :, 3] > 60
    # close small gaps inside sprites
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 9)))
    lab, n = ndimage.label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < min_area or len(ys) > max_area:
            continue
        out.append([int(xs.min()) , int(y0 + ys.min()), int(xs.max()) + 1, int(y0 + ys.max()) + 1, int(len(ys))])
    # merge boxes that overlap horizontally by > 55% of the narrower one and vertically too
    changed = True
    while changed:
        changed = False
        for a in range(len(out)):
            for b in range(a + 1, len(out)):
                A, B = out[a], out[b]
                ox = min(A[2], B[2]) - max(A[0], B[0])
                oy = min(A[3], B[3]) - max(A[1], B[1])
                if ox > 0.55 * min(A[2] - A[0], B[2] - B[0]) and oy > 0.4 * min(A[3] - B[1], B[3] - B[1]):
                    out[a] = [min(A[0], B[0]), min(A[1], B[1]), max(A[2], B[2]), max(A[3], B[3]), A[4] + B[4]]
                    out.pop(b)
                    changed = True
                    break
            if changed:
                break
    return sorted(out, key=lambda r: (r[1], r[0]))


def main(pack, out):
    pack, out = Path(pack), Path(out)
    stage = out / "staging"
    stage.mkdir(parents=True, exist_ok=True)
    index = {}
    for who in ("anna", "ben"):
        im = Image.open(pack / f"faces/{who}_face_expressions_visemes.png").convert("RGBA")
        arr = clean(np.asarray(im).copy())
        index[who] = {}
        for part in ("eyes", "mouths"):
            y0, y1 = FACES_LAYOUT[who][part]
            boxes = components_in_row(arr, y0, y1)
            index[who][part] = []
            for j, (x0, by0, x1, by1, area) in enumerate(boxes):
                name = f"{who}_{part}_{j:02d}"
                Image.fromarray(arr[by0:by1, x0:x1]).save(stage / f"{name}.png")
                index[who][part].append({"name": name, "rect": [x0, by0, x1, by1], "area": area})
        # labeled atlas
        items = index[who]["eyes"] + index[who]["mouths"]
        if not items:
            continue
        cw = max(x["rect"][2] - x["rect"][0] for x in items) + 20
        ch = max(x["rect"][3] - x["rect"][1] for x in items) + 26
        cols = 6
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * (ch + 22)), (110, 110, 116))
        d = ImageDraw.Draw(sheet)
        for k, it in enumerate(items):
            sprite = Image.open(stage / f"{it['name']}.png")
            x, y = (k % cols) * cw, (k // cols) * (ch + 22)
            bg = Image.new("RGBA", (cw - 8, ch - 8), (255, 255, 255, 255))
            for yy in range(0, bg.height, 16):
                for xx in range(0, bg.width, 16):
                    if (xx // 16 + yy // 16) % 2:
                        bg.paste(Image.new("RGBA", (16, 16), (186, 186, 192, 255)), (xx, yy))
            bg.alpha_composite(sprite, (4, 4))
            sheet.paste(bg.convert("RGB"), (x + 4, y + 18))
            d.text((x + 6, y + 2), it["name"], fill=(255, 255, 90))
        sheet.save(stage / f"{who}_parts_atlas.png")
    (stage / "parts_index.json").write_text(json.dumps(index, indent=2))
    for who in index:
        for part in index[who]:
            print(who, part, len(index[who][part]), "sprites")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
