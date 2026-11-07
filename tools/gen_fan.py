"""
Bakes three fans of double pendulums into a looping animated SVG banner.

Same constraint as the other banners: GitHub runs no JavaScript in a README,
so the motion has to live inside the SVG, and the browser re-rasterises the
whole document every frame. What that rules out here is the obvious approach.
Animating every pendulum honestly means two rotations per pendulum, each
carrying a couple of hundred baked angles -- forty-eight pendulums came to
about 80 KB of pure number and 96 live timelines. So the banner splits the job:

  * the fan is drawn, not animated.  Each pendulum's bob traces a curve; the
                 curve IS the physics, and it is a static path. Revealing it
                 with stroke-dashoffset costs one timeline and no extra bytes.
                 Honest caveat: a dash reveal is paced by arc length, not by
                 time, so the drawing speed along a curve is not the speed the
                 bob had. The shape is exact; the pacing is a flourish.
  * one pendulum per fan swings for real.  Its two angles are the integrated
                 state, sampled and baked, so the thing producing the curves
                 is on screen doing it. Three of those, not forty-eight.
  * rotation centres are translated away.  A rotate about (cx, cy) has to bake
                 "angle cx cy" into every keyframe; a rotate about the origin
                 inside a translated group bakes the angle alone, which is
                 less than half the bytes for the same motion.

Three fans rather than one because the banner is 1200x400 and a pendulum's
reach is a circle: one fan leaves two thirds of the frame empty. They start at
2.0, 2.2 and 2.4 radians -- the same rule, three places to drop it from.

Inside each fan the pendulums differ by one millionth of a radian in the first
angle, which is the entire point: they draw one line together, and then they
do not.

Run from the repository root:  python tools/gen_fan.py
"""
import math

W, H = 1200.0, 400.0
BG = "#05060f"
FANS = [(258.0, 186.0, 2.0), (600.0, 186.0, 2.2), (942.0, 186.0, 2.4)]
PER_FAN = 10          # traces per fan
L = 76.0              # rod length in pixels; two of them must fit the frame
T_END = 11.0          # seconds of physics in one loop; the split lands near 6.6 s
H_STEP = 0.002        # RK4 step
SAMPLE = 0.02         # trace sampling interval
ARM_SAMPLE = 0.05     # the live pendulum is baked coarser; it is one object
MIN_SEG = 7.0         # drop trace points closer than this, in pixels
MAX_TURN = 0.20       # ...unless the curve turns by this much, which keeps the cusps
SPLIT_PX = 2.5        # a trace branches off the shared line once it is this far from it
G = 9.81

DUR = 11.0            # loop: draw, hold, wipe back
K_ONE, K_DRAW, K_HOLD = 0.46, 0.80, 0.90


def deriv(s):
    """Both masses and both rods are 1, so the denominator is just 3 - cos 2d."""
    a, b, p, q = s
    d = a - b
    sd, cd = math.sin(d), math.cos(d)
    den = 3 - math.cos(2 * d)
    return (
        p,
        q,
        (-3 * G * math.sin(a) - G * math.sin(a - 2 * b) - 2 * sd * (q * q + p * p * cd)) / den,
        (2 * sd * (2 * p * p + 2 * G * math.cos(a) + q * q * cd)) / den,
    )


