"""
Bakes a gravitational scene into a looping animated SVG banner.

GitHub renders README images inside <img>, where no JavaScript runs -- so the
motion here is pre-computed rather than simulated live:

  * the sheet   : a lattice pulled toward the star, falling off as 1/distance.
                  Static, because the only mass heavy enough to bend it visibly
                  does not move.
  * the planet  : a circular orbit, seen with its plane tilted away from us so
                  it reads as an ellipse.
  * the trojans : L4 and L5 sit sixty degrees ahead of and behind the planet on
                  the very same orbit, so they cost one path and a phase offset
                  per body rather than an orbit each.
  * the rosette : a Schwarzschild orbit, integrated with RK4, whose relativistic
                  coefficient is tuned by bisection until the apsidal advance is
                  exactly 2*pi/5 -- so it closes after five radial periods and
                  the loop is seamless.

Motion rides <animateMotion> over an <mpath>, with keyPoints/keyTimes carrying
the physical timing (arc-length fraction against fraction of period). Comet
tails are a single dashed stroke whose dash-offset follows that same timing.
"""
import math

W, H = 1200.0, 380.0
BG = "#05060f"
VIOLET = "#7c5cff"
CYAN = "#4cc9f0"
GOLD = "#ffd166"
PINK = "#ff8fd1"

N8 = 260     # path vertices for the figure-eight (geometry, shared once)
NK = 160     # path vertices per Kepler ellipse
TS = 64      # samples of the timing curve (duplicated per trail ghost)
LOOP = 18.0  # seconds mapped onto one figure-eight period

