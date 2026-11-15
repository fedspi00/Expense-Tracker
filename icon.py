"""Generate the TrackIt! app icon programmatically using Pillow.

Design: a smooth violet gradient squircle with a minimal white rising
sparkline — thick round strokes, soft area fill, end-point dot.
Everything is drawn at 4× and downsampled for crisp, slick edges.
"""
from PIL import Image, ImageChops, ImageDraw, ImageFilter

SS = 4  # supersampling factor

# Gradient stops (top → bottom)
_GRAD_TOP    = (139, 104, 255)   # light violet
_GRAD_BOTTOM = (74,  29, 150)    # deep violet


def _draw_artwork(size: int) -> Image.Image:
    """Render the full squircle icon at edge-to-edge size `size`."""
    s = size * SS
    img  = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Vertical gradient background ───────────────────────────────────────
    for y in range(s):
        t = y / (s - 1)
        r = round(_GRAD_TOP[0] + (_GRAD_BOTTOM[0] - _GRAD_TOP[0]) * t)
        g = round(_GRAD_TOP[1] + (_GRAD_BOTTOM[1] - _GRAD_TOP[1]) * t)
        b = round(_GRAD_TOP[2] + (_GRAD_BOTTOM[2] - _GRAD_TOP[2]) * t)
        draw.line([(0, y), (s - 1, y)], fill=(r, g, b, 255))

    # ── Soft radial highlight, top-left ────────────────────────────────────
    hi = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    hr = int(s * 0.9)
    hd.ellipse([-hr // 2, -hr // 2, hr, hr], fill=(255, 255, 255, 46))
    hi = hi.filter(ImageFilter.GaussianBlur(radius=s // 6))
    img = Image.alpha_composite(img, hi)
    draw = ImageDraw.Draw(img)

    # ── Sparkline geometry (relative to inner drawing box) ────────────────
    pad = int(s * 0.20)
    a   = s - 2 * pad                       # effective drawing area
    pts = [
        (pad + int(a * 0.00), pad + int(a * 0.72)),
        (pad + int(a * 0.34), pad + int(a * 0.44)),
        (pad + int(a * 0.58), pad + int(a * 0.58)),
        (pad + int(a * 1.00), pad + int(a * 0.06)),
    ]
    stroke   = max(2, int(a * 0.115))
    baseline = pad + int(a * 0.98)

    # ── Soft area fill under the line, fading out toward the baseline ─────
    area = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ad   = ImageDraw.Draw(area)
    ad.polygon(pts + [(pts[-1][0], baseline), (pts[0][0], baseline)],
               fill=(255, 255, 255, 80))
    top_y = min(p[1] for p in pts)
    fade  = Image.new("L", (s, s), 0)
    fd    = ImageDraw.Draw(fade)
    for y in range(top_y, baseline):
        v = round(255 * (1 - (y - top_y) / (baseline - top_y)) ** 1.7)
        fd.line([(0, y), (s - 1, y)], fill=v)
    area.putalpha(ImageChops.multiply(area.getchannel("A"), fade))
    area = area.filter(ImageFilter.GaussianBlur(radius=max(1, s // 90)))
    img  = Image.alpha_composite(img, area)
    draw = ImageDraw.Draw(img)

    # ── Glow behind the line ──────────────────────────────────────────────
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    gd.line(pts, fill=(255, 255, 255, 80), width=int(stroke * 1.6), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(radius=s // 40))
    img  = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # ── Crisp white sparkline with round caps ─────────────────────────────
    draw.line(pts, fill=(255, 255, 255, 255), width=stroke, joint="curve")
    for px, py in (pts[0], pts[-1]):                       # round end caps
        r = stroke // 2
        draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 255))

    # ── End-point dot (subtle emphasis, with breathing ring) ──────────────
    ex, ey = pts[-1]
    dot_r  = int(stroke * 0.62)
    ring_r = int(stroke * 1.05)
    draw.ellipse([ex - ring_r, ey - ring_r, ex + ring_r, ey + ring_r],
                 fill=(255, 255, 255, 56))
    draw.ellipse([ex - dot_r, ey - dot_r, ex + dot_r, ey + dot_r],
                 fill=(255, 255, 255, 255))

    # ── Squircle mask ─────────────────────────────────────────────────────
    mask      = Image.new("L", (s, s), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius    = int(s * 0.225)
    mask_draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=255)
    img.putalpha(mask)

    return img.resize((size, size), Image.LANCZOS)


def create_app_icon(size: int = 512) -> Image.Image:
    # macOS icon grid: the colored shape occupies ~82 % of the canvas, leaving
    # a transparent margin so it matches the visual size of system app icons.
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner  = int(round(size * 0.82))
    art    = _draw_artwork(inner)
    offset = (size - inner) // 2
    canvas.alpha_composite(art, (offset, offset))
    return canvas