def rk4(s, h):
    k1 = deriv(s)
    k2 = deriv(tuple(s[i] + h / 2 * k1[i] for i in range(4)))
    k3 = deriv(tuple(s[i] + h / 2 * k2[i] for i in range(4)))
    k4 = deriv(tuple(s[i] + h * k3[i] for i in range(4)))
    return tuple(s[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(4))


def run(theta0, want_angles):
    """Integrate one pendulum, returning its bob trace and (optionally) its angles."""
    s = (theta0, theta0, 0.0, 0.0)
    trace, angles = [], []
    t, next_pt, next_ang = 0.0, 0.0, 0.0
    while t <= T_END + 1e-9:
        if t >= next_pt - 1e-9:
            a, b = s[0], s[1]
            trace.append((L * math.sin(a) + L * math.sin(b), L * math.cos(a) + L * math.cos(b)))
            next_pt += SAMPLE
        if want_angles and t >= next_ang - 1e-9:
            angles.append((s[0], s[1]))
            next_ang += ARM_SAMPLE
        s = rk4(s, H_STEP)
        t += H_STEP
    return trace, angles


def thin(pts):
    out, heading = [pts[0]], None
    for i, p in enumerate(pts[1:], 1):
        dx, dy = p[0] - out[-1][0], p[1] - out[-1][1]
        far = math.hypot(dx, dy) >= MIN_SEG
        turn = False
        if heading is not None and (dx or dy):
            d = abs(math.atan2(dy, dx) - heading)
            turn = min(d, 2 * math.pi - d) > MAX_TURN
        if far or turn:
            out.append(p)
            if dx or dy:
                heading = math.atan2(dy, dx)
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def n(v):
    return "%d" % round(v)


def deg(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def path_d(pts, ox, oy):
    head = "M%s %s" % (n(pts[0][0] + ox), n(pts[0][1] + oy))
    rest = " ".join("%s %s" % (n(x + ox), n(y + oy)) for x, y in pts[1:])
    return head + "L" + rest


def length(pts):
    return sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
               for i in range(1, len(pts)))


def mix(c0, c1, t):
    return "#%02x%02x%02x" % tuple(round(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))


BLOOD, ROSE, CRIMSON = (158, 19, 48), (255, 107, 125), (255, 45, 70)
parts = []

for fi, (px, py, theta0) in enumerate(FANS):
    traces = []
    angles = []
    for i in range(PER_FAN):
        tr, ang = run(theta0 + i * 1e-6, i == 0)
        traces.append(tr)
        if ang:
            angles = ang

    # Every pendulum in a fan draws the same line until it does not, and
    # storing that line twelve times over is most of the file. Find where each
    # one leaves the first, keep a single copy of the shared opening, branch
    # only after it.
    base = traces[0]
    split = len(base)
    for pts in traces[1:]:
        k = 0
        while k < min(len(pts), len(base)) and                 math.hypot(pts[k][0] - base[k][0], pts[k][1] - base[k][1]) < SPLIT_PX:
            k += 1
        split = min(split, k)
    shared = thin(base[:max(2, split)])
    sl = length(shared)
    parts.append(
        '<path d="%s" fill="none" stroke="%s" stroke-opacity="0.7" stroke-width="1.2" '
        'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="%s" '
        'stroke-dashoffset="%s"><animate attributeName="stroke-dashoffset" dur="%ss" '
        'repeatCount="indefinite" values="%s;0;0;%s" keyTimes="0;%s;%s;1"/></path>'
        % (path_d(shared, px, py), mix(BLOOD, ROSE, 0.25), n(sl), n(sl), n(DUR),
           n(sl), n(sl), K_ONE, K_HOLD))

    for i, pts in enumerate(traces):
        tail = thin(pts[max(0, split - 1):])
        if len(tail) < 2:
            continue
        ln = length(tail)
        col = mix(BLOOD, ROSE, i / max(1, PER_FAN - 1))
        # wait while the shared line draws, then branch, then wipe back with it
        parts.append(
            '<path d="%s" fill="none" stroke="%s" stroke-opacity="0.55" stroke-width="1" '
            'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="%s" '
            'stroke-dashoffset="%s"><animate attributeName="stroke-dashoffset" dur="%ss" '
            'repeatCount="indefinite" values="%s;%s;0;0;%s" keyTimes="0;%s;%s;%s;1"/></path>'
            % (path_d(tail, px, py), col, n(ln), n(ln), n(DUR), n(ln), n(ln), n(ln),
               K_ONE, K_DRAW, K_HOLD))

    # The one that swings. Angles run forward over the draw, hold at the end,
    # then rewind coarsely while the fan wipes back.
    fwd = angles
    back = list(reversed(fwd))[::5]
    a1 = ";".join(deg(-math.degrees(a)) for a, _ in fwd) + ";" + deg(-math.degrees(fwd[-1][0]))
    a2 = ";".join(deg(-math.degrees(b - a)) for a, b in fwd) + ";" + \
         deg(-math.degrees(fwd[-1][1] - fwd[-1][0]))
    a1 += ";" + ";".join(deg(-math.degrees(a)) for a, _ in back)
    a2 += ";" + ";".join(deg(-math.degrees(b - a)) for a, b in back)
    nf, nb = len(fwd), len(back)
    kt = [K_DRAW * i / (nf - 1) for i in range(nf)] + [K_HOLD] + \
         [K_HOLD + (1 - K_HOLD) * (i + 1) / nb for i in range(nb)]
    keys = ";".join(n(round(k, 4)) if k not in (0.0, 1.0) else ("0" if k == 0.0 else "1")
                    for k in kt)
    keys = ";".join(("%.4f" % k).rstrip("0").rstrip(".") or "0" for k in kt)
    anim = ('<animateTransform attributeName="transform" type="rotate" dur="%ss" '
            'repeatCount="indefinite" values="%s" keyTimes="%s"/>')
    parts.append(
        '<g transform="translate(%s,%s)"><g>%s'
        '<line x1="0" y1="0" x2="0" y2="%s" stroke="%s" stroke-opacity="0.85" stroke-width="1.6"/>'
        '<g transform="translate(0,%s)"><g>%s'
        '<line x1="0" y1="0" x2="0" y2="%s" stroke="%s" stroke-opacity="0.85" stroke-width="1.6"/>'
        '<circle cx="0" cy="%s" r="3.2" fill="#ff6b7d"/></g></g></g></g>'
        % (n(px), n(py), anim % (n(DUR), a1, keys), n(L), mix(CRIMSON, ROSE, 0.2),
           n(L), anim % (n(DUR), a2, keys), n(L), mix(CRIMSON, ROSE, 0.5), n(L)))
    parts.append('<circle cx="%s" cy="%s" r="2.6" fill="#e8ecff" fill-opacity="0.9"/>'
                 % (n(px), n(py)))

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" '
       'height="400" role="img" aria-label="Three fans of double pendulums. Each fan starts '
       'sixteen pendulums a millionth of a radian apart, they trace one line together, and '
       'then the curves separate and fill the frame.">\n'
       '<rect width="1200" height="400" fill="%s"/>\n%s\n</svg>\n' % (BG, "\n".join(parts)))

with open("assets/fan.svg", "w", encoding="utf-8") as fh:
    fh.write(svg)
print("wrote assets/fan.svg  %.1f KB" % (len(svg.encode("utf-8")) / 1024))
