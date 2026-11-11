"""Plup's pixel art: a Club Penguin-style penguin rendered like a RollerCoaster
Tycoon sprite (3/4 view, lit from the top-left, quantized to short colour
ramps with ordered dithering, dark same-colour edges instead of black lines).

The penguin is a little 3D puppet made of ellipsoids. A pose (see NEUTRAL)
says how to arrange it: flippers, feet, eyes, beak, jumping, leaning, turning,
props and hats. render_penguin() shades and palettizes the puppet;
compose() then adds effects (notes, hearts, confetti, puffles...) on top."""
import math

W, H = 56, 58          # canvas; the penguin stands at the bottom, effects float around
PX, PY = 6, 8          # where the penguin's local coordinates sit on the canvas
GROUND = 56.6          # canvas y of the shadow under his feet

LIGHT = (-0.55, -0.65, 0.75)
_l = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _l for c in LIGHT)

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# Club Penguin colours (body base colour; the ramp is derived from it)
COLORS = {
    "blue": "#1f5fc8", "red": "#c8222c", "green": "#2a8a2a", "black": "#33343a",
    "pink": "#f37fb1", "purple": "#7a3fc0", "yellow": "#f2d02c", "orange": "#f28a1c",
    "lime": "#7ccf2a", "aqua": "#2ac0c8", "brown": "#7a4b24", "peach": "#f7b78a",
    "dark green": "#145a32", "light blue": "#5fb0f0",
}
PUFFLES = {
    "blue": "#2f6fd8", "pink": "#ff7fc0", "green": "#3ab83a", "black": "#44444e",
    "purple": "#9a4fd8", "red": "#e03a3a", "yellow": "#ffd23a", "white": "#e8eef8",
    "orange": "#ff8a2a", "brown": "#8a5a30",
}

NEUTRAL = {
    "eyes": "open",      # open blink happy sleep wide heart star dizzy wink sad squint
    "look": (0, 0),      # pupils offset
    "mouth": "closed",   # closed open wide
    "lflip": 0,          # flippers: 0 rest, 1 out, 2 up, 3 in front, 4 behind
    "rflip": 0,
    "lfoot": 0,          # foot lift in pixels
    "rfoot": 0,
    "lift": 0,           # jump height in pixels
    "squash": 0,         # -1 stretched tall, 1 squashed, 2 very squashed
    "bob": 0,            # body sinks 1px (breathing)
    "rot": 0.0,          # lean/rotation in radians (+ = clockwise)
    "pivot": "feet",     # rotate around "feet" or "center"
    "turn": "front",     # front side back away (back, turned 135 degrees towards the upper right)
    "mirror": False,     # face left instead of right
    "ox": 0,             # horizontal nudge (shivering, laughing)
    "blush": False,
    "prop": None,        # see PROPS
    "hat": None,         # see HATS
    "glasses": None,     # "shades"
    "fx": (),            # effects drawn on top, see compose()
    "scene": None,       # scenery drawn behind him, e.g. ("pc", frame); see SCENES
}


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _ramp(base, n=8, dark=0.2, light=0.32, warm=False):
    """RCT-style ramp: deep shadow -> base -> highlight, with a slight hue
    shift (shadows cooler, highlights warmer), like the original palette."""
    r, g, b = _hex(base)
    out = []
    for i in range(n):
        t = i / (n - 1)
        if t < 0.6:
            k = dark + (1 - dark) * (t / 0.6)
            c = (r * k, g * k, b * k + (1 - k) * 30)
        else:
            k = (t - 0.6) / 0.4 * light
            tint = (255, 250, 225) if warm else (255, 255, 245)
            c = tuple(v + (tv - v) * k for v, tv in zip((r, g, b), tint))
        out.append(tuple(max(0, min(255, int(v))) for v in c))
    return out


RAMPS = {
    "white": [(0x58, 0x5e, 0x70), (0x74, 0x7b, 0x8c), (0x92, 0x99, 0xa8), (0xae, 0xb5, 0xc2),
              (0xc8, 0xce, 0xd8), (0xde, 0xe3, 0xea), (0xf0, 0xf2, 0xf5), (0xff, 0xff, 0xff)],
    "beak": _ramp("#f29a1a", warm=True),
    "mouth": [(0x3a, 0x08, 0x10), (0x55, 0x10, 0x18), (0x70, 0x18, 0x22), (0x8a, 0x22, 0x2c),
              (0xa0, 0x2c, 0x36), (0xb4, 0x38, 0x40), (0xc4, 0x44, 0x4a), (0xd0, 0x50, 0x55)],
}
EYE = (0x10, 0x12, 0x1c)
SHINE = (0xff, 0xff, 0xff)
SHADOW = (0, 0, 0, 80)

PAL = {
    "k": (0x1a, 0x1c, 0x2c), "w": (0xe8, 0xf0, 0xff), "W": (0xff, 0xff, 0xff),
    "s": (0x9c, 0xc8, 0xe8), "S": (0x5f, 0x8f, 0xb8), "e": EYE,
    "p": (0xf4, 0xec, 0xd8), "l": (0x9a, 0x90, 0x80), "r": (0xb8, 0x30, 0x2c),
    "R": (0xe4, 0x3b, 0x44), "b": (0x6b, 0x3a, 0x1e), "m": (0xee, 0xee, 0xf4),
    "D": (0x7a, 0x80, 0x8c), "d": (0xa8, 0xae, 0xb8), "G": (0x9c, 0xf0, 0xff),
    "y": (0xff, 0xd2, 0x3a), "o": (0xf0, 0xc8, 0x90), "P": (0xff, 0x8f, 0xab),
    "B": (0x3a, 0x7a, 0xd8), "v": (0x3a, 0xa8, 0x3a), "h": (0x7a, 0x4b, 0x24),
    "q": (0xe0, 0x40, 0x9a), "Q": (0xff, 0xe6, 0x80), "n": (0x22, 0x22, 0x2c),
}


