"""
Bakes a lensed black hole into a looping animated SVG banner.

GitHub runs no JavaScript in a README, so the motion lives inside the SVG.
The constraint that shapes everything here is cost: the browser re-rasterises
the document every frame, so what matters is how many SMIL timelines are
ticking and whether a filter sits in the paint path.

  * no filters.  A full-canvas feGaussianBlur over 1200x400 dominates the
                 frame budget by itself. The glow is faked instead with a
                 wide, low-opacity stroke laid under each bright one -- two
                 static paints rather than a blur re-run every frame.
  * one timeline per moving thing.  Stars are batched into three paths of
                 zero-length round-capped segments, so two hundred stars cost
                 three animations rather than two hundred. Disc families fade
                 in as groups, so each orbit carries exactly one animation:
                 its own dash offset.
  * the shear is the point.  Each orbit's dash period follows Kepler, so the
                 inner orbits visibly run ahead of the outer ones. The disc
                 does not turn like a wheel, which is the whole reason to
                 draw one.

Colour is temperature, not decoration: the inner orbits run blue-white, the
outer ones fall through amber into the crimson the rest of the profile uses,
and every orbit is ramped left to right for relativistic beaming -- the side
turning toward you is brighter and bluer.

Run from the repository root:  python tools/gen_hole.py
"""
import math
import random

W, H = 1200.0, 400.0
CX, CY = W / 2, H / 2
LOOP = 9.0

BG = "#05060f"
SPINE = "#9e1330"
RS = 66.0                      # the shadow
RPH = RS * 1.05                # the photon ring
NR = 10
RAD = [76.0 + i * 10.0 for i in range(NR)]
FLAT = 0.115                   # the disc, seen nearly edge-on

# inner orbits are hotter, so the ramp runs blue-white -> amber -> crimson
TEMP = ["#d6f2ff", "#a9dcff", "#e8ecff", "#ffeec4", "#ffd28a", "#ffab62",
        "#ff7d4c", "#ff5340", "#e63147", "#b52235"]


def fmt(x, n=2):
    return ("%.*f" % (n, x)).rstrip("0").rstrip(".")


def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    p, q = hx(a), hx(b)
    return "#%02x%02x%02x" % tuple(round(p[i] + (q[i] - p[i]) * t) for i in range(3))


def elen(a, b):
    h = ((a - b) ** 2) / ((a + b) ** 2)
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h))) / 2


def half(r, ry, top):
    return "M%s %sA%s %s 0 0 %d %s %s" % (fmt(CX - r), fmt(CY), fmt(r), fmt(ry),
                                          1 if top else 0, fmt(CX + r), fmt(CY))


def lensed(r, lift, up):
    return "M%s %sA%s %s 0 0 %d %s %s" % (fmt(CX - r), fmt(CY), fmt(r), fmt(lift),
                                          1 if up else 0, fmt(CX + r), fmt(CY))


def orbit(path, r, ry, i, w, op, glow=0.0):
    """One orbit: an optional static glow underlay, then the lit stroke streaming."""
    ln = elen(r, ry)
    per = 3.2 * (r / RAD[0]) ** 1.5        # Kepler: inner orbits come round sooner
    dash, gap = ln * 0.40, ln * 0.06
    shift = fmt(-(dash + gap))
    anim = ('<animate attributeName="stroke-dashoffset" values="0;%s" dur="%ss" '
            'repeatCount="indefinite"/>' % (shift, fmt(per)))
    out = []
    if glow:
        out.append('<path d="%s" stroke="url(#b%d)" stroke-width="%s" fill="none" '
                   'opacity="%s" stroke-dasharray="%s %s" stroke-linecap="round">%s</path>'
                   % (path, i, fmt(w * 4.2), fmt(glow), fmt(dash), fmt(gap), anim))
    out.append('<path d="%s" stroke="url(#b%d)" stroke-width="%s" fill="none" opacity="%s" '
               'stroke-dasharray="%s %s" stroke-linecap="round">%s</path>'
               % (path, i, fmt(w), fmt(op), fmt(dash), fmt(gap), anim))
    return "".join(out)


