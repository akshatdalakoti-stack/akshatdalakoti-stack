"""
Bakes the profile mark into a looping animated SVG: three nested epicycles
tracing a five-fold rose.

Same constraint as the banner -- README images run inside <img>, where no
JavaScript executes -- so the motion is pre-computed and carried by SMIL.

Three arms turn at integer rates, each carried on the tip of the one before it,
and the pen at the end draws the closed curve

    z(t) = SUM_k  R_k * exp(i * w_k * t)

This is the Ptolemaic epicycle, and it is also exactly a truncated Fourier
series -- the same construction, thirteen centuries apart.

The five-fold symmetry is not decoration, it is forced. Advancing time by one
fifth of a period multiplies every term by exp(2*pi*i*w_k/5), so the whole
curve maps onto itself rotated by a fifth of a turn IF every frequency leaves
the same remainder mod 5. Hence (1, 6, -4): all of them are 1 mod 5. Change one
frequency to break that congruence and the rose loses its symmetry.

Because every rate is an integer, all three arms return to their starting angle
together after one period, so the loop closes exactly.

    python tools/gen_avatar.py        # -> assets/avatar.svg
"""
import math
import os

S = 512                                    # square canvas
BG = "#05060f"
VIOLET, CYAN, GOLD = "#7c5cff", "#4cc9f0", "#ffd166"
CX = CY = S / 2.0

ARMS = ((132.0, 1), (52.0, 6), (30.0, -4))  # (radius, turns per period)
MOD = 5                                     # every rate is 1 mod 5
DUR = 18.0                                  # seconds for the full figure
N = 1100                                    # samples along the curve
TS = 72                                     # keyTimes resolution
TRAIL = 300.0                               # length of the bright trailing arc

assert len({w % MOD for _, w in ARMS}) == 1, "frequencies must agree mod %d" % MOD


# ------------------------------------------------------------------ the curve
def curve(n=N):
    """The pen's path: a sum of rotating vectors, sampled at equal steps of time."""
    pts = []
    for i in range(n + 1):
        th = 2.0 * math.pi * i / n
        x = y = 0.0
        for r, w in ARMS:
            x += r * math.cos(w * th)
            y += r * math.sin(w * th)
        pts.append((CX + x, CY - y))       # screen y runs downward
    return pts


PTS = curve()
PATH = "M%.2f,%.2f" % PTS[0] + "".join("L%.2f,%.2f" % p for p in PTS[1:]) + "Z"


def arc_lengths(pts):
    """Cumulative arc length, so the trail can be pinned to the pen.

    The pen moves at a constant rate in TIME, which is not a constant rate along
    the drawn curve -- it races through the petal tips and dawdles at the
    cusps. Mapping time to arc length is what keeps the trail attached to it.
    """
    seg = [0.0]
    for i in range(1, len(pts)):
        seg.append(seg[-1] + math.hypot(pts[i][0] - pts[i - 1][0],
                                        pts[i][1] - pts[i - 1][1]))
    return seg


SEG = arc_lengths(PTS)
PLEN = SEG[-1]

# dash-offset walks the bright segment around the path in step with the pen
offsets = []
for i in range(TS + 1):
    f = i / TS
    x = f * (len(PTS) - 1)
    j = min(int(x), len(PTS) - 2)
    s = SEG[j] + (SEG[j + 1] - SEG[j]) * (x - j)
    offsets.append("%.1f" % (TRAIL - s))
KT = ";".join("%.5f" % (i / TS) for i in range(TS + 1))

# ------------------------------------------------------------------- the arms
# Nested rotations COMPOSE: an arm inherits every rotation above it, so its own
# turn rate must be the DIFFERENCE from the arm it hangs on. Frequencies
# (1, 6, -4) therefore require the arms to spin at (1, 5, -10). Spinning them at
# the frequencies themselves silently draws a different curve, and the pen
# drifts off the path it is supposed to be tracing.
_rates, _prev = [], 0
for _r, _w in ARMS:
    _rates.append((_r, _w - _prev))
    _prev = _w

pen = ('<circle r="34" fill="url(#glow)"/>'
       '<circle r="7.5" fill="%s"/><circle r="3" fill="#ffffff"/>' % CYAN)
for r, rate in reversed(_rates):
    pen = ('<g><animateTransform attributeName="transform" type="rotate" '
           'from="0 0 0" to="%d 0 0" dur="%gs" repeatCount="indefinite"/>'
           '<circle r="%.1f" fill="none" stroke="%s" stroke-width="1" '
           'opacity="0.18"/>'
           '<line x1="0" y1="0" x2="%.1f" y2="0" stroke="%s" stroke-width="1.4" '
           'opacity="0.38"/>'
           '<g transform="translate(%.1f 0)">%s</g></g>'
           % (360 if rate > 0 else -360, DUR / abs(rate), r, VIOLET, r, CYAN,
              r, pen))

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" '
       'xmlns:xlink="http://www.w3.org/1999/xlink" '
       'width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
       'aria-label="Three nested epicycles tracing a five-fold rose.">'
       '<defs><path id="rose" d="%s"/>'
       '<radialGradient id="glow">'
       '<stop offset="0" stop-color="#ffffff" stop-opacity="0.95"/>'
       '<stop offset="0.3" stop-color="%s" stop-opacity="0.5"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '<radialGradient id="vig" cx="50%%" cy="47%%" r="74%%">'
       '<stop offset="0.35" stop-color="#161c40" stop-opacity="0.8"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '</defs>'
       '<rect width="%d" height="%d" fill="%s"/>'
       '<rect width="%d" height="%d" fill="url(#vig)"/>'
       # the completed figure, sitting quietly underneath
       '<use xlink:href="#rose" href="#rose" fill="none" stroke="%s" '
       'stroke-width="13" opacity="0.13" stroke-linejoin="round"/>'
       '<use xlink:href="#rose" href="#rose" fill="none" stroke="%s" '
       'stroke-width="3" opacity="0.42" stroke-linejoin="round"/>'
       # the arc the pen has just cut
       '<use xlink:href="#rose" href="#rose" fill="none" stroke="%s" '
       'stroke-width="4.2" stroke-linecap="round" stroke-dasharray="%g %g">'
       '<animate attributeName="stroke-dashoffset" dur="%gs" '
       'repeatCount="indefinite" calcMode="linear" values="%s" keyTimes="%s"/>'
       '</use>'
       '<g transform="translate(%g %g) scale(1 -1)">%s</g>'
       '</svg>'
       % (S, S, S, S, PATH, CYAN, CYAN, BG, S, S, BG, S, S,
          VIOLET, GOLD, GOLD, TRAIL, PLEN - TRAIL, DUR, ";".join(offsets), KT,
          CX, CY, pen))

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, "assets", "avatar.svg")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(SVG)
print("wrote %s  (%.1f KB)" % (out, len(SVG) / 1024.0))