def _art(rows, edge=PAL["k"]):
    """Pixel-art rows -> {(x, y): colour}, with a 1px edge around the shape."""
    px = {}
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                px[(x + 1, y + 1)] = PAL[ch]
    if edge:
        for (x, y) in list(px):
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in px:
                    px[n] = edge
    return px


# held props: art, top-left position in the penguin's local coordinates
PROPS = {
    "fish": (_art([".ssss..s", "sesSsss.", "ssssSss.", ".ssss..s"]), (23, 30)),
    "fish_bite": (_art(["..s", "ss.", "ss.", "..s"]), (27, 27)),
    "book": (_art(["pppp.pppp", "pllp.pllp", "pppp.pppp", "pllp.pllp", "pppp.pppp",
                   "rrrrrrrrr"]), (19, 32)),
    "book2": (_art(["pppp.ppp.", "pllp.plp.", "pppp.pppp", "pllp.pllp", "pppp.pppp",
                    "rrrrrrrrr"]), (19, 32)),
    "mug": (_art(["bbbb.", "mmmmm", "mRRmm", "mmmmm", "mmmm."]), (28, 30)),
    "mug_sip": (_art(["bbbb.", "mmmmm", "mRRmm", "mmmmm", "mmmm."]), (26, 26)),
    "laptop": (_art([".DDDDDD.", ".DDDDDD.", ".DDGGDD.", ".DDDDDD.", "dddddddd"]), (17, 36)),
    "laptop2": (_art([".DDDDDD.", ".DDDDDD.", ".DDyyDD.", ".DDDDDD.", "dddddddd"]), (17, 36)),
    "magnifier": (_art([".ww..", "wWww.", "wwww.", ".ww..", "...h.", "....h"]), (29, 22)),
    "magnifier2": (_art([".ww..", "wWww.", "wwww.", ".ww..", "...h.", "....h"]), (27, 23)),
    "pencil": (_art(["....P", "...y.", "..y..", ".y...", "o...."]), (27, 29)),
    "pencil2": (_art(["....P", "...y.", "..y..", ".y...", "o...."]), (26, 31)),
    "globe": (_art([".BvB.", "BvvBB", "BBvvB", "vBBBv", ".BvB."]), (29, 28)),
    "globe2": (_art([".vBB.", "vvBBv", "BvvBB", "BvBBB", ".BBv."]), (29, 28)),
    "globe3": (_art([".BBv.", "vBBvv", "BBBvv", "BvBBv", ".vBB."]), (29, 28)),
    "snowball": (_art([".ww.", "wWww", "wwww", ".ww."]), (31, 29)),
    "snowball_back": (_art([".ww.", "wWww", "wwww", ".ww."]), (36, 37)),
}

HATS = {
    "propeller": (_art(["RRRRyyyBBBB", ".....y.....", "...RRyBB...", "..RRRyBBB..",
                        ".RRRRyBBBB.", ".vvvvvvvvv."]), (16, 9)),
    "propeller2": (_art(["....RyB....", ".....y.....", "...RRyBB...", "..RRRyBBB..",
                         ".RRRRyBBBB.", ".vvvvvvvvv."]), (16, 9)),
    "party": (_art(["..y..", "..q..", ".qQq.", ".QqQ.", "qQqQq", "QqQqQ"]), (19, 9)),
}

# flippers: cx, cy, rx, ry, angle, depth
LEFT_FLIPPER = {
    0: (8.8, 34.5, 2.8, 8.0, 0.35, 1.0),
    1: (6.5, 25.5, 2.8, 8.0, 1.1, 1.0),
    2: (8.0, 22.0, 2.8, 8.0, 0.5, 1.0),
    3: (14.5, 31.0, 2.5, 6.5, 0.9, 11.5),
    4: (10.0, 37.0, 2.8, 8.0, -0.2, -4.0),
    5: (9.5, 33.0, 2.8, 7.5, 0.25, 1.0),     # 5/6: typing, seen from behind
    6: (9.3, 32.3, 2.8, 7.5, 0.4, 1.0),
}
RIGHT_FLIPPER = {
    0: (35.0, 34.5, 2.6, 7.5, -0.35, -2.0),
    1: (37.5, 25.5, 2.6, 7.5, -1.1, -2.0),
    2: (36.0, 22.0, 2.6, 7.5, -0.5, -2.0),
    3: (29.5, 33.0, 2.5, 6.5, -1.0, 11.5),
    4: (35.5, 37.5, 2.6, 7.5, 0.25, -4.0),
    5: (37.8, 32.5, 2.4, 6.0, -1.0, 1.0),
    6: (37.8, 31.3, 2.4, 6.0, -1.25, 1.0),
}


def _in(px, py, cx, cy, rx, ry):
    dx, dy = (px - cx) / rx, (py - cy) / ry
    return dx * dx + dy * dy <= 1


