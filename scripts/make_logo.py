"""
Willow Psychology Practice — standalone logo generator.

Reproduces the in-page brand mark (botanical willow sprig + "WILLOW." wordmark)
as background-less assets:
  - transparent high-res PNGs (gold / deep-green / white)
  - a self-contained transparent SVG (sprig paths + wordmark as vector paths
    when fontTools is available, else as <text> with a Google Fonts import)

Run:  python3 scripts/make_logo.py
Out:  output/willow-psychology/logo/
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "CormorantGaramond.ttf"
OUT = ROOT / "output" / "willow-psychology" / "logo"
OUT.mkdir(parents=True, exist_ok=True)

GOLD = (169, 140, 107)      # #A98C6B
GREEN = (43, 51, 45)        # #2B332D
WHITE = (250, 251, 248)     # #FAFBF8

WORD = "WILLOW."
WGHT = 560                  # font weight (medium / semibold feel)

# ---------------------------------------------------------------- geometry
# Sprig in its own 100 x 122 space (matches build_page.py SPRIG).
LEAF_CUBICS = [
    [(0, 0), (7, -6), (17, -6), (23, 0)],
    [(23, 0), (17, 6), (7, 6), (0, 0)],
]
LEAF_MIDRIB = [(4, 0), (19, 0)]
LEAVES = [(50, 48, -90), (50, 70, -145), (50, 70, -35), (50, 92, -150), (50, 92, -30)]
STEM = [(50, 118), (47, 96), (51, 76), (50, 48)]


def cubic(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def leaf_polylines(tx, ty, deg):
    """Leaf outline + midrib transformed by SVG translate(tx,ty) rotate(deg)."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def tf(p):
        x, y = p
        return (tx + x * ca - y * sa, ty + x * sa + y * ca)

    outline = []
    for c in LEAF_CUBICS:
        outline += cubic(*c)
    return [[tf(p) for p in outline], [tf(p) for p in LEAF_MIDRIB]]


def sprig_polylines():
    polys = [cubic(*STEM)]                       # stem
    for (tx, ty, deg) in LEAVES:
        polys += leaf_polylines(tx, ty, deg)
    return polys


# ---------------------------------------------------------------- raster
def render_png(color, name):
    SS = 4                       # supersample
    W, H = 1180, 760             # final canvas
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # --- sprig ---
    sprig_h = 300                # final px tall
    s = sprig_h / 122 * SS       # scale (work px per sprig unit)
    cx = W / 2 * SS              # centre x in work px
    top = 36 * SS
    ox = cx - 50 * s             # sprig local x=50 -> centre
    oy = top
    lw = max(2, int(1.5 * s))    # stroke width

    def place(poly):
        return [(ox + x * s, oy + y * s) for (x, y) in poly]

    for poly in sprig_polylines():
        d.line(place(poly), fill=color, width=lw, joint="curve")
        # round the caps
        for (px, py) in (place(poly)[0], place(poly)[-1]):
            r = lw / 2
            d.ellipse([px - r, py - r, px + r, py + r], fill=color)

    # --- wordmark ---
    fsize = int(178 * SS)
    font = ImageFont.truetype(str(FONT_PATH), fsize)
    try:
        font.set_variation_by_axes([WGHT])
    except Exception:
        pass
    ls = int(0.14 * fsize)       # letter spacing
    widths = [font.getlength(c) for c in WORD]
    total = sum(widths) + ls * (len(WORD) - 1)
    wx = cx - total / 2
    wy = (sprig_h + 92) * SS     # below the sprig
    for c, w in zip(WORD, widths):
        d.text((wx, wy), c, font=font, fill=color)
        wx += w + ls

    # crop to content + downsample
    bbox = img.getbbox()
    pad = 28 * SS
    bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad))
    img = img.crop(bbox)
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    img.save(OUT / name)
    return img.size


# ---------------------------------------------------------------- svg
def svg_sprig_paths():
    """Return SVG <path>/<polyline> markup for the sprig (gold stroke)."""
    def d_from(poly):
        return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in poly)
    parts = [f'<path d="{d_from(p)}"/>' for p in sprig_polylines()]
    return "".join(parts)


