"""
Bakes REAL orbital mechanics into a looping animated SVG banner.

  * centrepiece : the Chenciner-Montgomery figure-eight choreography, an exact
                  periodic solution of the equal-mass three-body problem,
                  integrated here with RK4.
  * flanks      : true Keplerian two-body orbits, obtained by solving Kepler's
                  equation M = E - e*sin(E) with Newton-Raphson, so the bodies
                  really do sweep equal areas in equal times.

Motion is emitted as <animateMotion> over an <mpath>, with keyPoints/keyTimes
carrying the physical timing (arc-length fraction vs. time fraction). Trails are
the same animation replayed at negative begin offsets.
"""
import math

W, H = 1200.0, 380.0
BG = "#05060f"
VIOLET = "#7c5cff"
CYAN = "#4cc9f0"
GOLD = "#ffd166"

N8 = 260     # path vertices for the figure-eight (geometry, shared once)
NK = 160     # path vertices per Kepler ellipse
TS = 64      # samples of the timing curve (duplicated per trail ghost)
LOOP = 18.0  # seconds mapped onto one figure-eight period

# ------------------------------------------------------------------ figure 8
# Canonical initial conditions (G = 1, m = 1 for all three bodies).
_x, _y = 0.97000436, -0.24308753
_vx, _vy = -0.93240737, -0.86473146
P8 = 6.32591398292621
INIT = [(-_x, -_y, -_vx / 2, -_vy / 2),
        (_x, _y, -_vx / 2, -_vy / 2),
        (0.0, 0.0, _vx, _vy)]


def accel(s):
    """Newtonian gravity, G = m = 1, for the three-body state vector."""
    a = [0.0] * 6
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            dx = s[4 * j] - s[4 * i]
            dy = s[4 * j + 1] - s[4 * i + 1]
            r = math.hypot(dx, dy)
            f = 1.0 / (r * r * r)
            a[2 * i] += f * dx
            a[2 * i + 1] += f * dy
    return a


def deriv(s):
    a = accel(s)
    d = [0.0] * 12
    for i in range(3):
        d[4 * i] = s[4 * i + 2]
        d[4 * i + 1] = s[4 * i + 3]
        d[4 * i + 2] = a[2 * i]
        d[4 * i + 3] = a[2 * i + 1]
    return d


def rk4(s, dt):
    k1 = deriv(s)
    k2 = deriv([s[i] + 0.5 * dt * k1[i] for i in range(12)])
    k3 = deriv([s[i] + 0.5 * dt * k2[i] for i in range(12)])
    k4 = deriv([s[i] + dt * k3[i] for i in range(12)])
    return [s[i] + dt / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
            for i in range(12)]


def figure_eight():
    s = [v for b in INIT for v in b]
    sub = 40                       # RK4 substeps between emitted samples
    dt = P8 / (N8 * sub)
    tracks = [[] for _ in range(3)]
    for _ in range(N8):
        for i in range(3):
            tracks[i].append((s[4 * i], s[4 * i + 1]))
        for _ in range(sub):
            s = rk4(s, dt)
    return tracks


# -------------------------------------------------------------------- kepler
def kepler(a, e, phase, tilt, n=NK):
    """Sample one full Keplerian ellipse at equal steps of time, not angle."""
    pts = []
    for i in range(n):
        M = 2 * math.pi * i / n + phase
        E = M
        for _ in range(60):        # Newton-Raphson on M = E - e*sin(E)
            E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        x = a * (math.cos(E) - e)
        y = a * math.sqrt(1 - e * e) * math.sin(E)
        c, s = math.cos(tilt), math.sin(tilt)
        pts.append((x * c - y * s, x * s + y * c))
    return pts


# ---------------------------------------------------------------- svg output
def fit(tracks, cx, cy, half_w, flip_y=True):
    """Scale a set of tracks about their common centre to a target half-width."""
    xs = [p[0] for t in tracks for p in t]
    ys = [p[1] for t in tracks for p in t]
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max((max(xs) - min(xs)) / 2, 1e-9)
    k = half_w / span
    sy = -k if flip_y else k
    return [[(cx + (x - mx) * k, cy + (y - my) * sy) for x, y in t]
            for t in tracks]


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