class _Ellipsoid:
    __slots__ = ("mat", "off", "cx", "cy", "rx", "ry", "c", "s", "zc", "rz", "egg", "r2")

    def __init__(self, mat, off, cx, cy, rx, ry, ang, zc, rz, egg=0.0):
        self.mat, self.off, self.cx, self.cy, self.rx, self.ry = mat, off, cx, cy, rx, ry
        self.c, self.s, self.zc, self.rz, self.egg = math.cos(ang), math.sin(ang), zc, rz, egg
        self.r2 = (max(rx, ry) * (1 + egg) + 0.5) ** 2

    def hit(self, px, py):
        """Front-surface depth and normal at (px, py), or None if missed."""
        dx, dy = px - self.cx, py - self.cy
        if dx * dx + dy * dy > self.r2:
            return None
        c, s = self.c, self.s
        u, v = dx * c + dy * s, -dx * s + dy * c
        vn = v / self.ry
        rxe = self.rx * (1 + self.egg * vn)
        un = u / rxe
        d = un * un + vn * vn
        if d > 1:
            return None
        wn = math.sqrt(1 - d)
        nu, nv, nw = un / rxe, vn / self.ry, wn / self.rz
        nx, ny = nu * c - nv * s, nu * s + nv * c
        ln = math.sqrt(nx * nx + ny * ny + nw * nw)
        return self.zc + self.rz * wn, (nx / ln, ny / ln, nw / ln)


def _shade(ramp, n, x, y, off):
    diff = max(0.0, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2])
    rz = 2 * diff * n[2] - LIGHT[2]  # reflection towards the viewer
    spec = max(0.0, rz) ** 16 * 0.22
    i = 0.22 + 0.74 * diff + spec
    k = len(ramp)
    idx = int(i * (k - 0.01) + (BAYER[y % 4][x % 4] / 16 - 0.5) * 0.6) + off
    return ramp[max(0, min(k - 1, idx))]


def _model(p):
    """Build the puppet for a pose: shaded ellipsoids, flat decals (eyes, props,
    hats) keyed by local pixel, and a test for the white face/belly patch."""
    s, bob, turn = p["squash"], p["bob"], p["turn"]
    face = {"front": 2.5, "side": 7.0, "back": None, "away": None}[turn]
    bcx, bcy = 22.0, 31.0 + 0.7 * s + bob
    brx, bry = 14.0 + 0.6 * s, 16.5 - 0.7 * s
    by = bcy - 2  # beak line; the face rides along with the body

    prims = [_Ellipsoid("body", 0, bcx, bcy, brx, bry, 0.0, 0.0, 12.0, 0.08)]
    lf, rf = LEFT_FLIPPER[p["lflip"]], RIGHT_FLIPPER[p["rflip"]]
    if turn == "back":  # seen from behind, the near/far flippers swap depth
        lf, rf = lf[:5] + (-lf[5] if lf[5] > 0 else 1.0,), rf[:5] + (1.0,)
    prims.append(_Ellipsoid("flip", 0, lf[0], lf[1] + bob, lf[2], lf[3], lf[4], lf[5], 4.0))
    prims.append(_Ellipsoid("flip", -1, rf[0], rf[1] + bob, rf[2], rf[3], rf[4], rf[5], 4.0))
    prims.append(_Ellipsoid("beak", 0, 15.5, 46.6 - p["lfoot"], 5.4, 2.7, 0.0, 3.0, 2.0))
    prims.append(_Ellipsoid("beak", -1, 28.8, 46.6 - p["rfoot"], 5.0, 2.6, 0.0, 2.0, 2.0))
    if turn == "away":  # just the tip of his beak peeks past his cheek
        prims.append(_Ellipsoid("beak", 0, bcx + brx - 0.6, by - 0.6, 3.2, 1.7, -0.25, -3.0, 2.0))

    decals = {}
    if face is not None:
        bx = 22 + face + (3.5 if turn == "side" else 0)
        rxb = 5.0 if turn == "side" else 4.6
        drop = {"closed": 1.9, "open": 3.4, "wide": 4.6}[p["mouth"]]
        prims.append(_Ellipsoid("beak", 0, bx, by + 0.2, rxb, 1.9, 0.0, 12.5, 3.0))
        prims.append(_Ellipsoid("beak", -1, bx, by + drop, rxb - 1.0, 1.5, 0.0, 12.0, 3.0))
        if p["mouth"] != "closed":
            prims.append(_Ellipsoid("mouth", 0, bx, by + drop / 2 + 0.9, rxb - 1.8,
                                    1.0 + drop / 4, 0.0, 11.8, 2.0))
        _eyes(decals, p, face, by)

    def white(px, py):
        if turn == "away":  # a sliver of cheek and belly on the far rim
            return (px - bcx) / brx > 0.8 and py > by - 11 and _in(px, py, bcx, bcy, brx - 1.0, bry - 1.6)
        if face is None or not _in(px, py, bcx, bcy, brx - 1.6, bry - 1.6):
            return False
        sh = face - 2.5
        return (_in(px, py, 19.8 + sh, by - 6.0, 5.2, 5.4) or _in(px, py, 28.8 + sh, by - 6.0, 4.8, 5.4)
                or _in(px, py, 22 + face * 0.8, bcy + 6, 10.5, 9.5))

    for key, table in (("glasses", None), ("hat", HATS), ("prop", PROPS)):
        name = p[key]
        if not name or table is None:
            continue
        art, (x0, y0) = table[name]
        dy = bob if key == "hat" else 0
        for (x, y), c in art.items():
            decals[(x0 + x, y0 + y + dy)] = c
    return prims, decals, white


