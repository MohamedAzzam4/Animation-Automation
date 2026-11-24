"""Phase 1 step C (FINAL): bake aligned overlays with VLM-verified fixed anchors/scales.

All numbers below were determined by an auditable process (see reports/phase_01.md):
  - feature midpoints: 10x10 grid VLM estimate -> decisive dot test -> 5x5 alignment
    mosaics at 3x zoom (crosshair-on-feature)
  - per-eye centers: alignment mosaics per eye
  - overlay scales: candidate sheet, VLM-picked natural-looking widths
Anchors are FIXED per character (identical across the 5 expressions) so the face anchor
is steady by construction while swapping eyes/mouth.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SELECT = {
    "anna": {"eyes_closed": "anna_eyes_02", "mouth_small": "anna_mouths_02",
             "mouth_open": "anna_mouths_01"},
    "ben": {"eyes_closed": "ben_eyes_02", "mouth_small": "ben_mouths_00",
            "mouth_open": "ben_mouths_00"},
}
EXPRESSIONS = ["neutral", "happy", "surprised", "thinking", "worried"]

# left eye, right eye (center + sprite width), mouth (center + widths for small/open)
# mouth widths chosen from speech-mouth candidate sheet (VLM): neutral speech, not grin.
# Ben's mouth anchor varies per expression (head turn/tilt shifts the mouth; measured
# via zoomed lower-face crops + alignment mosaics - see reports/phase_01.md).
# per-expression mouth anchors (measured: neutral via mosaic; thinking/happy/surprised
# via zoomed lower-face crops; see reports/phase_01.md for the full audit trail)
MOUTH_PER_EXPR = {
    "anna": {"neutral": (130, 171), "happy": (140, 169), "surprised": (130, 171),
             "thinking": (137, 164), "worried": (130, 171)},
    "ben": {"neutral": (122, 181), "happy": (118, 174), "surprised": (138, 183),
            "thinking": (135, 176), "worried": (126, 174)},
}
# base-mouth erase masks (half-extents, px) so the base smile/O does not show through
# the overlay on expressions whose base mouth is open/large (VLM QC: double-mouth bug)
ERASE_MASK = {
    "anna": {"neutral": (27, 12), "happy": (36, 15), "surprised": (22, 14),
             "thinking": (26, 11), "worried": (26, 11)},
    "ben": {"neutral": (36, 18), "happy": (44, 20), "surprised": (34, 20),
            "thinking": (34, 16), "worried": (32, 16)},
}
ANCHORS = {
    "anna": {"left_eye": (100, 117, 52), "right_eye": (150, 117, 52),
             "mirror_right": True,
             "mouth": (130, 171, 30, 42)},
    "ben": {"left_eye": (85, 120, 52), "right_eye": (129, 120, 52),
            "mirror_left": True,
            "mouth": (118, 182, 44, 50)},
}


def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA")).copy()


def erase_base_mouth(bust, cx, cy, hx, hy):
    """Cover the painted mouth with a feathered patch sampled from the surrounding
    skin/beard tones (left/right of the mouth), replacing OpenCV inpaint which left
    visible smudges in QC."""
    h, w = bust.shape[:2]
    # sample columns just outside the erase ellipse on both sides (close band, bright
    # percentile: avoids contour shadow tones that caused a bruise-like halo on Anna)
    def sample(side):
        xs = range(max(0, int(cx + side * (hx + 2))), min(w, int(cx + side * (hx + 13))))
        cols = []
        for x in xs:
            for y in range(max(0, int(cy - hy // 2)), min(h, int(cy + hy // 2))):
                if bust[y, x, 3] > 200:
                    cols.append(bust[y, x, :3].astype(np.float32))
        if not cols:
            return np.array([210.0, 170.0, 150.0])
        arr = np.array(cols)
        lum = arr.mean(axis=1)
        pick = arr[lum >= np.percentile(lum, 55)]
        return pick.mean(axis=0)
    left, right = sample(-1), sample(1)
    yy, xx = np.mgrid[0:h, 0:w]
    t = np.clip((xx - (cx - hx)) / (2 * hx), 0, 1)[..., None]
    fill = (left * (1 - t) + right * t).astype(np.uint8)
    # feathered mask
    mask = np.zeros((h, w), np.float32)
    cv2.ellipse(mask, (int(cx), int(cy)), (int(hx), int(hy)), 0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 3.5)[..., None]
    region = (mask > 0.02) & (bust[:, :, 3:4] > 0)
    bust[:, :, :3] = np.where(region, np.round(fill * mask + bust[:, :, :3] * (1 - mask)).astype(np.uint8), bust[:, :, :3])
    return bust


def feather_alpha(img, px=1.2):
    a = img[:, :, 3].astype(np.float32) / 255.0
    a = cv2.GaussianBlur(a, (0, 0), px)
    img[:, :, 3] = (a * 255).astype(np.uint8)
    return img


def paste_centered(canvas, sprite, cx, cy, target_w, mirror=False):
    if mirror:
        sprite = sprite[:, ::-1].copy()
    s = target_w / sprite.shape[1]
    tw, th = int(round(sprite.shape[1] * s)), int(round(sprite.shape[0] * s))
    t = cv2.resize(sprite, (tw, th), interpolation=cv2.INTER_AREA)
    x0, y0 = int(round(cx - tw / 2)), int(round(cy - th / 2))
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(canvas.shape[1], x0 + tw), min(canvas.shape[0], y0 + th)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    sub = t[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    dst = canvas[cy0:cy1, cx0:cx1]
    a = (sub[:, :, 3:4].astype(np.float32)) / 255.0
    blended = sub[:, :, :3].astype(np.float32) * a + dst[:, :, :3].astype(np.float32) * (1 - a)
    canvas[cy0:cy1, cx0:cx1, :3] = blended.astype(np.uint8)
    canvas[cy0:cy1, cx0:cx1, 3] = np.maximum(dst[:, :, 3], sub[:, :, 3])


def main(stage_dir):
    stage = Path(stage_dir)
    report = {"method": "fixed VLM-verified anchors (mosaic alignment + scale candidates)",
              "anchors": ANCHORS, "files": {}}
    for who in ("anna", "ben"):
        sel, an = SELECT[who], ANCHORS[who]
        lid = load_rgba(stage / f"{sel['eyes_closed']}.png")
        m_small = load_rgba(stage / f"{sel['mouth_small']}.png")
        m_open = load_rgba(stage / f"{sel['mouth_open']}.png")
        lx, ly, lw = an["left_eye"]
        rx, ry, rw = an["right_eye"]
        mx, my, w_small, w_open = an["mouth"]
        report["files"][who] = []
        for expr in EXPRESSIONS:
            bust = load_rgba(stage / f"{who}_bust_{EXPRESSIONS.index(expr)}_{expr}.png")
            emx, emy = MOUTH_PER_EXPR[who][expr]
            Image.fromarray(bust).save(stage / f"{who}_expr_{expr}.png")
            report["files"][who].append(f"{who}_expr_{expr}.png")
            if expr not in ("happy", "surprised"):  # eyes already closed/wide in these
                blink = np.zeros_like(bust)
                paste_centered(blink, lid, lx, ly, lw, mirror=an.get("mirror_left", False))
                paste_centered(blink, lid, rx, ry, rw, mirror=an.get("mirror_right", False))
                Image.fromarray(blink).save(stage / f"{who}_expr_{expr}_blink.png")
                report["files"][who].append(f"{who}_expr_{expr}_blink.png")
            for level, key, w in ((1, "mouth_small", w_small), (2, "mouth_open", w_open)):
                ov = np.zeros_like(bust)
                paste_centered(ov, m_open if level == 2 else m_small, emx, emy, w)
                feather_alpha(ov, 1.1)
                Image.fromarray(ov).save(stage / f"{who}_expr_{expr}_mouth{level}.png")
                report["files"][who].append(f"{who}_expr_{expr}_mouth{level}.png")
            # mouth-erased base variant for compositing in Godot: base with painted mouth
            # inpainted away, so overlay mouths never stack on the painted one
            erased = erase_base_mouth(bust.copy(), emx, emy, *ERASE_MASK[who][expr])
            Image.fromarray(erased).save(stage / f"{who}_expr_{expr}_noMouth.png")
            report["files"][who].append(f"{who}_expr_{expr}_noMouth.png")

        # QC composite: what Godot will actually show.
        # cols: base | blink | noMouth+mouth-small | noMouth+mouth-open
        tiles = []
        for expr in EXPRESSIONS:
            base = Image.fromarray(load_rgba(stage / f"{who}_expr_{expr}.png"))
            erased = Image.fromarray(load_rgba(stage / f"{who}_expr_{expr}_noMouth.png"))
            variants = [base]
            p = stage / f"{who}_expr_{expr}_blink.png"
            if p.is_file():
                v = base.copy()
                v.alpha_composite(Image.open(p))
                variants.append(v)
            else:
                variants.append(base)  # n/a column
            for level in (1, 2):
                v = erased.copy()
                v.alpha_composite(Image.open(stage / f"{who}_expr_{expr}_mouth{level}.png"))
                variants.append(v)
            tiles.append(variants)
        cw = tiles[0][0].width + 8
        chh = tiles[0][0].height + 8
        sheet = Image.new("RGB", (cw * 4, chh * 5 + 24), (235, 235, 240))
        from PIL import ImageDraw
        d = ImageDraw.Draw(sheet)
        d.text((6, 4), f"{who}: rows=neutral,happy,surprised,thinking,worried; cols=base,blink,mouth-small,mouth-open", fill=(0, 0, 0))
        for r, variants in enumerate(tiles):
            for c, v in enumerate(variants):
                tile = Image.new("RGBA", v.size, (255, 255, 255, 255))
                tile.alpha_composite(v)
                sheet.paste(tile.convert("RGB"), (c * cw + 4, r * chh + 24))
        sheet.save(stage / f"{who}_overlays_qc.png")

    (stage / "anchors.json").write_text(json.dumps(report, indent=2))
    print("baked overlays:", json.dumps(ANCHORS))


if __name__ == "__main__":
    main(sys.argv[1])
