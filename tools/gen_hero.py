"""
Bakes the transmutation circle into a looping animated SVG banner.

GitHub runs no JavaScript in a README, so the motion has to live inside the
SVG. The skull that used to be here was raster-shaped -- every pixel changed
every frame -- so it had to ship as a flipbook of pre-rendered character grids,
about 180 KB of them. This is vector: circles, a hexagram, tick marks. So the
whole thing is a few kilobytes of geometry with SMIL animation on top, and the
motion is genuinely continuous rather than stepped.

The cycle, over one loop:

  * construct : each stroke draws itself by running stroke-dashoffset down from
                its own length to zero. SMIL carries per-element values, which
                CSS keyframes cannot without a rule per distinct length.
  * turn      : the rune band and the hexagram counter-rotate the whole time,
                on their own much longer periods, so the figure never sits still
                even while nothing is being drawn.
  * ignite    : a bright arc sweeps the circumference, then the array flares.
  * reset     : everything runs back down and the loop closes seamlessly.

Geometry is computed here rather than hand-written so the hexagram actually
inscribes the inner ring and the tick marks actually divide the circle evenly.

Run from the repository root:  python tools/gen_hero.py
"""
import math

W, H = 1200.0, 400.0
CX, CY = W / 2, H / 2
R = 165.0                    # outer ring
LOOP = 9.0                   # seconds for one full cycle

BG = "#05060f"
GOLD = "#ffd166"
CYAN = "#4cc9f0"
VIOLET = "#7c5cff"
INK = "#e8ecff"

TICKS = 60                   # divisions of the rune band
SAT_R = 44.0                 # flanking satellite arrays


def fmt(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")


def circle(cx, cy, r, stroke, w, opacity=1.0, extra=""):
    return ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
            'stroke-width="%s" opacity="%s"%s>' % (fmt(cx), fmt(cy), fmt(r), stroke,
                                                   fmt(w), fmt(opacity), extra))


def draw_anim(length, t0, t1, hold_to=0.93):
    """stroke-dashoffset from full length to zero across [t0,t1] of the loop."""
    return ('<animate attributeName="stroke-dashoffset" '
            'values="%s;%s;0;0;%s" keyTimes="0;%s;%s;%s;1" dur="%ss" '
            'calcMode="spline" keySplines="0 0 1 1;.4 0 .2 1;0 0 1 1;.6 0 .9 1" '
            'repeatCount="indefinite"/>'
            % (fmt(length), fmt(length), fmt(length),
               fmt(t0), fmt(t1), fmt(hold_to), fmt(LOOP)))


def dashed(length):
    return ' stroke-dasharray="%s" stroke-dashoffset="%s"' % (fmt(length), fmt(length))


def spin(cx, cy, period, reverse=False):
    a, b = (360, 0) if reverse else (0, 360)
    return ('<animateTransform attributeName="transform" type="rotate" '
            'values="%d %s %s;%d %s %s" dur="%ss" repeatCount="indefinite"/>'
            % (a, fmt(cx), fmt(cy), b, fmt(cx), fmt(cy), fmt(period)))


def hexagram(cx, cy, r, t0, t1):
    """Two triangles, inscribed. Perimeter of each is 3*r*sqrt(3)."""
    out = []
    per = 3.0 * r * math.sqrt(3.0)
    for k, off in enumerate((0.0, math.pi / 3)):
        pts = " ".join("%s,%s" % (fmt(cx + r * math.cos(off + i * 2 * math.pi / 3)),
                                  fmt(cy + r * math.sin(off + i * 2 * math.pi / 3)))
                       for i in range(3))
        out.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="1.6" '
                   'stroke-linejoin="round"%s>%s</polygon>'
                   % (pts, CYAN, dashed(per), draw_anim(per, t0 + k * 0.045, t1 + k * 0.045)))
    return "".join(out)


def rune_band(cx, cy, r, n, t0, t1):
    """Tick marks between the outer rings, longer every third division."""
    out = []
    total = 0.0
    segs = []
    for i in range(n):
        a = i * 2 * math.pi / n
        long = (i % 3 == 0)
        r0 = r - (10.0 if long else 6.0)
        r1 = r - 1.5
        segs.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                     cx + r1 * math.cos(a), cy + r1 * math.sin(a), long))
        total += r1 - r0
    d = " ".join("M%s %sL%s %s" % (fmt(x0), fmt(y0), fmt(x1), fmt(y1))
                 for x0, y0, x1, y1, _ in segs)
    out.append('<path d="%s" stroke="%s" stroke-width="1.5" fill="none" opacity="0.85"%s>%s</path>'
               % (d, GOLD, dashed(total), draw_anim(total, t0, t1)))
    return "".join(out)


