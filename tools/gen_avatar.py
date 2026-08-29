"""
Bakes the profile mark into a looping animated SVG: a body orbiting a mass that
visibly bends the lattice around it.

Same constraint as the banner -- README images run inside <img>, where no
JavaScript executes -- so the motion is pre-computed and carried by SMIL.

The lattice is static. That is not a shortcut: the only mass heavy enough to
bend it visibly is the one at the centre, and that one does not move. The
orbiting body is a test particle, far too light to dent the sheet.

The orbit is a circle in its own plane, viewed at an inclination, so on screen
it reads as an ellipse. The body moves at a constant angular rate in that plane,
which is NOT constant speed along the drawn ellipse: it appears to slow at the
turns and hurry through the middle. That timing is what keyPoints/keyTimes
carries -- arc-length fraction plotted against fraction of the period.

    python tools/gen_avatar.py        # -> assets/avatar.svg
"""
import math
import os

S = 512                                    # square canvas
BG = "#05060f"
VIOLET, CYAN, GOLD = "#7c5cff", "#4cc9f0", "#ffd166"
CX = CY = S / 2.0

DUR = 14.0                                 # seconds per orbit
N = 240                                    # samples around the orbit
TS = 48                                    # keyTimes resolution
R_ORB = 168.0                              # orbital radius, in the plane
TILT = 0.42                                # cos of the viewing inclination
ROLL = math.radians(-18.0)                 # plane's roll on screen
PULL = 5200.0                              # how hard the mass drags the lattice


# ------------------------------------------------------------------- the well
def warp(px, py):
    """Pull a lattice node toward the mass, falling off as 1/distance."""
    ox, oy = px - CX, py - CY
    d = math.hypot(ox, oy) + 26.0
    pull = min(PULL / d, d * 0.62)
    return px - ox / d * pull, py - oy / d * pull


def line_d(pts):
    return "M%.1f,%.1f" % pts[0] + "".join("L%.1f,%.1f" % p for p in pts[1:])


STEP, FINE, PAD = 52.0, 13.0, 130.0
grid = []
g = -PAD
while g <= S + PAD + 0.1:
    row, col, t = [], [], -PAD
    while t <= S + PAD + 0.1:
        row.append(warp(t, g))
        col.append(warp(g, t))
        t += FINE
    grid.append(line_d(row))
    grid.append(line_d(col))
    g += STEP
GRID = ('<g fill="none" stroke="%s" stroke-width="2.4" opacity="0.5">'
        '<path d="%s"/></g>' % (VIOLET, "".join(grid)))


# ------------------------------------------------------------------ the orbit
def orbit(n=N):
    """A circle sampled at equal steps of TIME, then tilted and rolled."""
    pts = []
    c, s = math.cos(ROLL), math.sin(ROLL)
    for i in range(n):
        th = 2.0 * math.pi * i / n
        x, y = R_ORB * math.cos(th), R_ORB * math.sin(th) * TILT
        pts.append((CX + x * c - y * s, CY + x * s + y * c))
    return pts


PTS = orbit()


def path_d(pts):
    return "M%.2f,%.2f" % pts[0] + "".join("L%.2f,%.2f" % p for p in pts[1:]) + "Z"


def key_pairs(pts):
    """Map fraction-of-period to fraction-of-arc-length.

    animateMotion walks a path at constant SPEED unless told otherwise. The
    samples are uniform in time, so their cumulative arc length is exactly the
    correction needed to restore the real timing.
    """
    seg = [0.0]
    for i in range(1, len(pts)):
        seg.append(seg[-1] + math.hypot(pts[i][0] - pts[i - 1][0],
                                        pts[i][1] - pts[i - 1][1]))
    seg.append(seg[-1] + math.hypot(pts[0][0] - pts[-1][0],
                                    pts[0][1] - pts[-1][1]))
    total = seg[-1]
    kp, kt = [], []
    for i in range(TS + 1):
        f = i / TS
        x = f * len(pts)
        j = min(int(x), len(pts) - 1)
        d = seg[j] + (seg[j + 1] - seg[j]) * (x - j)
        kp.append("%.5f" % (d / total))
        kt.append("%.5f" % f)
    return ";".join(kp), ";".join(kt), total