# ------------------------------------------------------- schwarzschild orbit
# A Schwarzschild orbit obeys d2u/dphi2 + u = GM/h^2 + 3GM u^2/c^2, i.e. an
# extra 1/r^4 term in the radial acceleration. It precesses, so a generic orbit
# never closes -- useless for a seamless loop. But if the apsidal advance per
# radial period is exactly 2*pi*p/q, the path closes after q radial periods and
# draws a q-petal rosette. So we bisect the relativistic coefficient until the
# advance lands precisely on that rational.
def _pn_step(st, dt, h2, eps):
    def d(u):
        r2 = u[0] * u[0] + u[1] * u[1]
        r = math.sqrt(r2)
        f = -(1.0 / (r2 * r)) - eps * h2 / (r2 * r2 * r)
        return [u[2], u[3], f * u[0], f * u[1]]
    k1 = d(st)
    k2 = d([st[i] + 0.5 * dt * k1[i] for i in range(4)])
    k3 = d([st[i] + 0.5 * dt * k2[i] for i in range(4)])
    k4 = d([st[i] + dt * k3[i] for i in range(4)])
    return [st[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
            for i in range(4)]


def _radial_period(eps, e, dt=2e-4):
    """One periapsis-to-periapsis pass: returns (period, angle swept)."""
    v0 = math.sqrt(1.0 + e)
    st = [1.0, 0.0, 0.0, v0]
    h2 = v0 * v0
    t, phi, prev_vr = 0.0, 0.0, 0.0
    px, py = st[0], st[1]
    while t < 400:
        st = _pn_step(st, dt, h2, eps)
        t += dt
        cx, cy = st[0], st[1]
        dphi = math.atan2(px * cy - py * cx, px * cx + py * cy)
        phi += dphi
        px, py = cx, cy
        r = math.hypot(cx, cy)
        vr = (cx * st[2] + cy * st[3]) / r
        if t > dt * 10 and prev_vr < 0 <= vr:
            frac = -prev_vr / (vr - prev_vr)
            return t - dt * (1 - frac), phi - dphi * (1 - frac)
        prev_vr = vr
    raise RuntimeError("no periapsis found")


def rosette(q=5, p=1, e=0.55, n=N8):
    """A closed q-petal relativistic rosette, sampled at equal steps of time."""
    target = 2 * math.pi * (1 + p / q)
    lo, hi = 0.0, 0.02
    while _radial_period(hi, e)[1] < target:
        hi *= 1.6
    for _ in range(70):
        mid = (lo + hi) / 2
        if _radial_period(mid, e)[1] < target:
            lo = mid
        else:
            hi = mid
    eps = (lo + hi) / 2
    period, _ = _radial_period(eps, e)
    v0 = math.sqrt(1.0 + e)
    st = [1.0, 0.0, 0.0, v0]
    h2 = v0 * v0
    sub = 60
    dt = q * period / (n * sub)
    pts = []
    for _ in range(n):
        pts.append((st[0], st[1]))
        for _ in range(sub):
            st = _pn_step(st, dt, h2, eps)
    closure = math.hypot(st[0] - 1.0, st[1])
    assert closure < 1e-6, "rosette failed to close: %.2e" % closure
    return pts, eps, closure


# ---------------------------------------------------------------- svg output
def path_d(pts):
    d = "M%.1f,%.1f" % pts[0]
    d += "".join("L%.1f,%.1f" % p for p in pts[1:])
    return d + "Z"


def key_pairs(pts, samples=TS):
    """The timing curve: arc-length fraction travelled vs. fraction of period.

    The path geometry is kept at full resolution and shared by every ghost, but
    this curve is smooth and monotonic, so a coarse piecewise-linear sampling of
    it is visually exact -- and it is what gets duplicated per trail element.
    """
    closed = list(pts) + [pts[0]]
    cum, total = [0.0], 0.0
    for i in range(1, len(closed)):
        total += math.dist(closed[i - 1], closed[i])
        cum.append(total)
    n = len(closed) - 1
    kp, kt = [], []
    for j in range(samples + 1):
        t = j / samples
        f = t * n
        i0 = min(int(f), n - 1)
        c = cum[i0] + (cum[i0 + 1] - cum[i0]) * (f - i0)
        kp.append("%.4f" % (c / total))
        kt.append("%.4f" % t)
    return ";".join(kp), ";".join(kt)


KP, KT = {}, {}
defs, guides, art = [], [], []


def motion(pid, dur, begin):
    return ('<animateMotion dur="%gs" begin="%gs" repeatCount="indefinite" '
            'calcMode="linear" keyPoints="%s" keyTimes="%s">'
            '<mpath xlink:href="#%s" href="#%s"/></animateMotion>'
            % (dur, begin, KP[pid], KT[pid], pid, pid))


PL = 1000.0   # forced pathLength, so dash units are per-mille of the orbit


def emit_system(pts, pid, colour, name, dur, tails, r_head=4.4,
                guide_op=0.10, riders=None):
    """One orbiting body: faint guide ellipse, comet tail, glowing head.

    The tail is a single dashed stroke whose dash is exactly as long as the
    desired tail and whose gap fills the rest of the closed orbit, so the
    pattern wraps seamlessly. Animating stroke-dashoffset along the SAME
    arc-length timing curve as the head keeps the tail physically correct --
    it stretches at periapsis and bunches up at apoapsis -- for three elements
    instead of twenty ghost dots.
    """
    kp, kt = key_pairs(pts)
    KP[pid], KT[pid] = kp, kt
    defs.append('<path id="%s" pathLength="%g" d="%s"/>'
                % (pid, PL, path_d(pts)))
    guides.append('<use xlink:href="#%s" href="#%s" fill="none" stroke="%s" '
                  'stroke-width="1" opacity="%.2f"/>'
                  % (pid, pid, colour, guide_op))
    # several bodies may ride the same orbit, offset in phase
    for phase, rc, rn in (riders or ((0.0, colour, name),)):
        off = -phase * dur
        for length, width, op in tails:
            # dash leading edge sits on the body: offset = length - s(t)
            vals = ";".join("%.1f" % (length - PL * float(f))
                            for f in kp.split(";"))
            art.append('<use xlink:href="#%s" href="#%s" fill="none" '
                       'stroke="%s" stroke-width="%.1f" stroke-linecap="round" '
                       'opacity="%.3f" stroke-dasharray="%g %g">'
                       '<animate attributeName="stroke-dashoffset" dur="%gs" '
                       'begin="%gs" repeatCount="indefinite" calcMode="linear" '
                       'values="%s" keyTimes="%s"/></use>'
                       % (pid, pid, rc, width, op, length, PL - length,
                          dur, off, vals, kt))
        art.append('<g><circle r="%.1f" fill="url(#halo-%s)"/>'
                   '<circle r="%.2f" fill="%s" opacity="0.9"/>'
                   '<circle r="%.2f" fill="#ffffff"/>%s</g>'
                   % (r_head * 4.2, rn, r_head, rc, r_head * 0.44,
                      motion(pid, dur, off)))


# ---------------------------------------------------------------- the scene
# One star, seen with its orbital plane tilted away from us, sitting at the
# bottom of its own gravity well.
CX, CY = W / 2, 186.0
TILT = 0.36          # cos of the viewing inclination: a circle reads as an ellipse
R_ORB = 262.0        # planet's orbital radius, in the plane
PULL = 4300.0        # how hard the star drags the lattice inward


def project(x, y):
    """Plane coordinates -> screen. The orbital plane is tilted away from us,
    so every circular orbit reads as an ellipse."""
    return CX + x, CY + y * TILT


def warp(px, py):
    """Pull a lattice node toward the star, falling off as 1/distance. Only the
    sheet is bent; the bodies stay where they actually are."""
    ox, oy = px - CX, py - CY
    d = math.hypot(ox, oy) + 26.0
    pull = min(PULL / d, d * 0.62)
    return px - ox / d * pull, py - oy / d * pull


# ---- the sheet -------------------------------------------------------------
# Static, because the only mass heavy enough to bend it visibly does not move.
GRID = []
GX, GY = 690.0, 620.0
GSTEP_X = 56.0                  # screen spacing directly
GSTEP_Y = GSTEP_X / TILT        # foreshortened to the same spacing on screen
GFINE_X, GFINE_Y = 18.0, 26.0


def _grid_line(pts):
    d = "M%.1f,%.1f" % pts[0] + "".join("L%.1f,%.1f" % q for q in pts[1:])
    GRID.append('<path d="%s"/>' % d)


y = -GY
while y <= GY + 0.1:
    line, x = [], -GX
    while x <= GX + 0.1:
        line.append(warp(*project(x, y)))
        x += GFINE_X
    _grid_line(line)
    y += GSTEP_Y
x = -GX
while x <= GX + 0.1:
    line, y = [], -GY
    while y <= GY + 0.1:
        line.append(warp(*project(x, y)))
        y += GFINE_Y
    _grid_line(line)
    x += GSTEP_X

guides.append('<g fill="none" stroke="%s" stroke-width="0.8" opacity="0.23">'
              '%s</g>' % (VIOLET, "".join(GRID)))

# ---- the planet's orbit, shared by everything that rides it ----------------
P_DUR = 24.0
ORBIT = [project(R_ORB * math.cos(2 * math.pi * i / NK),
                 R_ORB * math.sin(2 * math.pi * i / NK)) for i in range(NK)]

emit_system(ORBIT, "orb", CYAN, "cyan", P_DUR,
            tails=((70, 2.4, 0.40), (210, 1.4, 0.16)),
            r_head=4.6, guide_op=0.16)

# ---- trojans ---------------------------------------------------------------
# L4 and L5 sit sixty degrees ahead of and behind the planet on the very same
# orbit, so one path and a phase offset per body is all this costs.
TROJ = []
for lead in (1, -1):
    for i in range(23):
        spread = (rnd_spread := ((i * 7 % 23) / 23.0 - 0.5)) * 0.115
        phase = (lead * 60.0 / 360.0) + spread
        size = 1.15 + ((i * 5 % 23) / 23.0) * 1.05
        op = 0.45 + ((i * 11 % 23) / 23.0) * 0.42
        col = VIOLET if lead > 0 else PINK
        TROJ.append('<circle r="%.2f" fill="%s" opacity="%.2f">%s</circle>'
                    % (size, col, op, motion("orb", P_DUR, -phase * P_DUR)))
art.append('<g>%s</g>' % "".join(TROJ))

# ---- an inner body on a relativistic rosette -------------------------------
ROS_PTS, ROS_EPS, ROS_ERR = rosette(q=5, e=0.55)
_rs = 138.0 / max(math.hypot(*q) for q in ROS_PTS)
emit_system([project(x * _rs, y * _rs) for x, y in ROS_PTS],
            "rose", GOLD, "gold", 19.0,
            tails=((55, 2.2, 0.42), (165, 1.4, 0.20), (470, 0.8, 0.09)),
            r_head=3.2, guide_op=0.10,
            riders=((0.0, GOLD, "gold"),))

# ---- the star, at the bottom of its own well -------------------------------
_sx, _sy = project(0.0, 0.0)
art.append('<g transform="translate(%.1f %.1f)">'
           '<circle r="62" fill="url(#halo-core)"/>'
           '<circle r="9" fill="#fff6e0"/>'
           '<circle r="13" fill="none" stroke="%s" stroke-width="0.9">'
           '<animate attributeName="r" values="12;30;12" dur="6s" '
           'repeatCount="indefinite"/>'
           '<animate attributeName="opacity" values="0.5;0;0.5" dur="6s" '
           'repeatCount="indefinite"/></circle></g>' % (_sx, _sy, GOLD))

# ---- starfield -------------------------------------------------------------
_seed = 1234567


def rand():
    global _seed
    _seed = (1103515245 * _seed + 12345) % (1 << 31)
    return _seed / (1 << 31)


stars = []
for _ in range(170):
    x, y, r = rand() * W, rand() * H, 0.35 + rand() * 1.15
    o, d = 0.25 + rand() * 0.55, 2.5 + rand() * 5.0
    stars.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#dfe8ff" '
                 'opacity="%.2f" style="animation:tw %.2fs ease-in-out %.2fs '
                 'infinite"/>' % (x, y, r, o, d, rand() * d))