def array(cx, cy, r, t0, scale=1.0, band_period=90.0, hex_period=140.0):
    """One complete transmutation array, built outward from the centre."""
    g = ['<g>']
    g.append(circle(cx, cy, r, GOLD, 2.0 * scale, 0.95, dashed(2 * math.pi * r))
             + draw_anim(2 * math.pi * r, t0, t0 + 0.16) + '</circle>')
    g.append(circle(cx, cy, r - 10 * scale, GOLD, 1.0 * scale, 0.45,
                    dashed(2 * math.pi * (r - 10 * scale)))
             + draw_anim(2 * math.pi * (r - 10 * scale), t0 + 0.04, t0 + 0.20) + '</circle>')

    g.append('<g>' + rune_band(cx, cy, r, int(TICKS * scale), t0 + 0.10, t0 + 0.30)
             + spin(cx, cy, band_period) + '</g>')

    ri = r * 0.60
    g.append(circle(cx, cy, ri, GOLD, 1.4 * scale, 0.75, dashed(2 * math.pi * ri))
             + draw_anim(2 * math.pi * ri, t0 + 0.14, t0 + 0.30) + '</circle>')
    g.append('<g>' + hexagram(cx, cy, ri, t0 + 0.22, t0 + 0.44)
             + spin(cx, cy, hex_period, reverse=True) + '</g>')

    rc = r * 0.22
    g.append(circle(cx, cy, rc, CYAN, 1.4 * scale, 0.9, dashed(2 * math.pi * rc))
             + draw_anim(2 * math.pi * rc, t0 + 0.36, t0 + 0.48) + '</circle>')

    # spokes and vertex nodes
    spokes, per = [], 0.0
    for k in range(6):
        a = k * math.pi / 3
        x, y = cx + ri * math.cos(a), cy + ri * math.sin(a)
        spokes.append("M%s %sL%s %s" % (fmt(cx + rc * math.cos(a)), fmt(cy + rc * math.sin(a)),
                                        fmt(x), fmt(y)))
        per += ri - rc
    g.append('<path d="%s" stroke="%s" stroke-width="1" fill="none" opacity="0.5"%s>%s</path>'
             % (" ".join(spokes), CYAN, dashed(per), draw_anim(per, t0 + 0.40, t0 + 0.54)))
    for k in range(6):
        a = k * math.pi / 3
        x, y = cx + ri * math.cos(a), cy + ri * math.sin(a)
        g.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.25" stroke="%s" '
                 'stroke-width="1.2" opacity="0">'
                 '<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;%s;%s;0.93;1" '
                 'dur="%ss" repeatCount="indefinite"/></circle>'
                 % (fmt(x), fmt(y), fmt(5 * scale), GOLD, GOLD,
                    fmt(t0 + 0.46), fmt(t0 + 0.56), fmt(LOOP)))

    # the arc that races the circumference, then the flare
    c = 2 * math.pi * r
    g.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s" '
             'stroke-linecap="round" stroke-dasharray="%s %s" opacity="0">'
             '<animate attributeName="stroke-dashoffset" values="0;%s" keyTimes="0;1" '
             'begin="%ss" dur="%ss" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values="0;0;1;1;0;0" '
             'keyTimes="0;%s;%s;%s;%s;1" dur="%ss" repeatCount="indefinite"/>'
             '</circle>'
             % (fmt(cx), fmt(cy), fmt(r), INK, fmt(2.6 * scale), fmt(c * 0.16), fmt(c),
                fmt(-c), fmt(t0 * LOOP), fmt(LOOP * 0.34),
                fmt(t0 + 0.56), fmt(t0 + 0.60), fmt(t0 + 0.86), fmt(t0 + 0.92), fmt(LOOP)))
    g.append('</g>')
    return "".join(g)


def main():
    parts = []
    # a spine running the full width, so the banner is a composition and not a
    # small figure marooned in a lot of black
    ticks = []
    total = 0.0
    for i in range(41):
        x = 40 + i * (W - 80) / 40.0
        if abs(x - CX) < R + 26:
            continue
        h = 9.0 if i % 5 == 0 else 4.0
        ticks.append("M%s %sL%s %s" % (fmt(x), fmt(CY - h), fmt(x), fmt(CY + h)))
        total += 2 * h
    parts.append('<path d="%s" stroke="%s" stroke-width="1" fill="none" opacity="0.35"%s>%s</path>'
                 % (" ".join(ticks), VIOLET, dashed(total), draw_anim(total, 0.02, 0.30)))
    for x0, x1 in ((40, CX - R - 30), (CX + R + 30, W - 40)):
        parts.append('<path d="M%s %sL%s %s" stroke="%s" stroke-width="1" opacity="0.30"%s>%s</path>'
                     % (fmt(x0), fmt(CY), fmt(x1), fmt(CY), VIOLET,
                        dashed(x1 - x0), draw_anim(x1 - x0, 0.0, 0.26)))

    parts.append(array(CX - R - 30 - 96, CY, SAT_R, 0.06, 0.62, 70.0, 110.0))
    parts.append(array(CX + R + 30 + 96, CY, SAT_R, 0.10, 0.62, 82.0, 96.0))
    parts.append(array(CX, CY, R, 0.0, 1.0))

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" '
        'width="1200" height="400" role="img" '
        'aria-label="An alchemical transmutation circle drawing itself stroke by '
        'stroke, its rune band and inscribed hexagram counter-rotating, then '
        'igniting as a bright arc races around the circumference.">\n'
        '<defs><filter id="g" x="-25%%" y="-25%%" width="150%%" height="150%%">'
        '<feGaussianBlur stdDeviation="3.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter></defs>\n'
        '<rect width="1200" height="400" fill="%s"/>\n'
        '<g filter="url(#g)" stroke-linecap="round">\n%s\n</g>\n</svg>\n'
    ) % (BG, "\n".join(parts))

    with open("assets/hero.svg", "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("wrote assets/hero.svg  %.1f KB" % (len(svg.encode("utf-8")) / 1024))


if __name__ == "__main__":
    main()
