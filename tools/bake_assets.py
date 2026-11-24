"""Phase 2 step A: consolidated final asset bake.

Everything with a verified constant lives here:
  - expression busts + overlays (blink, mouth closed/small/open, look L/R)
    padded onto ONE common canvas per character, anchored at the eye midpoint
    (face anchor literally cannot drift between expression swaps);
  - gesture figures scaled so their head width matches the bust head and padded
    onto the same canvas with head top/center aligned;
  - writes manifest.json (canvas size, file list, anchors) for the Godot side.

Inputs: art/staging (split + registered sprites). Output: godot/assets/characters.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

EXPRESSIONS = ["neutral", "happy", "surprised", "thinking", "worried"]

# eye midpoint in LOCAL bust coordinates (the 5 busts share internal geometry;
# measured on the neutral bust). NOT sheet coordinates - each bust cell has its own
# sheet origin, so sheet-propagated anchors would be wrong by the cell offset.
EYE_LOCAL = {
    "anna": (125, 117),
    "ben": (107, 120),
}
# single-eye anchors (local, on the neutral bust) + sprite width
EYES = {
    "anna": {"left": (100, 117, 52), "right": (150, 117, 52), "mirror_right": True,
             "look_left": "anna_eyes_09", "look_right": "anna_eyes_10"},
    "ben": {"left": (85, 120, 52), "right": (129, 120, 52), "mirror_left": True,
            "look_left": "ben_eyes_09", "look_right": "ben_eyes_11"},
}
MOUTH = {
    "anna": {"small": ("anna_mouths_02", 30), "open": ("anna_mouths_01", 42),
             "closed": ("anna_mouths_04", 52)},
    "ben": {"small": ("ben_mouths_00", 44), "open": ("ben_mouths_00", 50),
            "closed": ("ben_mouths_04", 78)},
}
MOUTH_PER_EXPR = {
    "anna": {"neutral": (130, 171), "happy": (140, 169), "surprised": (130, 171),
             "thinking": (137, 164), "worried": (130, 171)},
    "ben": {"neutral": (122, 181), "happy": (118, 174), "surprised": (138, 183),
            "thinking": (135, 176), "worried": (126, 174)},
}
ERASE_MASK = {
    "anna": {"neutral": (27, 12), "happy": (36, 15), "surprised": (22, 14),
             "thinking": (26, 11), "worried": (26, 11)},
    "ben": {"neutral": (36, 18), "happy": (44, 20), "surprised": (34, 20),
            "thinking": (34, 16), "worried": (32, 16)},
}
BLINK_SKIP = ("happy", "surprised")     # eyes already closed / wide
LOOK_SKIP = ("happy", "surprised")      # no open eyes to redirect

GESTURES = {
    # QC-verified usable set. Dropped: anna whoa (head-run misdetects raised palms ->
    # head jump), ben point/whoa (chair fragments + floating artifact). The pilot ticket
    # only needs wave/explain figures + nod/head_tilt transforms.
    "anna": {"wave": "anna_gestures_0_1", "explain": "anna_gestures_0_0",
             "point": "anna_gestures_0_2"},
    "ben": {"wave": "ben_gestures_0_1", "explain": "ben_conversation_0_1"},
}


def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA")).copy()


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


def feather_alpha(img, px=1.1):
    a = img[:, :, 3].astype(np.float32) / 255.0
    a = cv2.GaussianBlur(a, (0, 0), px)
    img[:, :, 3] = (a * 255).astype(np.uint8)
    return img


def erase_base_mouth(bust, cx, cy, hx, hy):
    h, w = bust.shape[:2]

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
    mask = np.zeros((h, w), np.float32)
    cv2.ellipse(mask, (int(cx), int(cy)), (int(hx), int(hy)), 0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 3.5)[..., None]
    region = (mask > 0.02) & (bust[:, :, 3:4] > 0)
    bust[:, :, :3] = np.where(region, np.round(fill * mask + bust[:, :, :3] * (1 - mask)).astype(np.uint8), bust[:, :, :3])
    return bust


def head_run(img, top_frac=0.35):
    """Largest contiguous opaque column-run in the top band -> head box estimate."""
    h, w = img.shape[:2]
    band = img[: int(h * top_frac), :, 3] > 60
    cov = band.mean(axis=0)
    runs, start = [], None
    for i, v in enumerate(cov):
        if v > 0.25 and start is None:
            start = i
        elif v <= 0.25 and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, w))
    if not runs:
        return None
    best = max(runs, key=lambda r: r[1] - r[0])
    x0, x1 = best
    ys = np.where(band[:, x0:x1].any(axis=1))[0]
    return (x0, x1, int(ys.min()) if len(ys) else 0)


def pad_to(arr, pad_left, pad_top, W, H):
    """Place arr into a WxH canvas with the given offsets; negative offsets crop."""
    out = np.zeros((H, W, 4), np.uint8)
    # source region after applying negative offsets
    sy0, sx0 = max(0, -pad_top), max(0, -pad_left)
    dy0, dx0 = max(0, pad_top), max(0, pad_left)
    h, w = arr.shape[:2]
    hh = min(h - sy0, H - dy0)
    ww = min(w - sx0, W - dx0)
    if hh > 0 and ww > 0:
        out[dy0:dy0 + hh, dx0:dx0 + ww] = arr[sy0:sy0 + hh, sx0:sx0 + ww]
    return out


def main(stage_dir, out_root):
    stage, out_root = Path(stage_dir), Path(out_root)
    rects = json.loads((stage / "split_index.json").read_text())
    for who in ("anna", "ben"):
        out = out_root / "characters" / who
        out.mkdir(parents=True, exist_ok=True)
        bust_rects = {b["name"]: b["rect"] for b in rects[who]["busts"]}

        # ---- compute common canvas + per-expression pads ----
        local_eye, pads, sizes = {}, {}, {}
        for expr in EXPRESSIONS:
            local_eye[expr] = EYE_LOCAL[who]
        EX = max(v[0] for v in local_eye.values())
        EY = max(v[1] for v in local_eye.values())
        for expr in EXPRESSIONS:
            base = load_rgba(stage / f"{who}_bust_{EXPRESSIONS.index(expr)}_{expr}.png")
            sizes[expr] = base.shape[:2]
            pads[expr] = (EX - local_eye[expr][0], EY - local_eye[expr][1])
        # gesture scaling onto the same canvas (head run = widest opaque run in the
        # top 25%; includes hair spread on both busts and gestures, so matching the
        # runs approximately matches the heads)
        neutral = load_rgba(stage / f"{who}_bust_0_neutral.png")
        nh = head_run(neutral, 0.25)
        gesture_data = {}
        for gname, gsrc in GESTURES[who].items():
            g = load_rgba(stage / f"{gsrc}.png")
            gh = head_run(g, 0.25)
            if gh is None or nh is None:
                continue
            scale = (nh[1] - nh[0]) / (gh[1] - gh[0])
            ng = cv2.resize(g, (int(round(g.shape[1] * scale)), int(round(g.shape[0] * scale))),
                            interpolation=cv2.INTER_AREA)
            ngh = head_run(ng, 0.25)
            gesture_data[gname] = (ng, ngh)
        # canvas extents: expression canvases and gestures, anchored head top y = EY - head_h/2... 
        # use: eye anchor EY; head top on neutral = nh[2] + pads['neutral'][1]
        head_top = nh[2] + pads["neutral"][1]
        W = H = 0
        for expr in EXPRESSIONS:
            W = max(W, pads[expr][0] + sizes[expr][1])
            H = max(H, pads[expr][1] + sizes[expr][0])
        for gname, (ng, ngh) in gesture_data.items():
            # pad so that gesture head center x == neutral head center x, head top y == head_top
            nhc = (nh[0] + nh[1]) // 2 + pads["neutral"][0]
            ghc = (ngh[0] + ngh[1]) // 2
            pl = nhc - ghc
            pt = head_top - ngh[2]
            gesture_data[gname] = (ng, (pl, pt))
            W = max(W, pl + ng.shape[1], 0)
            H = max(H, pt + ng.shape[0], 0)
        W, H = int(W), int(H)

        manifest = {"canvas": [W, H], "eye_anchor": [EX, EY],
                    "head_top": int(head_top), "files": []}

        # ---- bake expressions + overlays on the common canvas ----
        eye = EYES[who]
        lid = load_rgba(stage / f"{who}_eyes_02.png")
        for expr in EXPRESSIONS:
            base = load_rgba(stage / f"{who}_bust_{EXPRESSIONS.index(expr)}_{expr}.png")
            pl, pt = pads[expr]
            mx, my = MOUTH_PER_EXPR[who][expr]
            files = {"base": base}
            # noMouth (erase) + mouth overlays 0/1/2
            noM = erase_base_mouth(base.copy(), mx, my, *ERASE_MASK[who][expr])
            files["noMouth"] = noM
            for level, key in ((0, "closed"), (1, "small"), (2, "open")):
                spr, w = MOUTH[who][key]
                ov = np.zeros_like(base)
                paste_centered(ov, load_rgba(stage / f"{spr}.png"), mx, my, w)
                feather_alpha(ov)
                files[f"mouth{level}"] = ov
            if expr not in BLINK_SKIP:
                blink = np.zeros_like(base)
                paste_centered(blink, lid, *eye["left"], mirror=eye.get("mirror_left", False))
                paste_centered(blink, lid, *eye["right"], mirror=eye.get("mirror_right", False))
                files["blink"] = blink
            if expr not in LOOK_SKIP:
                for look in ("left", "right"):
                    spr = load_rgba(stage / f"{eye[f'look_{look}']}.png")
                    ov = np.zeros_like(base)
                    paste_centered(ov, spr, *eye["left"], mirror=(look == "right" and eye.get("mirror_right", False)))
                    paste_centered(ov, spr, *eye["right"], mirror=(look == "left" and eye.get("mirror_left", False)))
                    files[f"look{look}"] = ov
            for tag, arr in files.items():
                canvas = pad_to(arr, pl, pt, W, H)
                fname = f"expr_{expr}.png" if tag == "base" else f"expr_{expr}_{tag}.png"
                Image.fromarray(canvas).save(out / fname)
                manifest["files"].append(fname)

        # ---- gestures on the same canvas ----
        # gesture bodies fade out at the same visual line where busts fade, so the
        # bust -> gesture swap never reads as a framing/scale pop (and Ben's residual
        # table/chair fragments dissolve with the same fade)
        bust_bottom = 0
        for expr in EXPRESSIONS:
            base = load_rgba(stage / f"{who}_bust_{EXPRESSIONS.index(expr)}_{expr}.png")
            a = base[:, :, 3]
            ys, _ = np.where(a > 40)
            if len(ys):
                bust_bottom = max(bust_bottom, pads[expr][1] + int(ys.max()))
        manifest["gestures"] = {}
        for gname, (ng, (pl, pt)) in gesture_data.items():
            ng = ng.copy()
            h = ng.shape[0]
            fade_start = max(0, bust_bottom - 50 - pt)
            fade_end = min(h, bust_bottom + 10 - pt)
            if fade_end > fade_start:
                ramp = np.ones((h, 1), np.float32)
                n = fade_end - fade_start
                ramp[fade_start:fade_end, 0] = np.linspace(1.0, 0.0, n)
                ramp[fade_end:, 0] = 0.0
                ng[:, :, 3] = (ng[:, :, 3].astype(np.float32) * ramp).astype(np.uint8)
            canvas = pad_to(ng, max(0, pl), max(0, pt), W, H)
            Image.fromarray(canvas).save(out / f"gesture_{gname}.png")
            manifest["files"].append(f"gesture_{gname}.png")
            manifest["gestures"][gname] = f"gesture_{gname}.png"

        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"{who}: canvas {W}x{H} eye@({EX},{EY}) head_top={head_top} "
              f"{len(manifest['files'])} files, gestures={list(gesture_data)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
