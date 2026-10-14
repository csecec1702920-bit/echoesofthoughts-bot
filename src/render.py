"""Render a quote as a minimal dark 1080x1350 JPEG."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent.parent / "fonts"


def _font(name, size, weight=None):
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight] if "Inter" not in name else [14 if size < 40 else 32, weight])
        except Exception:
            pass
    return f


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(quote, out_path, cfg, handle):
    c = cfg["image"]
    W, H = c["width"], c["height"]
    img = Image.new("RGB", (W, H), c["background"])
    d = ImageDraw.Draw(img)
    margin = 130
    max_w = W - 2 * margin

    # Shrink font until the quote fits comfortably in the middle 60% of the canvas.
    size = 74
    while size > 36:
        font = _font("PlayfairDisplay.ttf", size, 420)
        lines = _wrap(d, quote, font, max_w)
        line_h = int(size * 1.42)
        if len(lines) * line_h <= H * 0.58:
            break
        size -= 3

    block_h = len(lines) * line_h
    y = (H - block_h) // 2 - 20

    # Opening quote mark
    mark = _font("PlayfairDisplay-Italic.ttf", 180, 500)
    d.text((margin - 10, y - 170), "“", font=mark, fill=c["accent_color"])

    for ln in lines:
        d.text((margin, y), ln, font=font, fill=c["text_color"])
        y += line_h

    # Accent rule + handle
    y += 50
    d.line([(margin, y), (margin + 70, y)], fill=c["accent_color"], width=3)
    small = _font("Inter.ttf", 30, 400)
    d.text((margin, H - 120), handle, font=small, fill=c["muted_color"])

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=92, optimize=True)  # Instagram API requires JPEG
    return out_path