def halo(n, c):
    return ('<radialGradient id="halo-%s"><stop offset="0" stop-color="%s" '
            'stop-opacity="0.8"/><stop offset="0.4" stop-color="%s" '
            'stop-opacity="0.2"/><stop offset="1" stop-color="%s" '
            'stop-opacity="0"/></radialGradient>' % (n, c, c, c))


svg = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="A star bending a lattice of spacetime, orbited by a planet with trojan swarms at its L4 and L5 points, and an inner body tracing a relativistic rosette.">
<style>
  @keyframes tw {{ 0%,100% {{ opacity:.18 }} 50% {{ opacity:.9 }} }}
  @keyframes drift {{ 0%,100% {{ transform:translate(0,0) }} 50% {{ transform:translate(-16px,9px) }} }}
  .neb {{ animation: drift 26s ease-in-out infinite }}
</style>
<defs>
  {halos}
  <radialGradient id="neb1"><stop offset="0" stop-color="{v}" stop-opacity="0.30"/><stop offset="1" stop-color="{v}" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb2"><stop offset="0" stop-color="{c}" stop-opacity="0.22"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb3"><stop offset="0" stop-color="{g}" stop-opacity="0.14"/><stop offset="1" stop-color="{g}" stop-opacity="0"/></radialGradient>
  <linearGradient id="vign" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0.4"/><stop offset="0.5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.45"/></linearGradient>
  {defs}