def group(inner, t0, t1):
    """One opacity timeline for a whole family, rather than one per member."""
    return ('<g opacity="0">%s<animate attributeName="opacity" values="0;0;1;1;0" '
            'keyTimes="0;%s;%s;0.93;1" dur="%ss" repeatCount="indefinite"/></g>'
            % (inner, fmt(t0), fmt(t1), fmt(LOOP)))


def drawn(d, tot, colour, op, t0, t1, w=1.0):
    return ('<path d="%s" stroke="%s" stroke-width="%s" fill="none" opacity="%s" '
            'stroke-dasharray="%s" stroke-dashoffset="%s">'
            '<animate attributeName="stroke-dashoffset" values="%s;%s;0;0;%s" '
            'keyTimes="0;%s;%s;0.93;1" dur="%ss" calcMode="spline" '
            'keySplines="0 0 1 1;.4 0 .2 1;0 0 1 1;.6 0 .9 1" repeatCount="indefinite"/></path>'
            % (d, colour, fmt(w), fmt(op), fmt(tot), fmt(tot), fmt(tot), fmt(tot), fmt(tot),
               fmt(t0), fmt(t1), fmt(LOOP)))


random.seed(23)
p = []

# --- starfield, deflected outward, batched into three paints -----------------
buckets = {"#ffffff": [], "#bcd8ff": [], "#ffd9a6": []}
arcs = []
for _ in range(240):
    sx, sy = 14 + random.random() * (W - 28), 12 + random.random() * (H - 24)
    dx, dy = sx - CX, sy - CY
    b = math.hypot(dx, dy) or 1.0
    d = min(2100.0 / b, b * 0.8)
    nx, ny = CX + dx / b * (b + d), CY + dy / b * (b + d)
    if not (6 < nx < W - 6 and 4 < ny < H - 4):
        continue
    nb = math.hypot(nx - CX, ny - CY)
    if nb < 250 and random.random() < 0.2:
        a0 = math.atan2(ny - CY, nx - CX)
        sw = 0.05 + 0.15 * (235.0 / nb)
        arcs.append("M%s %sA%s %s 0 0 1 %s %s"
                    % (fmt(CX + nb * math.cos(a0 - sw), 1), fmt(CY + nb * math.sin(a0 - sw), 1),
                       fmt(nb, 1), fmt(nb, 1),
                       fmt(CX + nb * math.cos(a0 + sw), 1), fmt(CY + nb * math.sin(a0 + sw), 1)))
    else:
        c = random.choice(("#ffffff", "#ffffff", "#bcd8ff", "#ffd9a6"))
        buckets[c].append("M%s %sh0" % (fmt(nx, 1), fmt(ny, 1)))

for k, c in enumerate(("#ffffff", "#bcd8ff", "#ffd9a6")):
    p.append(group('<path d="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" '
                   'fill="none" opacity="%s"/>'
                   % ("".join(buckets[c]), c, fmt(1.5 + 0.3 * k), fmt(0.6 + 0.1 * k)),
                   0.02 + 0.05 * k, 0.16 + 0.05 * k))
p.append(group('<path d="%s" stroke="#ffb0a0" stroke-width="0.9" fill="none" opacity="0.34"/>'
               % "".join(arcs), 0.14, 0.30))

# --- far side of the disc, lensed up over the top (behind the shadow) --------
far = []
for i, r in enumerate(RAD):
    lift = r * (0.60 - 0.018 * i)
    far.append(orbit(lensed(r, lift, True), r, lift, i, 1.7, 0.62))
    far.append(orbit(half(r, r * FLAT, True), r, r * FLAT, i, 1.9, 0.7))
p.append(group("".join(far), 0.20, 0.40))

