"""Phase 1 step E: promote staged assets to final deterministic names under
godot/assets/characters/{anna,ben}/ + backgrounds + font. Writes assets_manifest.json.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

GESTURES = {
    "anna": {
        "gesture_wave": "anna_gestures_0_1",
        "gesture_explain": "anna_gestures_0_0",
        "gesture_point": "anna_gestures_0_2",
        "gesture_whoa": "anna_gestures_1_2",
        "gesture_thinking": "anna_gestures_1_1",
    },
    "ben": {
        # fade-treated gesture cells (furniture removed; see phase_01 report)
        "gesture_wave": "ben_gestures_0_1_fade",
        # explain only used in table scenes (cafe/room): seated explain w/ table fits
        "gesture_explain": "ben_conversation_0_1",
        "gesture_point": "ben_gestures_1_0_fade",
        "gesture_whoa": "ben_gestures_2_1_fade",
        "gesture_thinking": "ben_gestures_2_0_fade",
    },
}
EXPRESSIONS = ["neutral", "happy", "surprised", "thinking", "worried"]


def fade_treat(src, dst):
    import numpy as np
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).copy()
    h, w = a.shape[:2]
    a = a[: int(h * 0.90)]
    h2 = a.shape[0]
    fade = np.ones((h2, 1), np.float32)
    fade[-70:] = np.linspace(1, 0, 70)[:, None]
    a[:, :, 3] = (a[:, :, 3].astype(np.float32) * fade).astype(np.uint8)
    Image.fromarray(a).save(dst)


def main(stage_dir, godot_assets, pack):
    stage = Path(stage_dir)
    assets = Path(godot_assets)
    pack = Path(pack)
    manifest = {"generator": "art/extract_characters pipeline", "files": {}}

    for who in ("anna", "ben"):
        out = assets / "characters" / who
        out.mkdir(parents=True, exist_ok=True)
        for expr in EXPRESSIONS:
            pairs = [(f"{who}_expr_{expr}.png", f"expr_{expr}.png"),
                     (f"{who}_expr_{expr}_noMouth.png", f"expr_{expr}_noMouth.png"),
                     (f"{who}_expr_{expr}_mouth1.png", f"expr_{expr}_mouth1.png"),
                     (f"{who}_expr_{expr}_mouth2.png", f"expr_{expr}_mouth2.png")]
            p = stage / f"{who}_expr_{expr}_blink.png"
            if p.is_file():
                pairs.append((p.name, f"expr_{expr}_blink.png"))
            for src, dst in pairs:
                shutil.copyfile(stage / src, out / dst)
        for dst, src in GESTURES[who].items():
            if src.endswith("_fade"):
                fade_treat(stage / f"{src[:-5]}.png", out / f"{dst}.png")
            else:
                shutil.copyfile(stage / f"{src}.png", out / f"{dst}.png")
        # canonical reference for identity QC comparisons
        shutil.copyfile(pack / f"reference/{who}_canonical.png", out / "reference_canonical.png")

    bg = assets / "backgrounds"
    bg.mkdir(parents=True, exist_ok=True)
    for scene in ("student_room", "station", "cafe", "riverside_park"):
        shutil.copyfile(pack / f"backgrounds/{scene}.png", bg / f"{scene}.png")

    fonts = assets / "fonts"
    fonts.mkdir(exist_ok=True)
    shutil.copyfile(Path("assets/noto-sans-latin.ttf"), fonts / "noto-sans-latin.ttf")

    for f in sorted(assets.rglob("*")):
        if f.is_file():
            manifest["files"][str(f.relative_to(assets))] = {
                "bytes": f.stat().st_size,
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest()[:16],
            }
    (assets / "assets_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"promoted {len(manifest['files'])} files -> {assets}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