</defs>
<rect width="{w:.0f}" height="{h:.0f}" fill="{bg}"/>
<g class="neb">
  <ellipse cx="600" cy="180" rx="470" ry="215" fill="url(#neb1)"/>
  <ellipse cx="240" cy="250" rx="330" ry="190" fill="url(#neb2)"/>
  <ellipse cx="980" cy="130" rx="300" ry="170" fill="url(#neb3)"/>
</g>
<g>{stars}</g>
<g>{guides}</g>
<g>{art}</g>
<rect width="{w:.0f}" height="{h:.0f}" fill="url(#vign)"/>
</svg>
""".format(w=W, h=H, bg=BG, v=VIOLET, c=CYAN, g=GOLD,
           halos="".join(halo(n, c) for n, c in
                         (("violet", VIOLET), ("cyan", CYAN),
                          ("gold", GOLD), ("pink", PINK),
                          ("core", GOLD))),
           defs="".join(defs), stars="".join(stars),
           guides="".join(guides), art="".join(art))

out = r"C:\Users\aksha\OneDrive\Documents\akshatdalakoti-stack\assets\hero.svg"
with open(out, "w", encoding="utf-8") as f:
    f.write(svg)
print("wrote %s  (%.1f KB, %d animated bodies)"
      % (out, len(svg) / 1024, len(KP)))
