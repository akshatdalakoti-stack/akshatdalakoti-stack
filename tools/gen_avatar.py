"""
Bakes the profile mark into a looping animated SVG: a body on a tilted circular
orbit around a monogram.

Same constraint as the banner -- README images run inside <img>, where no
JavaScript executes -- so the motion is pre-computed and carried by SMIL.

The orbit is a circle in its own plane, viewed at an inclination, so on screen
it reads as an ellipse. The body moves at a constant angular rate in that plane,
which is NOT constant speed along the drawn ellipse: it appears to slow at the
turns and hurry through the middle. That timing is what keyPoints/keyTimes
carries -- arc-length fraction plotted against fraction of the period.

The monogram is drawn as geometry rather than text so it renders identically
everywhere, with no dependency on a font being installed.

    python tools/gen_avatar.py        # -> assets/avatar.svg
"""
import math
import os

S = 512                                    # square canvas
BG = "#05060f"
VIOLET, CYAN, GOLD = "#7c5cff", "#4cc9f0", "#ffd166"

DUR = 12.0                                 # seconds per orbit
N = 240                                    # samples around the orbit
TS = 48                                    # keyTimes resolution
R_ORB = 196.0                              # orbital radius, in the plane
TILT = 0.39                                # cos of the viewing inclination
ROLL = math.radians(-24.0)                 # plane's roll on screen
CX = CY = S / 2.0


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


def path_d(pts, close=True):
    return ("M%.2f,%.2f" % pts[0]
            + "".join("L%.2f,%.2f" % p for p in pts[1:])
            + ("Z" if close else ""))


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
        x = f * (len(pts))
        j = min(int(x), len(pts) - 1)
        frac = x - j
        d = seg[j] + (seg[j + 1] - seg[j]) * frac
        kp.append("%.5f" % (d / total))
        kt.append("%.5f" % f)
    return ";".join(kp), ";".join(kt), total


KP, KT, PLEN = key_pairs(PTS)


def motion(begin=0.0):
    return ('<animateMotion dur="%gs" begin="%gs" repeatCount="indefinite" '
            'calcMode="linear" keyPoints="%s" keyTimes="%s">'
            '<mpath xlink:href="#trk" href="#trk"/></animateMotion>'
            % (DUR, begin, KP, KT))


# --------------------------------------------------------------- the monogram
# An "A" as two legs and a crossbar, so it needs no font to be installed.
APEX = (256.0, 152.0)
FOOT_L, FOOT_R = (166.0, 366.0), (346.0, 366.0)
BAR_Y = 302.0
_t = (BAR_Y - APEX[1]) / (FOOT_L[1] - APEX[1])
BAR_L = (APEX[0] + (FOOT_L[0] - APEX[0]) * _t, BAR_Y)
BAR_R = (APEX[0] + (FOOT_R[0] - APEX[0]) * _t, BAR_Y)

MONOGRAM = ('<g fill="none" stroke="%s" stroke-width="27" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f"/>'
            '<path d="M%.1f,%.1f L%.1f,%.1f"/></g>'
            % (GOLD, FOOT_L[0], FOOT_L[1], APEX[0], APEX[1],
               FOOT_R[0], FOOT_R[1], BAR_L[0], BAR_L[1], BAR_R[0], BAR_R[1]))

# ------------------------------------------------------------------ the comet
# A single dashed stroke whose dash-offset follows the same timing, so the
# bright dash stays pinned to the body and trails behind it.
TAILS = ((150.0, 5.0, 0.55), (360.0, 3.0, 0.22))
tail_svg = []
for length, width, op in TAILS:
    vals = ";".join("%.1f" % (length - PLEN * float(f)) for f in KP.split(";"))
    tail_svg.append('<use xlink:href="#trk" href="#trk" fill="none" '
                    'stroke="%s" stroke-width="%.1f" stroke-linecap="round" '
                    'opacity="%.2f" stroke-dasharray="%g %g">'
                    '<animate attributeName="stroke-dashoffset" dur="%gs" '
                    'repeatCount="indefinite" calcMode="linear" values="%s" '
                    'keyTimes="%s"/></use>'
                    % (CYAN, width, op, length, PLEN - length, DUR, vals, KT))

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" '
       'xmlns:xlink="http://www.w3.org/1999/xlink" '
       'width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
       'aria-label="A monogram A with a body orbiting it on a tilted ellipse.">'
       '<defs>'
       '<path id="trk" d="%s"/>'
       '<radialGradient id="glow">'
       '<stop offset="0" stop-color="#ffffff" stop-opacity="0.95"/>'
       '<stop offset="0.3" stop-color="%s" stop-opacity="0.5"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '<radialGradient id="vig" cx="50%%" cy="46%%" r="74%%">'
       '<stop offset="0.4" stop-color="#161c40" stop-opacity="0.8"/>'
       '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
       '</defs>'
       '<rect width="%d" height="%d" fill="%s"/>'
       '<rect width="%d" height="%d" fill="url(#vig)"/>'
       '<use xlink:href="#trk" href="#trk" fill="none" stroke="%s" '
       'stroke-width="2.5" opacity="0.20"/>'
       '%s'
       '%s'
       '<g><circle r="52" fill="url(#glow)"/>'
       '<circle r="13" fill="%s"/><circle r="5" fill="#ffffff"/>%s</g>'
       '</svg>'
       % (S, S, S, S, path_d(PTS), CYAN, CYAN, BG, S, S, BG, S, S,
          VIOLET, MONOGRAM, "".join(tail_svg), CYAN, motion()))

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, "assets", "avatar.svg")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(SVG)
print("wrote %s  (%.1f KB)" % (out, len(SVG) / 1024.0))