# --- the shadow, and the photon ring rimming it ------------------------------
p.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (fmt(CX), fmt(CY), fmt(RS), BG))
p.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#9fd0ff" stroke-width="9" '
         'opacity="0.13"/>' % (fmt(CX), fmt(CY), fmt(RPH)))
c = 2 * math.pi * RPH
p.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#f2f8ff" stroke-width="2.4" '
         'stroke-dasharray="%s" stroke-dashoffset="%s">'
         '<animate attributeName="stroke-dashoffset" values="%s;%s;0;0;%s" '
         'keyTimes="0;0.34;0.52;0.93;1" dur="%ss" calcMode="spline" '
         'keySplines="0 0 1 1;.4 0 .2 1;0 0 1 1;.6 0 .9 1" repeatCount="indefinite"/></circle>'
         % (fmt(CX), fmt(CY), fmt(RPH), fmt(c), fmt(c), fmt(c), fmt(c), fmt(c), fmt(LOOP)))

# --- near side, crossing in front of the shadow ------------------------------
near = []
for i, r in enumerate(RAD):
    near.append(orbit(half(r, r * FLAT, False), r, r * FLAT, i, 2.4, 0.95,
                      glow=0.09 if i < 5 else 0.0))
    lift = r * (0.27 - 0.009 * i)
    near.append(orbit(lensed(r, lift, False), r, lift, i, 1.5, 0.52))
p.append(group("".join(near), 0.22, 0.42))

# --- the spine, carried over from the rest of the profile --------------------
GAP = 210.0
sp, st = [], 0.0
for x0, x1 in ((40.0, CX - GAP), (CX + GAP, W - 40.0)):
    sp.append("M%s %sL%s %s" % (fmt(x0), fmt(CY), fmt(x1), fmt(CY)))
    st += x1 - x0
tk, tt = [], 0.0
for i in range(41):
    x = 40 + i * (W - 80) / 40.0
    if abs(x - CX) < GAP:
        continue
    h = 9.0 if i % 5 == 0 else 4.0
    tk.append("M%s %sL%s %s" % (fmt(x), fmt(CY - h), fmt(x), fmt(CY + h)))
    tt += 2 * h
p.append(drawn(" ".join(sp), st, SPINE, 0.3, 0.0, 0.24))
p.append(drawn(" ".join(tk), tt, SPINE, 0.32, 0.02, 0.28))

# one gradient per orbit: dimmed and reddened receding, brightened approaching
grads = []
for i, base in enumerate(TEMP):
    grads.append('<linearGradient id="b%d" x1="0" y1="0" x2="1" y2="0">'
                 '<stop offset="0" stop-color="%s"/><stop offset="0.34" stop-color="%s"/>'
                 '<stop offset="0.72" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
                 '</linearGradient>'
                 % (i, mix(base, "#3a0a18", 0.62), mix(base, "#5e0f20", 0.24),
                    base, mix(base, "#ffffff", 0.55)))

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" '
       'height="400" role="img" aria-label="A black hole: its shadow rimmed by a bright '
       'photon ring, an accretion disc seen almost edge-on that runs blue-white at the inner '
       'orbits and crimson at the outer ones, its far side lensed up over the top, and a '
       'starfield smeared into arcs around it.">\n'
       '<defs>%s<radialGradient id="halo">'
       '<stop offset="0" stop-color="#ff7a52" stop-opacity="0.11"/>'
       '<stop offset="0.42" stop-color="#ff2d46" stop-opacity="0.045"/>'
       '<stop offset="1" stop-color="#ff2d46" stop-opacity="0"/></radialGradient></defs>\n'
       '<rect width="1200" height="400" fill="%s"/>\n'
       '<circle cx="%s" cy="%s" r="340" fill="url(#halo)"/>\n%s\n</svg>\n'
       % ("".join(grads), BG, fmt(CX), fmt(CY), "\n".join(p)))

with open("assets/hole.svg", "w", encoding="utf-8") as fh:
    fh.write(svg)
print("wrote assets/hole.svg  %.1f KB" % (len(svg.encode("utf-8")) / 1024))