def _eyes(d, p, face, by):
    lx, ly = p["look"]
    kind = p["eyes"]
    sh = face - 2.5
    if p["turn"] == "side":
        spots = [(26.5 + lx, 1.5, "near")]
    else:
        spots = [(19.5 + sh + lx, 1.7, "near"), (27.5 + sh + lx, 1.35, "far")]
    cy = by - 6.0 + ly

    def put(x, y, c=EYE):
        d[(x, y)] = c

    for cx, rx, which in spots:
        ix, iy = int(cx), int(cy)
        k = kind
        if kind == "wink":
            k = "open" if which == "near" else "happy"
        if k in ("open", "wide", "sad"):
            ry, rxx = (3.6, rx + 0.6) if k == "wide" else (2.9, rx)
            for y in range(iy - 4, iy + 5):
                for x in range(ix - 3, ix + 4):
                    if _in(x + 0.5, y + 0.5, cx, cy, rxx, ry):
                        put(x, y)
            put(ix - 1, iy - 2, SHINE)
            put(ix - 1, iy - 1, SHINE)
            if k == "wide":
                put(ix, iy - 3, SHINE)
            if k == "sad":  # brows tilted up towards the middle
                inner = 1 if which == "near" else -1
                for dx in (-2, -1, 0, 1, 2):
                    put(ix + dx, iy - 4 - (1 if dx * inner > 0 else 0))
        elif k == "blink":
            for dx in (-1, 0, 1):
                put(ix + dx, iy + 1)
        elif k == "happy":
            for dx, dy in ((-2, 1), (-1, 0), (0, -1), (1, 0), (2, 1)):
                put(ix + dx, iy + dy)
        elif k == "sleep":
            for dx, dy in ((-2, 0), (-1, 1), (0, 1), (1, 1), (2, 0)):
                put(ix + dx, iy + dy)
        elif k == "squint":  # > <
            sgn = 1 if which == "near" else -1
            for dx, dy in ((-2, -2), (-1, -1), (0, 0), (-1, 1), (-2, 2)):
                put(ix + dx * sgn, iy + dy)
        elif k == "dizzy":  # X X
            for i in (-2, -1, 0, 1, 2):
                put(ix + i, iy + i)
                put(ix + i, iy - i)
        elif k == "heart":
            for dx, dy in ((-2, -1), (-1, -1), (1, -1), (2, -1), (-2, 0), (-1, 0), (0, 0),
                           (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
                put(ix + dx, iy + dy, (0xff, 0x3a, 0x64))
            put(ix - 1, iy - 1, (0xff, 0xb0, 0xc0))
        elif k == "star":
            for dx, dy in ((0, -2), (-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (0, 0),
                           (1, 0), (2, 0), (-1, 1), (1, 1), (-2, 2), (2, 2)):
                put(ix + dx, iy + dy, (0xff, 0xd2, 0x3a))
            put(ix, iy, (0xff, 0xf4, 0xb0))
    if p["blush"] and spots:
        near = spots[0][0]
        for x in (int(near) - 3, int(near) - 2):
            put(x, int(cy) + 3, (0xff, 0x8f, 0xab))
        if len(spots) > 1:
            far = spots[1][0]
            for x in (int(far) + 2, int(far) + 3):
                put(x, int(cy) + 3, (0xff, 0x8f, 0xab))
    if p["glasses"] == "shades":
        near, far = spots[0][0], spots[-1][0]
        y0 = int(cy) - 2
        lens = {}
        for x in range(int(near) - 2, int(near) + 3):
            for y in range(y0, y0 + 4):
                lens[(x, y)] = PAL["n"]
        for x in range(int(far) - 1, int(far) + 3):
            for y in range(y0, y0 + 4):
                lens[(x, y)] = PAL["n"]
        for x in range(int(near) + 3, int(far) - 1):
            lens[(x, y0 + 1)] = PAL["n"]
        for (x, y) in list(lens):
            for n in ((x, y - 1), (x, y + 1)):
                if n not in lens:
                    d[n] = PAL["k"]
        d.update(lens)
        d[(int(near) - 1, y0)] = SHINE
        d[(int(far), y0)] = SHINE


def render_penguin(pose, color="blue"):
    """Render the penguin alone. Returns an HxW grid of RGB(A) tuples or None."""
    p = {**NEUTRAL, **pose}
    base = COLORS.get(color) or (color if str(color).startswith("#") else COLORS["blue"])
    ramps = dict(RAMPS, body=_ramp(base), flip=_ramp(base))
    prims, decals, white = _model(p)

    rot, mirror = p["rot"], p["mirror"]
    cr, sr = math.cos(rot), math.sin(rot)
    pvx, pvy = (22.0, 47.0) if p["pivot"] == "feet" else (22.0, 31.0)
    lift, ox = p["lift"], p["ox"]

    g = [[None] * W for _ in range(H)]
    solid = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            lx, ly = x + 0.5 - PX - ox, y + 0.5 - PY + lift
            if mirror:
                lx = 44.0 - lx
            if rot:
                dx, dy = lx - pvx, ly - pvy
                lx, ly = pvx + dx * cr + dy * sr, pvy - dx * sr + dy * cr
            key = (math.floor(lx), math.floor(ly))
            if key in decals:
                g[y][x] = decals[key]
                continue
            best = None
            for e in prims:
                h = e.hit(lx, ly)
                if h and (best is None or h[0] > best[0]):
                    best = (h[0], h[1], e)
            if not best:
                continue
            _, n, e = best
            nx, ny, nz = n
            if mirror:
                nx = -nx
            if rot:  # keep the light coming from the screen's top-left
                nx, ny = nx * cr - ny * sr, nx * sr + ny * cr
            mat = e.mat
            if mat == "body" and white(lx, ly):
                mat = "white"
            g[y][x] = _shade(ramps[mat], (nx, ny, nz), x, y, e.off)
            solid[y][x] = True

    # dark same-colour edge around the silhouette, the way RCT sprites read
    out = [row[:] for row in g]
    for y in range(H):
        for x in range(W):
            if not solid[y][x]:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= nx < W and 0 <= ny < H) or g[ny][nx] is None:
                    out[y][x] = tuple(int(c * 0.45) for c in g[y][x])
                    break

    if p["scene"]:
        for (x, y), c in _scene(*p["scene"]).items():
            if 0 <= x < W and 0 <= y < H and out[y][x] is None:
                out[y][x] = c

    # shadow on the ground, shrinking as he jumps
    srx = max(4.0, 14.0 * (1 - lift / 24))
    for y in range(int(GROUND - 3), min(H, int(GROUND + 3))):
        for x in range(W):
            if out[y][x] is None and _in(x + 0.5, y + 0.5, PX + 22.5 + ox, GROUND, srx, 2.0):
                out[y][x] = SHADOW
    return out


# ---- scenery ------------------------------------------------------------------
# Drawn behind the penguin, in canvas coordinates (it doesn't jump with him).

BEIGE = [(0x4a, 0x40, 0x30), (0x8a, 0x7e, 0x60), (0xb4, 0xa8, 0x84), (0xd6, 0xcc, 0xa8),
         (0xee, 0xe6, 0xc8)]   # edge, dark, shade, base, highlight
WOOD = [(0x3a, 0x22, 0x12), (0x6a, 0x40, 0x22), (0x94, 0x5e, 0x34), (0xb8, 0x7c, 0x48)]
TEAL, NAVY, SILVER = (0x00, 0x80, 0x80), (0x00, 0x00, 0x80), (0xc0, 0xc0, 0xc0)


def _poly(layer, pts, c):
    """Fill a convex polygon (canvas pixel centres inside it)."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    n = len(pts)
    for y in range(int(min(ys)), int(max(ys)) + 1):
        for x in range(int(min(xs)), int(max(xs)) + 1):
            px, py = x + 0.5, y + 0.5
            sgn = 0
            for i in range(n):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
                cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
                if cross:
                    if sgn and (cross > 0) != (sgn > 0):
                        break
                    sgn = cross
            else:
                layer[(x, y)] = c


def _rect(layer, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            layer[(x, y)] = c


_SCENE_CACHE = {}


def _scene(name, t=0):
    key = (name, t)
    if key not in _SCENE_CACHE:
        _SCENE_CACHE[key] = SCENES[name](t)
    return _SCENE_CACHE[key]


def _pc(t):
    """A 1990s beige desktop on a wooden desk, seen over his shoulder: CRT
    monitor on a pizza-box case, keyboard, a Windows 95-ish screen where a
    line of text types itself out, and a blinking drive light."""
    obj = {}
    # desk: top surface receding to the upper right, front edge, legs
    _poly(obj, [(16, 39), (56, 39), (56, 36), (20, 36)], WOOD[3])
    _rect(obj, 16, 39, 55, 40, WOOD[1])
    _rect(obj, 50, 41, 52, 55, WOOD[1])
    _rect(obj, 53, 41, 53, 55, WOOD[0])
    _rect(obj, 18, 41, 20, 55, WOOD[1])
    # case (pizza box) under the monitor
    _poly(obj, [(29, 31), (49, 31), (55, 28), (35, 28)], BEIGE[4])
    _rect(obj, 29, 31, 48, 35, BEIGE[3])
    _poly(obj, [(49, 31), (55, 28), (55, 32), (49, 36)], BEIGE[2])
    _rect(obj, 38, 33, 44, 33, BEIGE[1])                       # floppy slot
    obj[(46, 33)] = (0x40, 0xff, 0x60) if (t * 7) % 5 < 2 else (0x20, 0x60, 0x30)  # drive light
    # CRT monitor: angled front, tapering back, light top
    _poly(obj, [(31, 15), (47, 15), (53, 12), (37, 12)], BEIGE[4])
    _poly(obj, [(47, 15), (53, 12), (53, 26), (47, 30)], BEIGE[2])
    _rect(obj, 31, 15, 46, 29, BEIGE[3])
    _rect(obj, 31, 29, 46, 29, BEIGE[2])
    _rect(obj, 36, 30, 43, 30, BEIGE[1])                       # stand
    # keyboard on the desk
    _poly(obj, [(34, 38), (47, 38), (49, 36), (36, 36)], BEIGE[3])
    for x in range(36, 47, 2):
        obj[(x, 37)] = BEIGE[4]

    # dark same-colour edge around the whole lot
    layer = dict(obj)
    for (x, y) in obj:
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in obj:
                layer[n] = BEIGE[0] if y < 36 else WOOD[0]

    # screen, recessed in a dark bezel
    _rect(layer, 32, 16, 45, 28, BEIGE[1])
    _rect(layer, 33, 17, 44, 27, TEAL)
    _rect(layer, 33, 27, 44, 27, SILVER)                       # taskbar
    _rect(layer, 33, 27, 34, 27, (0x20, 0xa0, 0x20))           # start button
    _rect(layer, 34, 18, 43, 25, SILVER)                       # window
    _rect(layer, 35, 18, 43, 18, NAVY)                         # title bar
    layer[(43, 18)] = (0xff, 0x40, 0x40)
    _rect(layer, 35, 19, 42, 24, (0xff, 0xff, 0xff))
    left, cur = t, (36, 20)
    for i, n in enumerate((7, 5, 6)):   # lines of "text", typed one pixel per frame
        k = min(n, left)
        left -= k
        for x in range(36, 36 + k):
            layer[(x, 20 + 2 * i)] = (0x30, 0x30, 0x38)
        if k:
            cur = (36 + k, 20 + 2 * i)
    if t <= PC_FRAMES or (t // 3) % 2 == 0:
        layer[cur] = NAVY                                      # cursor
    layer[(33, 17)] = layer[(34, 17)] = (0x60, 0xc0, 0xc0)       # glass glare
    return layer


SCENES = {"pc": _pc}
PC_FRAMES = 18   # frames for the text to type out on the pc screen


# ---- effects ------------------------------------------------------------------

GLYPHS = {
    "Z": ["#####", "...#.", "..#..", ".#...", "#####"],
    "!": [".##.", "####", "####", ".##.", ".##.", "....", ".##.", ".##."],
    "?": [".###.", "##.##", "...##", "..##.", ".##..", ".....", ".##..", ".##.."],
    "heart": [".##.##.", "#######", "#######", "#######", ".#####.", "..###..", "...#..."],
    "hsmall": [".#.#.", "#####", ".###.", "..#.."],
    "note": ["..###", "..#.#", "..#..", "###..", "###.."],
    "spark": [".#.", "###", ".#."],
    "sparkbig": ["..#..", "..#..", "#####", "..#..", "..#.."],
    "star": ["..#..", ".###.", "#####", ".###.", ".#.#."],
    "drop": [".#.", ".#.", "###", "###", ".#."],
    "flake": ["#.#", ".#.", "#.#"],
    "bulb": [".###.", "#####", "#####", "#####", ".###."],
}
INK = {  # fill, edge (None = no edge)
    "Z": ((0xa6, 0xd8, 0xff), (0x2a, 0x4a, 0x8a)),
    "!": ((0xff, 0xd8, 0x3a), (0x8a, 0x4a, 0x08)),
    "?": ((0xff, 0xd8, 0x3a), (0x8a, 0x4a, 0x08)),
    "heart": ((0xff, 0x4a, 0x6e), (0x7a, 0x10, 0x28)),
    "hsmall": ((0xff, 0x5a, 0x7e), (0x7a, 0x10, 0x28)),
    "star": ((0xff, 0xd8, 0x3a), (0x8a, 0x5a, 0x08)),
    "drop": ((0x9c, 0xd8, 0xff), (0x2a, 0x5a, 0x9a)),
    "flake": ((0xff, 0xff, 0xff), (0x8a, 0xb8, 0xe8)),
    "bulb": ((0xff, 0xf0, 0x80), (0x9a, 0x7a, 0x10)),
    "spark": ((0xff, 0xff, 0xd0), None),
    "sparkbig": ((0xff, 0xff, 0xd0), None),
}
NOTE_COLORS = [(0xff, 0xd8, 0x3a), (0xff, 0x7f, 0xc0), (0x7c, 0xe8, 0xff)]
CONFETTI = [(0xff, 0x4a, 0x6e), (0xff, 0xd8, 0x3a), (0x5c, 0xe0, 0x6a), (0x5c, 0xb8, 0xff),
            (0xd0, 0x7c, 0xff), (0xff, 0x9a, 0x3a)]


def _paint(g, layer, edge, top_light=False):
    """Paint a {(x, y): colour} layer plus a 1px edge; top pixels get a highlight."""
    if edge:
        for (x, y) in list(layer):
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in layer and 0 <= nx < W and 0 <= ny < H:
                    g[ny][nx] = edge
    for (x, y), c in layer.items():
        if 0 <= x < W and 0 <= y < H:
            if top_light and (x, y - 1) not in layer:
                c = tuple(min(255, v + 50) for v in c[:3])
            g[y][x] = c


def _glyph(g, name, x0, y0, fill=None, edge="default"):
    f, e = INK.get(name, ((255, 255, 255), (0x40, 0x46, 0x58)))
    layer = {}
    for dy, row in enumerate(GLYPHS[name]):
        for dx, ch in enumerate(row):
            if ch == "#":
                layer[(int(x0) + dx, int(y0) + dy)] = fill or f
    _paint(g, layer, e if edge == "default" else edge, top_light=True)


def _blob(g, cx, cy, rx, ry, fill, edge):
    layer = {}
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            if _in(x + 0.5, y + 0.5, cx, cy, rx, ry):
                layer[(x, y)] = fill
    _paint(g, layer, edge)


def _puffle(g, cx, by, color, squash=0):
    """A Club Penguin puffle: a fuzzy shaded ball with big eyes and a tuft."""
    ramp = _ramp(PUFFLES.get(color, PUFFLES["blue"]))
    rx, ry = 5.6 + 0.7 * squash, 5.0 - 0.9 * squash
    cy = by - ry
    layer = {}
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = dx * dx + dy * dy
            if d <= 1:
                n = (dx, dy, math.sqrt(1 - d))
                layer[(x, y)] = _shade(ramp, n, x, y, 0)
    edge = tuple(int(c * 0.45) for c in ramp[3])
    _paint(g, layer, edge)
    top = int(cy - ry)
    for dx, dy in ((-1, -1), (0, -2), (1, -1), (0, -1)):  # tuft
        x, y = int(cx) + dx, top + dy
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = edge
    for ex in (int(cx) - 2, int(cx) + 1):  # big eyes, looking right towards Plup
        for dx in (0, 1):
            for dy in (-2, -1, 0):
                x, y = ex + dx, int(cy) + dy
                if 0 <= x < W and 0 <= y < H:
                    g[y][x] = EYE if (dx == 1 and dy > -2) else (255, 255, 255)


def compose(grid, fx, lift=0, ox=0):
    """Draw effects over a rendered penguin. Each effect is a tuple:
    ("dots", n) ("zzz", n) ("!",) ("?",) ("heart",) ("hearts", t) ("notes", t)
    ("sparkles", t) ("stars", t) ("sweat",) ("steam", t) ("confetti", t)
    ("dust", t) ("snow", t) ("bulb",) ("snowball", x, y) ("achoo", t)
    ("poof", t) ("puffle", x, y, colour, squash)"""
    if not fx:
        return grid
    g = [row[:] for row in grid]
    hx, hy = 28 + ox, 22 - lift  # top of his head
    for item in fx:
        kind, args = item[0], item[1:]
        t = args[0] if args else 0
        if kind == "dots":
            layer = {}
            for y in range(1, 11):
                for x in range(32, 52):
                    if _in(x + 0.5, y + 0.5, 42, 6, 9.6, 4.9):
                        layer[(x, y)] = RAMPS["white"][7 if y < 6 else 6]
            for x, y, r in ((34.5, 13.0, 1.7), (31.5, 16.0, 1.1)):
                for yy in range(int(y - 2), int(y + 3)):
                    for xx in range(int(x - 2), int(x + 3)):
                        if _in(xx + 0.5, yy + 0.5, x, y, r + 0.3, r + 0.3):
                            layer[(xx, yy)] = RAMPS["white"][6]
            _paint(g, layer, (0x40, 0x46, 0x58))
            for i in range(t):
                for dx in (0, 1):
                    for dy in (0, 1):
                        g[5 + dy][37 + i * 4 + dx] = EYE
        elif kind == "zzz":
            for i, (x, y) in enumerate(((38, 16), (42, 10), (46, 4))):
                if i < t:
                    _glyph(g, "Z", x, y - lift)
        elif kind in ("!", "?"):
            _glyph(g, kind, 42, max(1, 8 - lift))
        elif kind == "heart":
            _glyph(g, "heart", 40, max(1, 9 - lift))
        elif kind == "hearts":
            for i in range(3):
                y = 24 - ((t * 2 + i * 8) % 24)
                x = 8 + i * 18 + (1 if (t // 2 + i) % 2 else 0)
                _glyph(g, "hsmall", x, y)
        elif kind == "notes":
            for i in range(3):
                y = 22 - ((t * 2 + i * 7) % 22)
                x = 6 + i * 17 + (1 if (t // 2 + i) % 2 else -1)
                _glyph(g, "note", x, y, fill=NOTE_COLORS[i], edge=(0x30, 0x30, 0x40))
        elif kind == "sparkles":
            for i, (x, y) in enumerate(((7, 20), (46, 14), (12, 6), (49, 34), (4, 38), (40, 2))):
                phase = (t + i * 2) % 6
                if phase < 2:
                    _glyph(g, "spark", x, y)
                elif phase < 4:
                    _glyph(g, "sparkbig", x - 1, y - 1)
        elif kind == "stars":
            for i in range(3):
                a = t * 0.7 + i * 2.094
                x, y = hx + 13 * math.cos(a) - 2, hy - 2 + 3 * math.sin(a)
                _glyph(g, "star", x, y)
        elif kind == "sweat":
            _glyph(g, "drop", 43 + ox, 22 - lift)
        elif kind == "steam":
            for i in range(3):
                for j in range(5):
                    y = 34 - lift - j * 2 - (t % 2)
                    x = 36 + ox + i * 2 + (1 if (j + t + i) % 3 == 0 else 0)
                    if 0 <= y < H and j < 3 + (t + i) % 3:
                        g[y][x] = (0xf0, 0xf4, 0xff)
        elif kind == "confetti":
            for i in range(26):
                x = (i * 37 + 11) % W
                y = ((i * 23) % 40 + t * 3) % 52
                if 0 <= y < H:
                    c = CONFETTI[i % len(CONFETTI)]
                    g[y][x] = c
                    if (i + t) % 2 and x + 1 < W:
                        g[y][x + 1] = c
        elif kind == "dust":
            for side in (-1, 1):
                r = 1.5 + t * 0.9
                cx = 28 + ox + side * (13 + t * 3)
                _blob(g, cx, GROUND - 1 - t * 0.5, r, r * 0.8, (0xe8, 0xe2, 0xd4), (0xa8, 0xa0, 0x90))
        elif kind == "snow":
            for i in range(10):
                x = (i * 13 + 5 + (t // 3 + i) % 3) % W
                y = ((i * 17) % 50 + t * 2) % 54
                _glyph(g, "flake", x, y)
        elif kind == "bulb":
            _glyph(g, "bulb", hx - 2, max(1, hy - 15))
            for dx in (0, 1, 2):
                for dy in (5, 6):
                    y = max(1, hy - 15) + dy
                    if 0 <= y < H:
                        g[y][hx - 1 + dx] = (0x8a, 0x90, 0x9c)
            if t % 2 == 0:
                for x, y in ((hx - 6, hy - 14), (hx + 6, hy - 14), (hx, hy - 19)):
                    _glyph(g, "spark", x, y)
        elif kind == "snowball":
            art = PROPS["snowball"][0]
            for (x, y), c in art.items():
                X, Y = int(args[0]) + x, int(args[1]) + y
                if 0 <= X < W and 0 <= Y < H:
                    g[Y][X] = c
        elif kind == "achoo":
            for i in range(6):
                x = 40 + ox + i * 2 + t * 2
                y = 31 - lift + (i % 3) - 1 + (i // 3)
                if 0 <= x < W and 0 <= y < H:
                    g[y][x] = (0xc8, 0xe8, 0xff)
        elif kind == "poof":
            for i, (dx, dy) in enumerate(((-9, -2), (8, -3), (-3, -8), (4, 3), (-7, 5), (10, 4))):
                r = 2.0 + (t + i) % 3 * 0.8
                _blob(g, hx + dx * (1 + t * 0.15), hy + 6 + dy, r, r, (0xf4, 0xf4, 0xf8),
                      (0xb0, 0xb4, 0xc0))
        elif kind == "puffle":
            _puffle(g, args[0], args[1], args[2], args[3] if len(args) > 3 else 0)
    return g


def render(pose, color="blue"):
    """Penguin plus effects, as an HxW grid of RGB/RGBA tuples (None = transparent)."""
    p = {**NEUTRAL, **pose}
    return compose(render_penguin({k: v for k, v in p.items() if k != "fx"}, color),
                   p["fx"], p["lift"], p["ox"])


def to_rgba(grid, scale):
    """Scaled RGBA bytes for a grid, nearest-neighbour so pixels stay crisp."""
    out = bytearray()
    for row in grid:
        line = bytearray()
        for c in row:
            px = b"\0\0\0\0" if c is None else bytes((c[0], c[1], c[2], c[3] if len(c) == 4 else 255))
            line += px * scale
        out += bytes(line) * scale
    return bytes(out)


def sheet(poses, path, color="blue", scale=4, cols=8):
    """Write a contact sheet of poses on RCT grass, for eyeballing."""
    import cairo
    w, h = W * scale, H * scale
    rows = (len(poses) + cols - 1) // cols
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w * min(cols, len(poses)), h * rows)
    cr = cairo.Context(surf)
    cr.set_source_rgb(0.55, 0.75, 0.45)
    cr.paint()
    for i, p in enumerate(poses):
        data = bytearray(to_rgba(render(p, color), scale))
        for j in range(0, len(data), 4):  # RGBA -> cairo's premultiplied BGRA
            r, g, b, a = data[j:j + 4]
            data[j:j + 4] = bytes((b * a // 255, g * a // 255, r * a // 255, a))
        img = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, w * 4)
        cr.set_source_surface(img, (i % cols) * w, (i // cols) * h)
        cr.paint()
    surf.write_to_png(path)


if __name__ == "__main__":
    # python3 sprite.py out.png [color]
    import sys
    sheet([
        {}, {"eyes": "blink"}, {"eyes": "happy", "rflip": 1, "fx": (("heart",),)},
        {"lflip": 2, "rflip": 2, "eyes": "happy"}, {"look": (1, -1), "fx": (("dots", 3),)},
        {"mouth": "wide", "eyes": "squint"}, {"eyes": "sleep", "squash": 1, "fx": (("zzz", 3),)},
        {"turn": "side"}, {"turn": "back"}, {"turn": "side", "mirror": True},
        {"rot": 0.2, "lfoot": 2}, {"lift": 8, "squash": -1, "lflip": 1, "rflip": 1},
        {"rot": 3.14, "pivot": "center", "lift": 8}, {"rot": 1.5, "pivot": "center", "lift": -6},
        {"eyes": "heart", "blush": True, "fx": (("hearts", 2),)},
        {"eyes": "star", "fx": (("sparkles", 1),)}, {"eyes": "dizzy", "fx": (("stars", 1),)},
        {"eyes": "wide", "fx": (("!",),)}, {"eyes": "sad", "fx": (("sweat",),)},
        {"eyes": "wink"}, {"prop": "fish", "rflip": 3}, {"prop": "book", "lflip": 3, "rflip": 3, "look": (0, 1)},
        {"prop": "mug", "rflip": 3, "fx": (("steam", 1),)}, {"prop": "laptop", "lflip": 3, "rflip": 3, "look": (0, 1)},
        {"prop": "magnifier", "rflip": 3, "look": (1, 0)}, {"prop": "pencil", "rflip": 3, "look": (1, 1)},
        {"prop": "globe", "rflip": 3}, {"glasses": "shades", "rot": 0.08},
        {"hat": "propeller", "lift": 6, "eyes": "happy"}, {"hat": "party", "fx": (("confetti", 2),)},
        {"lflip": 3, "look": (1, -1), "fx": (("bulb",),)},
        {"eyes": "happy", "fx": (("puffle", 8, 56, "pink"),), "mirror": True},
        {"fx": (("notes", 3),), "eyes": "happy", "rot": -0.15, "lflip": 2},
        {"eyes": "squint", "ox": 1, "lflip": 3, "rflip": 3, "fx": (("snow", 3),)},
        {"squash": 2, "fx": (("dust", 1),)}, {"prop": "snowball", "rflip": 3},
    ], sys.argv[1] if len(sys.argv) > 1 else "sheet.png", sys.argv[2] if len(sys.argv) > 2 else "blue")