KP, KT, PLEN = key_pairs(PTS)


def motion(begin=0.0):
    return ('<animateMotion dur="%gs" begin="%gs" repeatCount="indefinite" '
            'calcMode="linear" keyPoints="%s" keyTimes="%s">'
            '<mpath xlink:href="#trk" href="#trk"/></animateMotion>'
            % (DUR, begin, KP, KT))


# ------------------------------------------------------------------ the comet
# A single dashed stroke whose dash-offset follows the same timing, so the
# bright dash stays pinned to the body and trails behind it.
tails = []
for length, width, op in ((165.0, 5.5, 0.60), (380.0, 3.2, 0.24)):
    vals = ";".join("%.1f" % (length - PLEN * float(f)) for f in KP.split(";"))
    tails.append('<use xlink:href="#trk" href="#trk" fill="none" stroke="%s" '
                 'stroke-width="%.1f" stroke-linecap="round" opacity="%.2f" '
                 'stroke-dasharray="%g %g">'
                 '<animate attributeName="stroke-dashoffset" dur="%gs" '
                 'repeatCount="indefinite" calcMode="linear" values="%s" '
                 'keyTimes="%s"/></use>'
                 % (CYAN, width, op, length, PLEN - length, DUR, vals, KT))

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" '
       'xmlns:xlink="http://www.w3.org/1999/xlink" '
       'width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
       'aria-label="A mass bending a lattice of spacetime, with a body '
       'orbiting it.">'
       '<defs><path id="trk" d="%s"/>'
       '<radialGradient id="core">'
       '<stop offset="0" stop-color="#fff6e0" stop-opacity="0.98"/>'
       '<stop offset="0.32" stop-color="%s" stop-opacity="0.5"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '<radialGradient id="glow">'
       '<stop offset="0" stop-color="#ffffff" stop-opacity="0.95"/>'
       '<stop offset="0.3" stop-color="%s" stop-opacity="0.5"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '<radialGradient id="vig" cx="50%%" cy="47%%" r="74%%">'
       '<stop offset="0.4" stop-color="#151b3e" stop-opacity="0.75"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '</defs>'
       '<rect width="%d" height="%d" fill="%s"/>'
       '<rect width="%d" height="%d" fill="url(#vig)"/>'
       '%s'
       '<use xlink:href="#trk" href="#trk" fill="none" stroke="%s" '
       'stroke-width="2.2" opacity="0.22"/>'
       '%s'
       '<circle cx="%g" cy="%g" r="112" fill="url(#core)"/>'
       '<circle cx="%g" cy="%g" r="22" fill="#fff6e0"/>'
       '<circle cx="%g" cy="%g" r="30" fill="none" stroke="%s" '
       'stroke-width="1.6">'
       '<animate attributeName="r" values="26;62;26" dur="%gs" '
       'repeatCount="indefinite"/>'
       '<animate attributeName="opacity" values="0.55;0;0.55" dur="%gs" '
       'repeatCount="indefinite"/></circle>'
       '<g><circle r="46" fill="url(#glow)"/>'
       '<circle r="12" fill="%s"/><circle r="4.6" fill="#ffffff"/>%s</g>'
       '</svg>'
       % (S, S, S, S, path_d(PTS), GOLD, GOLD, CYAN, CYAN, BG,
          S, S, BG, S, S, GRID, CYAN, "".join(tails),
          CX, CY, CX, CY, CX, CY, GOLD, DUR / 2, DUR / 2, CYAN, motion()))

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, "assets", "avatar.svg")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(SVG)
print("wrote %s  (%.1f KB)" % (out, len(SVG) / 1024.0))
