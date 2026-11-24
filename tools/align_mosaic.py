"""Fine alignment mosaic: for a candidate anchor, generate a 5x5 grid of zoomed crops
at pixel offsets; VLM picks the crop where the feature is best centered."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

def mosaic(bust_path, cx, cy, crop_w, crop_h, step, out_path, zoom=3, label="feature"):
    crop_w, crop_h = int(crop_w), int(crop_h)
    step = int(step)
    im = Image.open(bust_path).convert("RGBA")
    W, H = im.size
    cols = rows = 5
    cw, ch = crop_w * zoom, crop_h * zoom
    sheet = Image.new("RGB", (cols * (cw + 6) + 6, rows * (ch + 22) + 26), (70, 70, 76))
    d = ImageDraw.Draw(sheet)
    d.text((8, 4), f"{bust_path} anchor=({cx},{cy}) step={step} label={label}", fill=(255, 255, 80))
    for r in range(rows):
        for c in range(cols):
            dx = (c - 2) * step
            dy = (r - 2) * step
            x0, y0 = cx + dx - crop_w // 2, cy + dy - crop_h // 2
            # clamp-free: pad if outside
            tile = Image.new("RGBA", (crop_w, crop_h), (255, 255, 255, 0))
            region = im.crop((max(0, x0), max(0, y0), max(0, x0) + crop_w, max(0, y0) + crop_h))
            tile.paste(region, (max(0, -x0), max(0, -y0)))
            tile = tile.resize((cw, ch), Image.LANCZOS)
            # crosshair
            dd = ImageDraw.Draw(tile)
            dd.line((cw // 2, 0, cw // 2, ch), fill=(255, 0, 0, 200), width=2)
            dd.line((0, ch // 2, cw, ch // 2), fill=(255, 0, 0, 200), width=2)
            x, y = 6 + c * (cw + 6), 26 + r * (ch + 22)
            sheet.paste(tile.convert("RGB"), (x, y))
            d.text((x + 4, y + ch + 3), f"r{r}c{c} d({dx},{dy})", fill=(200, 200, 200))
    sheet.save(out_path, quality=90)
    print("wrote", out_path, sheet.size)


if __name__ == "__main__":
    # usage: mosaic.py bust.png cx cy crop_w crop_h step out.jpg label
    a = sys.argv[1:]
    mosaic(a[0], int(a[1]), int(a[2]), int(a[3]), int(a[4]), int(a[5]), a[6], 3, a[7])