def emit_system(pts, pid, colour, name, dur, tails, r_head=4.4, guide_op=0.10):
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
    for length, width, op in tails:
        # dash leading edge sits on the body: offset = length - s(t)
        vals = ";".join("%.1f" % (length - PL * float(f))
                        for f in kp.split(";"))
        art.append('<use xlink:href="#%s" href="#%s" fill="none" stroke="%s" '
                   'stroke-width="%.1f" stroke-linecap="round" opacity="%.3f" '
                   'stroke-dasharray="%g %g">'
                   '<animate attributeName="stroke-dashoffset" dur="%gs" '
                   'repeatCount="indefinite" calcMode="linear" values="%s" '
                   'keyTimes="%s"/></use>'
                   % (pid, pid, colour, width, op, length, PL - length,
                      dur, vals, kt))
    art.append('<g><circle r="%.1f" fill="url(#halo-%s)"/>'
               '<circle r="%.2f" fill="%s" opacity="0.9"/>'
               '<circle r="%.2f" fill="#ffffff"/>%s</g>'
               % (r_head * 4.2, name, r_head, colour, r_head * 0.44,
                  motion(pid, dur, 0)))


# ---- centrepiece: the figure-eight choreography ----------------------------
for pts, col, name in zip(fit(figure_eight(), W / 2, H / 2 - 4, 245),
                          (VIOLET, CYAN, GOLD), ("violet", "cyan", "gold")):
    emit_system(pts, "%s8" % name, col, name, LOOP,
                tails=((70, 3.4, 0.55), (190, 2.1, 0.26), (360, 1.2, 0.12)),
                r_head=5.0, guide_op=0.13)

# ---- flanks: Keplerian satellites in 1:2:3 resonance -----------------------
SATS = [(118, 0.42, 0.0, 0.35, VIOLET, "violet", LOOP),
        (82, 0.55, 2.1, -0.62, CYAN, "cyan", LOOP / 2),
        (52, 0.18, 4.0, 1.25, GOLD, "gold", LOOP / 3)]

for side, (cx, sign) in enumerate(((196.0, 1), (1004.0, -1))):
    tracks = fit([kepler(a, e, ph, tilt * sign)
                  for a, e, ph, tilt, _, _, _ in SATS], cx, H / 2 - 4, 150)
    for pts, (_, _, _, _, col, name, dur) in zip(tracks, SATS):
        emit_system(pts, "%sk%d" % (name, side), col, name, dur,
                    tails=((90, 2.4, 0.5), (230, 1.5, 0.22)),
                    r_head=3.4, guide_op=0.09)
    art.append('<g transform="translate(%.1f %.1f)">'
               '<circle r="34" fill="url(#halo-core)"/>'
               '<circle r="6.5" fill="#fff6e0"/>'
               '<circle r="10" fill="none" stroke="%s" stroke-width="0.8">'
               '<animate attributeName="r" values="9;16;9" dur="4s" '
               'repeatCount="indefinite"/>'
               '<animate attributeName="opacity" values="0.55;0;0.55" dur="4s" '
               'repeatCount="indefinite"/></circle></g>'
               % (cx, H / 2 - 4, GOLD))

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


svg = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="Animated simulation of the figure-eight three-body choreography, flanked by two Keplerian orbital systems on a starfield.">
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
                          ("gold", GOLD), ("core", GOLD))),
           defs="".join(defs), stars="".join(stars),
           guides="".join(guides), art="".join(art))

out = r"C:\Users\aksha\OneDrive\Documents\akshatdalakoti-stack\assets\hero.svg"
with open(out, "w", encoding="utf-8") as f:
    f.write(svg)
print("wrote %s  (%.1f KB, %d animated bodies)"
      % (out, len(svg) / 1024, len(KP)))
