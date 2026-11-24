"""Phase 0 asset audit: verify checksums, measure alpha/panels, build contact sheet.

Usage: python3 art_audit.py <asset_pack_dir> <output_qa_dir>
Writes asset_audit.json and contact_sheet.png.
"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

THUMB = 220


def alpha_stats(im):
    if im.mode != "RGBA":
        return {"mode": im.mode, "has_alpha": False}
    a = im.getchannel("A")
    hist = a.histogram()
    total = sum(hist)
    transparent = sum(hist[:16])
    semi = sum(hist[16:240])
    opaque = sum(hist[240:])
    bbox = a.getbbox()
    return {
        "mode": im.mode,
        "has_alpha": True,
        "transparent_pct": round(100 * transparent / total, 2),
        "semi_pct": round(100 * semi / total, 2),
        "opaque_pct": round(100 * opaque / total, 2),
        "alpha_bbox": list(bbox) if bbox else None,
    }


def detect_panels(im):
    """Detect a grid of opaque panels by projecting alpha coverage onto rows/cols."""
    if im.mode != "RGBA":
        return None
    w, h = im.size
    small = im.resize((min(w, 560), min(h, 700)))
    sw, sh = small.size
    a = small.getchannel("A").point(lambda v: 1 if v > 40 else 0)
    px = a.load()
    colcov = [sum(px[x, y] for y in range(sh)) / sh for x in range(sw)]
    rowcov = [sum(px[x, y] for x in range(sw)) / sw for y in range(sh)]

    def cuts(cov, thresh):
        runs, start = [], None
        for i, v in enumerate(cov):
            if v > thresh and start is None:
                start = i
            elif v <= thresh and start is not None:
                runs.append((start, i))
                start = None
        if start is not None:
            runs.append((start, len(cov)))
        # drop hairline runs
        return [r for r in runs if r[1] - r[0] >= max(3, int(len(cov) * 0.05))]

    cols, rows = cuts(colcov, 0.03), cuts(rowcov, 0.03)
    return {"cols": len(cols), "rows": len(rows),
            "col_bands": cols, "row_bands": rows,
            "grid": f"{len(cols)}x{len(rows)}" if cols and rows else "unclear"}


def main():
    pack = Path(sys.argv[1]).resolve()
    qa = Path(sys.argv[2]).resolve()
    qa.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    audit = {"pack_version": manifest.get("version"), "entries": [], "notes": []}

    thumbs = []
    for entry in manifest["assets"]:
        rel = entry["path"]
        p = pack / rel
        rec = {"path": rel, "exists": p.is_file()}
        if not p.is_file():
            audit["entries"].append(rec)
            continue
        data = p.read_bytes()
        rec["sha256"] = hashlib.sha256(data).hexdigest()
        rec["sha256_matches_manifest"] = rec["sha256"] == entry.get("sha256")
        with Image.open(p) as im:
            rec["size_px"] = list(im.size)
            rec.update(alpha_stats(im))
            if entry["status"] == "SOURCE_SHEET_NEEDS_EXTRACTION":
                rec["panel_detection"] = detect_panels(im)
            im2 = im.convert("RGBA")
            im2.thumbnail((THUMB, THUMB))
            canvas = Image.new("RGBA", (THUMB + 4, THUMB + 26), (24, 24, 28, 255))
            canvas.paste(im2, (2, 24), im2)
            d = ImageDraw.Draw(canvas)
            d.text((4, 4), rel, fill=(240, 240, 240, 255))
            thumbs.append(canvas)
        audit["entries"].append(rec)

    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * (THUMB + 8), rows * (THUMB + 34)), (40, 40, 46, 255))
    for i, t in enumerate(thumbs):
        x, y = (i % cols) * (THUMB + 8) + 4, (i // cols) * (THUMB + 34) + 4
        sheet.alpha_composite(t, (x, y))
    sheet.convert("RGB").save(qa / "contact_sheet.png")

    bad = [e["path"] for e in audit["entries"] if not e.get("sha256_matches_manifest", False)]
    audit["notes"].append(f"checksum mismatches: {bad or 'none'}")
    (qa / "asset_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({e["path"]: {k: e.get(k) for k in ("size_px", "opaque_pct", "panel_detection")}
                      for e in audit["entries"]}, indent=1))
    print(f"Wrote {qa / 'asset_audit.json'} and contact_sheet.png")


if __name__ == "__main__":
    main()
