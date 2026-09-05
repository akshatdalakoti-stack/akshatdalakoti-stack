"""
Bakes the skull into a looping animated SVG banner of real characters.

GitHub renders README images inside <img>, where no JavaScript runs -- so the
live version in docs/index.html cannot be embedded directly. What works there
is CSS animation inside the SVG itself, so this pre-renders a short cycle of
frames and flicks between them:

  * geometry  : the same signed distance function the page raymarches, kept in
                sync by hand -- braincase and facial mass blended, brow ridge
                and zygomatic arches added, orbits and nasal aperture carved
                back out, a dental arch repeated around a polar angle, and a
                mandible hinged at the condyles.
  * shading   : a near-frontal key plus five-tap ambient occlusion. A hard side
                light would break the symmetry the skull reads by.
  * motion    : yaw sways as a sine, so the loop closes seamlessly and never
                reaches the straight profile, which is the least legible angle.
  * animation : one @keyframes shared by every frame group, each offset by its
                own animation-delay. Cheaper than a keyframes block per frame.

Every row is pinned with textLength/lengthAdjust so the grid stays square
whatever monospace font the viewer happens to resolve -- without that, a font
whose advance width is not exactly 0.6em shears the picture apart.

Needs numpy. Run from the repository root:  python tools/gen_hero.py
"""
import numpy as np

# ----------------------------------------------------------------- geometry
JAW = 0.10


def nrm(v):
    return np.sqrt((v * v).sum(-1))


def sdEllipsoid(p, c, r):
    q = (p - c) / r
    k0 = nrm(q)
    k1 = nrm((p - c) / (r * r))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def sdCapsule(p, a, b, r):
    pa = p - a
    ba = np.asarray(b, float) - np.asarray(a, float)
    h = np.clip((pa * ba).sum(-1) / ba.dot(ba), 0.0, 1.0)[..., None]
    return nrm(pa - ba * h) - r