def make_svg(hexcolor, name, glyphs=None):
    """Lay out sprig (top) + wordmark (below), centred, sized to content."""
    sprig = svg_sprig_paths()
    pad = 30.0
    sprig_h = 168.0
    ssc = sprig_h / 122.0
    sprig_w = 100.0 * ssc
    gap = 30.0

    if glyphs:
        d_units, adv_units, upm = glyphs
        gscale = (sprig_h / 1.7) / upm          # font size ~ sprig_h/1.7
        word_w = adv_units * gscale
        cap = 0.66 * (sprig_h / 1.7)
        word = None
    else:
        # fallback: web-font <text> (needs network at render time)
        gscale = None
        word_w = 360.0
        cap = 100.0

    content_w = max(sprig_w, word_w) + 2 * pad
    cx = content_w / 2.0
    baseline = pad + sprig_h + gap + cap
    content_h = baseline + pad * 0.7

    sprig_g = (
        f'<g transform="translate({cx - sprig_w / 2:.2f},{pad:.2f}) scale({ssc:.4f})" '
        f'stroke="{hexcolor}" stroke-width="1.4" stroke-linecap="round" '
        f'stroke-linejoin="round" fill="none">{sprig}</g>'
    )
    if glyphs:
        tx = cx - word_w / 2.0
        word = (
            f'<g transform="translate({tx:.2f},{baseline:.2f}) scale({gscale:.5f},{-gscale:.5f})" '
            f'fill="{hexcolor}" stroke="none">{d_units}</g>'
        )
        css = ""
    else:
        word = (
            f'<text x="{cx:.1f}" y="{baseline:.1f}" text-anchor="middle" fill="{hexcolor}" '
            f'font-family="Cormorant Garamond, Georgia, serif" font-weight="600" '
            f'font-size="{cap * 1.5:.0f}" letter-spacing="{cap * 0.18:.0f}">WILLOW.</text>'
        )
        css = ('<style>@import url(https://fonts.googleapis.com/css2?'
               'family=Cormorant+Garamond:wght@600&amp;display=swap);</style>')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {content_w:.1f} {content_h:.1f}" fill="none">'
        f'{css}{sprig_g}{word}</svg>'
    )
    (OUT / name).write_text(svg, encoding="utf-8")


def try_text_to_svg_path():
    """Convert WILLOW. to an SVG path group transform + path data via fontTools."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        from fontTools.pens.svgPathPen import SVGPathPen
    except Exception:
        return None
    try:
        f = TTFont(str(FONT_PATH))
        instantiateVariableFont(f, {"wght": WGHT}, inplace=True)
        upm = f["head"].unitsPerEm
        cmap = f.getBestCmap()
        gs = f.getGlyphSet()
        hmtx = f["hmtx"]
        ls = int(0.14 * upm)
        x = 0
        d_all = []
        for ch in WORD:
            gname = cmap.get(ord(ch))
            if not gname:
                continue
            pen = SVGPathPen(gs)
            gs[gname].draw(pen)
            seg = pen.getCommands()
            if seg:
                d_all.append(f'<path transform="translate({x},0)" d="{seg}"/>')
            x += hmtx[gname][0] + ls
        total_adv = x - ls                       # font units, baseline at y=0 (y-up)
        return ("".join(d_all), total_adv, upm)
    except Exception as e:
        print("  (text->path failed, using <text> fallback:", e, ")")
        return None


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    for color, name in [(GOLD, "willow-logo-gold.png"),
                        (GREEN, "willow-logo-green.png"),
                        (WHITE, "willow-logo-white.png")]:
        size = render_png(color, name)
        print(f"PNG  {name}  {size[0]}x{size[1]}")

    fp = try_text_to_svg_path()
    make_svg("#A98C6B", "willow-logo-gold.svg", fp)
    make_svg("#2B332D", "willow-logo-green.svg", fp)
    print("SVG  willow-logo-gold.svg, willow-logo-green.svg",
          "(vector wordmark)" if fp else "(web-font wordmark)")
    print("Out:", OUT)