def sdBox(p, b):
    q = np.abs(p) - b
    return nrm(np.maximum(q, 0.0)) + np.minimum(q.max(-1), 0.0)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    h = np.clip(0.5 - 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h + k * h * (1.0 - h)


def ssub(a, b, k):
    return smax(a, -b, k)


def rotX(p, a):
    s, c = np.sin(a), np.cos(a)
    return np.stack([p[..., 0],
                     c * p[..., 1] - s * p[..., 2],
                     s * p[..., 1] + c * p[..., 2]], -1)


def arch(p, yc, zc, rad, halfH, count, span):
    """One tooth, repeated around the polar angle and clipped to the front arc."""
    q = p - np.array([0.0, yc, zc])
    a = np.arctan2(q[..., 0], q[..., 2])
    r = np.hypot(q[..., 0], q[..., 2])
    seg = 2 * np.pi / count
    a2 = np.mod(a + seg * 0.5, seg) - seg * 0.5
    d = sdBox(np.stack([a2 * r, q[..., 1], r - rad], -1),
              np.array([0.028, halfH, 0.030])) - 0.013
    return np.maximum(d, (np.abs(a) - span) * 0.55)


def map_(p):
    m = np.stack([np.abs(p[..., 0]), p[..., 1], p[..., 2]], -1)

    d = sdEllipsoid(p, np.array([0.0, 0.24, -0.10]), np.array([0.575, 0.565, 0.700]))
    d = ssub(d, sdEllipsoid(p, np.array([0.0, -1.02, -0.40]),
                            np.array([0.95, 0.66, 0.72])), 0.20)
    d = smin(d, sdEllipsoid(p, np.array([0.0, -0.25, 0.31]),
                            np.array([0.405, 0.480, 0.385])), 0.20)
    d = smin(d, sdCapsule(p, [-0.34, 0.19, 0.485], [0.34, 0.19, 0.485], 0.120), 0.13)
    d = smin(d, sdCapsule(m, [0.40, -0.03, 0.365], [0.560, 0.04, -0.22], 0.058), 0.10)
    d = ssub(d, sdEllipsoid(m, np.array([0.860, 0.30, 0.02]),
                            np.array([0.340, 0.420, 0.500])), 0.16)
    d = ssub(d, sdEllipsoid(m, np.array([0.305, -0.01, 0.38]),
                            np.array([0.195, 0.228, 0.44])), 0.042)
    nose = sdEllipsoid(p, np.array([0.0, -0.30, 0.50]), np.array([0.140, 0.130, 0.26]))
    nose = smin(nose, sdEllipsoid(p, np.array([0.0, -0.04, 0.50]),
                                  np.array([0.036, 0.165, 0.24])), 0.075)
    d = ssub(d, nose, 0.032)
    d = smin(d, arch(p, -0.660, 0.19, 0.290, 0.050, 20.0, 1.32), 0.03)

    hinge = np.array([0.0, -0.08, -0.26])
    j = rotX(p - hinge, JAW) + hinge
    jm = np.stack([np.abs(j[..., 0]), j[..., 1], j[..., 2]], -1)
    jaw = sdCapsule(j, [-0.11, -0.895, 0.435], [0.11, -0.895, 0.435], 0.078)
    jaw = np.minimum(jaw, sdCapsule(jm, [0.10, -0.895, 0.435], [0.275, -0.860, 0.315], 0.074))
    jaw = np.minimum(jaw, sdCapsule(jm, [0.275, -0.860, 0.315], [0.415, -0.800, 0.020], 0.070))
    jaw = np.minimum(jaw, sdCapsule(jm, [0.415, -0.800, 0.020], [0.455, -0.735, -0.190], 0.068))
    jaw = smin(jaw, sdBox(jm - np.array([0.455, -0.450, -0.145]),
                          np.array([0.024, 0.290, 0.070])) - 0.026, 0.10)
    jaw = smin(jaw, arch(j, -0.800, 0.19, 0.275, 0.048, 20.0, 1.28), 0.03)
    return np.minimum(d, jaw)


def normal(p):
    e = 0.0016
    out = np.zeros_like(p)
    for k in ([1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]):
        k = np.array(k, float) * e
        out += k * map_(p + k)[..., None]
    return out / np.maximum(nrm(out)[..., None], 1e-9)


def ao(p, n):
    s, w = np.zeros(p.shape[:-1]), 1.0
    for i in range(1, 6):
        h = 0.024 * i * i
        s += w * (h - map_(p + n * h))
        w *= 0.72
    return np.clip(1.0 - 3.0 * s, 0.0, 1.0)


def render(cols, rows, yaw, pitch, dist, cellw, fov=1.75):
    ys, xs = np.mgrid[0:rows, 0:cols]
    u = ((xs + 0.5) / cols * 2 - 1) * (cols * cellw) / rows
    v = 1 - (ys + 0.5) / rows * 2
    target = np.array([0.0, -0.14, 0.0])
    cp, sp = np.cos(pitch), np.sin(pitch)
    ro = target + np.array([np.sin(yaw) * cp, sp, np.cos(yaw) * cp]) * dist
    fw = target - ro; fw /= np.linalg.norm(fw)
    rt = np.cross(fw, [0, 1, 0]); rt /= np.linalg.norm(rt)
    up = np.cross(rt, fw)
    rd = u[..., None] * rt + v[..., None] * up + fov * fw
    rd /= nrm(rd)[..., None]

    t = np.zeros(rd.shape[:-1])
    alive = np.ones(t.shape, bool)
    for _ in range(120):
        h = map_(ro + rd * t[..., None])
        alive &= h >= 0.0009
        t = np.where(alive, t + h * 0.92, t)
        alive &= t < 9.0
    p = ro + rd * t[..., None]
    hit = (map_(p) < 0.004) & (t < 9.0)

    n = normal(p)
    occ = ao(p, n) ** 1.15
    front = np.clip((n * -rd).sum(-1), 0, 1)
    key = -rd * 0.75 + np.array([-0.34, 0.54, 0.0])
    key = key / nrm(key)[..., None]
    dif = np.clip((n * key).sum(-1), 0, 1)
    sil = np.clip(1.0 - front, 0, 1) ** 3.0
    lum = 0.05 + occ * (0.40 * front ** 0.6 + 0.60 * dif) + 0.20 * occ * sil
    lum = np.clip((lum - 0.04) / 0.90, 0, 1)
    return np.where(hit, lum, 0.0)


# -------------------------------------------------------------------- output
W, H = 1200.0, 400.0
FS = 8.5                  # font size in px
ADV = FS * 0.6            # advance width the grid is pinned to
COLS = int(W // ADV)
ROWS = int(H // FS)
X0 = (W - COLS * ADV) / 2
Y0 = (H - ROWS * FS) / 2
FRAMES = 16
DUR = 3.6                 # seconds for one full sway
RAMP = " .:-=+*#%@"
LIT = 6                   # ramp index at which a glyph joins the bright layer

BG = "#05060f"
DIM = "#2f3766"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    top = len(RAMP) - 1
    parts = []
    for f in range(FRAMES):
        phase = 2 * np.pi * f / FRAMES
        lum = render(COLS, ROWS,
                     yaw=0.62 * np.sin(phase),
                     pitch=0.11 + 0.07 * np.cos(phase * 0.5),
                     dist=2.00, cellw=ADV / FS)
        idx = np.clip((lum * top + 0.5).astype(int), 0, top)

        # two layers: the falloff in a flat dim colour, the highlights in the
        # gradient, so the form has some depth instead of reading as a stencil
        g = ['<g class="f f%d">' % f]
        for cls, lo, hi in (("d", 2, LIT - 1), ("l", LIT, top)):
            for r in range(ROWS):
                line = "".join(RAMP[i] if lo <= i <= hi else " " for i in idx[r])
                s = line.rstrip()
                if not s.strip():
                    continue
                lead = len(s) - len(s.lstrip())
                s = s[lead:]
                g.append(
                    '<text class="%s" x="%.2f" y="%.2f" textLength="%.2f" '
                    'lengthAdjust="spacing" xml:space="preserve">%s</text>'
                    % (cls, X0 + lead * ADV, Y0 + (r + 0.79) * FS,
                       len(s) * ADV, esc(s)))
        g.append('</g>')
        parts.append("".join(g))
        print("frame %2d/%d  %d rows" % (f + 1, FRAMES, parts[-1].count("<text")))

    slot = 100.0 / FRAMES
    delays = "".join(".f%d{animation-delay:%.3fs}" % (i, DUR * i / FRAMES)
                     for i in range(FRAMES))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" '
        'width="1200" height="400" role="img" '
        'aria-label="A human skull drawn entirely in monospace characters, '
        'turning slowly between three-quarter views.">\n'
        '<style>\n'
        'text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'
        '"DejaVu Sans Mono",monospace;font-size:%.1fpx}\n'
        '.d{fill:%s}\n'
        '.l{fill:url(#bone)}\n'
        '.f{opacity:0;animation:flick %.2fs steps(1) infinite}\n'
        '@keyframes flick{0%%{opacity:1}%.4f%%{opacity:0}100%%{opacity:0}}\n'
        '%s\n'
        '@media (prefers-reduced-motion:reduce){.f{animation:none}.f0{opacity:1}}\n'
        '</style>\n'
        '<defs><linearGradient id="bone" x1="0" y1="0" x2="0.9" y2="1">'
        '<stop offset="0" stop-color="#7c5cff"/>'
        '<stop offset="0.45" stop-color="#4cc9f0"/>'
        '<stop offset="1" stop-color="#ffd166"/></linearGradient></defs>\n'
        '<rect width="1200" height="400" fill="%s"/>\n'
        '%s\n</svg>\n'
    ) % (FS, DIM, DUR, slot, delays, BG, "\n".join(parts))

    with open("assets/hero.svg", "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("wrote assets/hero.svg  %.1f KB  %d frames  %dx%d cells"
          % (len(svg.encode("utf-8")) / 1024, FRAMES, COLS, ROWS))


if __name__ == "__main__":
    main()
