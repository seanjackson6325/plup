"""Plup's animations.

Two kinds:
  * loops: what he does continuously in a state (idle, thinking, talking,
    working with a tool, sleeping, being dragged). A function of the tick.
  * tricks: one-shot sequences of keyframes, played on events or at random
    while idle. A trick is a list of (ticks, pose) frames; a pose is a dict of
    sprite.NEUTRAL keys, plus optional "move" (screen pixels per tick, for
    walking/sliding across the desktop).

One tick is TICK_MS milliseconds."""
import random

import sprite

TICK_MS = 100


def F(n, **pose):
    return (n, pose)


# ---- loops ------------------------------------------------------------------

TOOL_KIND = {
    "Bash": "type", "BashOutput": "type", "KillShell": "type",
    "Read": "search", "Grep": "search", "Glob": "search", "LS": "search",
    "Edit": "write", "Write": "write", "MultiEdit": "write", "NotebookEdit": "write",
    "WebSearch": "web", "WebFetch": "web",
}


def loop(state, t, tool=None, since=0):
    """since: the tick the current tool started, for intro moves like turning around."""
    if state == "sleep":
        return dict(eyes="sleep", squash=(t // 10) % 2, fx=(("zzz", (t // 7) % 4),))
    if state == "think":
        return dict(look=((t // 12) % 2 * 2 - 1, -1), lflip=3, bob=(t // 8) % 2,
                    fx=(("dots", (t // 3) % 3 + 1),))
    if state == "talk":
        return dict(mouth="open" if (t // 2) % 2 else "closed", bob=(t // 5) % 2,
                    rflip=(0, 1, 0, 3)[(t // 9) % 4])
    if state == "work":
        kind = TOOL_KIND.get(tool, "think")
        if kind == "type":  # turns around to type at his 90s desktop
            e = t - since
            if e < 2:
                return dict(turn="side", ox=-5, scene=("pc", 0))
            tap = (t // 2) % 2
            return dict(turn="away", ox=-5, scene=("pc", (e - 2) % (sprite.PC_FRAMES + 12)),
                        lflip=5 + tap, rflip=6 - tap, bob=(t // 6) % 2)
        if kind == "search":
            return dict(prop="magnifier" if (t // 6) % 2 else "magnifier2", rflip=3,
                        look=((1, 0), (0, 1), (-1, 0), (0, 1))[(t // 6) % 4], bob=(t // 6) % 2)
        if kind == "write":
            return dict(prop="pencil" if (t // 2) % 2 else "pencil2", rflip=3, look=(1, 1),
                        bob=(t // 6) % 2, eyes="squint" if (t // 20) % 3 == 2 else "open")
        if kind == "web":
            return dict(prop=("globe", "globe2", "globe3")[(t // 3) % 3], rflip=3, look=(1, 0),
                        bob=(t // 6) % 2, eyes="wide" if (t // 15) % 4 == 3 else "open")
        return loop("think", t)
    if state == "alert":
        return dict(rflip=1 + (t // 3) % 2, lift=2 * ((t // 3) % 2), fx=(("!",),))
    if state == "drag":
        return dict(eyes="wide", mouth="open", lflip=1 + (t // 2) % 2, rflip=2 - (t // 2) % 2,
                    lfoot=2 * ((t // 2) % 2), rfoot=2 * (1 - (t // 2) % 2), fx=(("sweat",),))
    return dict(bob=(t // 6) % 2)  # idle: gentle breathing


# ---- tricks -----------------------------------------------------------------

TRICKS = {}  # name -> (label, builder, idle weight, needs room to move)


def trick(label, weight=1.0, moves=False):
    def deco(fn):
        TRICKS[fn.__name__] = (label, fn, weight, moves)
        return fn
    return deco


def _hop(height=6, **extra):
    return [F(2, squash=1, **extra), F(1, lift=height // 2, squash=-1, **extra),
            F(2, lift=height, squash=-1, **extra), F(1, lift=height // 2, **extra),
            F(1, squash=2, fx=(("dust", 0),)), F(2, squash=1, fx=(("dust", 1),))]


@trick("Wave hello", 3)
def wave(r):
    return [F(2, rflip=1 + i % 2, eyes="happy") for i in range(6)] + [F(2)]


@trick("Look around", 3)
def look_around(r):
    seq = [(-1, 0), (1, 0), (1, -1), (-1, 1)]
    r.shuffle(seq)
    return [F(r.randint(5, 9), look=l) for l in seq[:3]] + [F(3, eyes="blink"), F(2)]


@trick("Yawn", 1.5)
def yawn(r):
    return [F(3, eyes="blink", squash=-1), F(2, mouth="open", eyes="sleep", lflip=1, rflip=1, squash=-1),
            F(9, mouth="wide", eyes="squint", lflip=2, rflip=2, squash=-1, lift=1),
            F(3, mouth="open", eyes="sleep", lflip=1, rflip=1), F(4, eyes="sleep", squash=1),
            F(2, eyes="blink"), F(2)]


@trick("Stretch", 1.5)
def stretch(r):
    return [F(3, lflip=1, rflip=1), F(8, lflip=2, rflip=2, squash=-1, lift=1, eyes="squint"),
            F(3, lflip=2, rflip=2, squash=-1, rot=0.1, eyes="squint"),
            F(3, lflip=2, rflip=2, squash=-1, rot=-0.1, eyes="squint"),
            F(2, squash=1, eyes="happy"), F(2)]


@trick("Hop", 1.5)
def hop(r):
    frames = _hop(6, eyes="happy", lflip=1, rflip=1)
    if r.random() < 0.5:
        frames += _hop(8, eyes="happy", lflip=2, rflip=2)
    return frames + [F(3, eyes="happy")]


@trick("Spin", 1)
def spin(r):
    one = [F(2, turn="side"), F(2, turn="back"), F(2, turn="side", mirror=True), F(2, mirror=True)]
    return [F(1, squash=1)] + one * r.choice((1, 2)) + [F(5, eyes="happy", fx=(("sparkles", 1),))]


@trick("Dance", 1.2)
def dance(r):
    frames = []
    for beat in range(12):
        side = 1 if beat % 2 else -1
        frames.append(F(3, rot=0.15 * side, lflip=2 if side < 0 else 0, rflip=2 if side > 0 else 0,
                        lfoot=2 if side < 0 else 0, rfoot=2 if side > 0 else 0,
                        eyes="happy", mouth="open" if beat % 4 == 1 else "closed",
                        bob=beat % 2, fx=(("notes", beat * 3),)))
        if beat == 7:
            frames += [F(2, turn="side", fx=(("notes", 22),)), F(2, turn="back", fx=(("notes", 23),)),
                       F(2, turn="side", mirror=True, fx=(("notes", 24),))]
    return frames + [F(4, lflip=2, rflip=2, eyes="star", fx=(("sparkles", 2),))]


@trick("Sing", 1)
def sing(r):
    frames = []
    for i in range(14):
        frames.append(F(3, mouth=("open", "wide", "open", "closed")[i % 4], eyes="sleep" if i % 6 < 3 else "happy",
                        rot=(-0.06, 0, 0.06, 0)[i % 4], lflip=3, rflip=1 if i % 4 < 2 else 0,
                        fx=(("notes", i * 2),)))
    return frames + [F(3, eyes="happy", blush=True)]


@trick("Laugh", 0.6)
def laugh(r):
    return [F(1, eyes="squint", mouth="wide" if i % 2 else "open", ox=(i % 2) * 2 - 1,
              bob=i % 2, lflip=3, rflip=3) for i in range(16)] + [F(4, eyes="happy", blush=True)]


@trick("Sneeze", 0.7)
def sneeze(r):
    return [F(4, eyes="squint", mouth="open", rot=-0.1), F(5, eyes="squint", mouth="wide", rot=-0.18, lift=1),
            F(2, eyes="blink", mouth="wide", rot=0.2, squash=1, fx=(("achoo", 0),)),
            F(3, eyes="blink", rot=0.12, fx=(("achoo", 1),)), F(2, eyes="blink", fx=(("achoo", 2),)),
            F(3, eyes="wide"), F(4, eyes="happy", blush=True)]


@trick("Eat a fish", 1)
def eat_fish(r):
    return [F(3, fx=(("poof", 0),), prop="fish", rflip=3, eyes="wide"), F(4, prop="fish", rflip=3, eyes="star"),
            F(3, prop="fish", rflip=3, eyes="heart", mouth="open"),
            F(3, prop="fish_bite", rflip=3, mouth="wide", eyes="squint"),
            F(2, mouth="closed", squash=1, eyes="squint", blush=True),
            F(2, squash=-1, eyes="happy", blush=True),
            F(10, eyes="happy", blush=True, fx=(("hearts", 0),)) ] + \
           [F(2, eyes="happy", blush=True, fx=(("hearts", i),)) for i in range(1, 6)]


@trick("Throw a snowball", 1)
def snowball(r):
    path = [(44, 30), (49, 25), (54, 22), (60, 21)]
    return [F(4, prop="snowball", rflip=3, look=(0, 1)), F(3, prop="snowball", rflip=3, eyes="happy"),
            F(4, prop="snowball_back", rflip=4, rot=-0.12, eyes="squint", look=(1, 0)),
            F(1, rflip=1, rot=0.15, mouth="open", fx=(("snowball",) + path[0],))] + \
           [F(1, rflip=1, rot=0.1, look=(1, -1), fx=(("snowball",) + p,)) for p in path[1:]] + \
           [F(6, look=(1, 0), eyes="wide"), F(5, eyes="happy", fx=(("sparkles", 0),))]


@trick("Read a book", 1)
def read(r):
    frames = []
    for page in range(3):
        frames += [F(r.randint(10, 16), prop="book", lflip=3, rflip=3, look=(page % 2 * 2 - 1, 1)),
                   F(2, prop="book2", lflip=3, rflip=3, look=(0, 1))]
    return frames + [F(3, prop="book", lflip=3, rflip=3, eyes="blink"), F(4, eyes="happy")]


@trick("Hot cocoa", 1)
def cocoa(r):
    frames = [F(2, prop="mug", rflip=3, fx=(("steam", i),)) for i in range(6)]
    frames += [F(5, prop="mug_sip", rflip=3, eyes="sleep", blush=True)]
    frames += [F(2, prop="mug", rflip=3, eyes="happy", blush=True, fx=(("steam", i),)) for i in range(6)]
    return frames + [F(4, eyes="happy", blush=True, fx=(("hearts", 1),))]


@trick("Cool shades", 0.8)
def shades(r):
    return [F(3, fx=(("poof", 0),)), F(2, glasses="shades", fx=(("poof", 1),)),
            F(6, glasses="shades", rot=0.08, lflip=3),
            F(8, glasses="shades", rot=0.08, lflip=3, fx=(("sparkles", 1),)),
            F(4, glasses="shades", rot=-0.08, rflip=2, fx=(("sparkles", 3),)),
            F(3, glasses="shades"), F(3, fx=(("poof", 2),)), F(2)]


@trick("Propeller hat", 0.8)
def propeller(r):
    frames = [F(3, hat="propeller", fx=(("poof", 0),))]
    for i in range(30):
        lift = min(i, 8) if i < 22 else max(0, 8 - (i - 22))
        frames.append(F(1, hat="propeller" if i % 2 else "propeller2", lift=lift,
                        lflip=1, rflip=1, eyes="happy" if i < 20 else "open",
                        lfoot=1 if lift else 0, bob=i % 2 if lift else 0))
    return frames + [F(1, hat="propeller", squash=2, fx=(("dust", 0),)),
                     F(2, hat="propeller", squash=1, fx=(("dust", 1),)),
                     F(3, hat="propeller", eyes="happy"), F(3, fx=(("poof", 1),))]


@trick("Puffle visit", 1)
def puffle(r):
    col = r.choice(["blue", "pink", "green", "black", "purple", "red", "yellow", "white", "orange", "brown"])
    frames = []
    xs = list(range(-6, 9, 2))
    for i, x in enumerate(xs):  # hops in from the left
        hop = (0, 3, 4, 3)[i % 4]
        frames.append(F(1, look=(-1, 0), eyes="wide" if i > 3 else "open",
                        fx=(("puffle", x, 56 - hop, col, 1 if hop == 0 else 0),)))
    for i in range(4):  # happy bouncing together
        frames.append(F(2, eyes="heart", mirror=True, blush=True, lift=2 * (i % 2),
                        fx=(("puffle", 8, 56 - 3 * ((i + 1) % 2), col), ("hearts", i * 2))))
    frames.append(F(6, eyes="happy", mirror=True, lflip=1, rflip=1,
                    fx=(("puffle", 8, 56, col), ("hearts", 9))))
    for i, x in enumerate(range(8, -10, -2)):  # and away it goes
        hop = (0, 3, 4, 3)[i % 4]
        frames.append(F(1, mirror=True, rflip=1 + i % 2, eyes="happy",
                        fx=(("puffle", x, 56 - hop, col),)))
    return frames + [F(3)]


@trick("Backflip", 0.6)
def backflip(r):
    frames = [F(2, squash=1), F(1, squash=2), F(1, lift=5, squash=-1, lflip=2, rflip=2)]
    for i, (lift, rot) in enumerate(((9, -0.8), (12, -1.6), (13, -2.4), (13, -3.1), (12, -3.9),
                                     (10, -4.7), (7, -5.5))):
        frames.append(F(1, lift=lift, rot=rot, pivot="center", lflip=1, rflip=1, eyes="squint"))
    return frames + [F(1, squash=2, fx=(("dust", 0),)), F(2, squash=1, fx=(("dust", 1),)),
                     F(6, lflip=2, rflip=2, eyes="star", fx=(("sparkles", 0),)),
                     F(4, lflip=2, rflip=2, eyes="star", fx=(("sparkles", 2),)), F(2)]


@trick("Shiver", 0.5)
def shiver(r):
    return [F(1, eyes="squint", lflip=3, rflip=3, ox=(i % 2) * 2 - 1, blush=i > 6,
              fx=(("snow", i),)) for i in range(26)] + [F(3, eyes="blink")]


@trick("Tap foot", 1)
def tap_foot(r):
    frames = []
    for i in range(6):
        frames += [F(2, rfoot=2, look=(1, -1)), F(2, look=(1, -1))]
    return frames + [F(4, eyes="sleep", squash=1), F(2, eyes="blink"), F(2)]


@trick("Have an idea", 1)
def ponder(r):
    return [F(16, lflip=3, look=(1, -1), fx=(("dots", 3),)), F(6, lflip=3, look=(-1, -1), fx=(("dots", 3),)),
            F(1, eyes="wide", squash=1), F(3, eyes="wide", lift=4, rflip=2, fx=(("bulb", 0),)),
            F(3, eyes="star", lift=2, rflip=2, fx=(("bulb", 1),)),
            F(6, eyes="star", rflip=2, fx=(("bulb", 0),)), F(2)]


@trick("Bow", 0.5)
def bow(r):
    return [F(3, rot=0.15, lflip=3), F(6, rot=0.32, eyes="sleep", lflip=3), F(3, rot=0.1, eyes="blink"),
            F(4, eyes="happy", rflip=1)]


@trick("Juggle snowballs", 0.8)
def juggle(r):
    pts = [(15, 30), (13, 17), (26, 5), (39, 17), (37, 30), (26, 13)]
    frames = []
    for i in range(24):
        balls = tuple(("snowball",) + pts[(i + k * 2) % 6] for k in range(3))
        frames.append(F(1, lflip=3 if i % 2 else 1, rflip=1 if i % 2 else 3, look=(0, -1),
                        eyes="wide" if i > 18 else "open", fx=balls))
    return frames + [F(3, eyes="happy"), F(4, eyes="happy", fx=(("sparkles", 1),))]


@trick("Belly slide", 0.8, moves=True)
def slide(r, direction=None):
    d = direction or r.choice((-1, 1))
    m = d < 0
    frames = [F(3, mirror=m, squash=1), F(2, mirror=m, rot=0.6, pivot="center", lift=2, lflip=1, rflip=1)]
    frames += [F(1, mirror=m, rot=1.55, pivot="center", lift=-6, lflip=2, rflip=2, eyes="happy",
                 move=d * 9, fx=(("dust", i % 3),) if i % 4 == 0 else ()) for i in range(r.randint(14, 26))]
    return frames + [F(2, mirror=m, rot=0.8, pivot="center", lift=2), F(1, mirror=m, squash=2),
                     F(4, mirror=m, eyes="star", fx=(("sparkles", 0),)), F(2, mirror=m)]


@trick("Waddle around", 2.5, moves=True)
def walk(r, direction=None):
    d = direction or r.choice((-1, 1))
    m = d < 0
    frames = [F(4, mirror=m, look=(1, 0))]
    for i in range(r.randint(8, 20)):
        frames.append(F(2, mirror=m, rot=0.08 if i % 2 else -0.08, lfoot=2 if i % 2 else 0,
                        rfoot=0 if i % 2 else 2, bob=i % 2, move=d * 3))
    return frames + [F(4, mirror=m), F(3, eyes="happy")]


@trick("Wave both flippers", 1)
def cheer(r):
    frames = []
    for i in range(8):
        frames.append(F(2, lflip=2 if i % 2 else 1, rflip=1 if i % 2 else 2, eyes="happy",
                        lift=2 * (i % 2), mouth="open", fx=(("sparkles", i),)))
    return frames + [F(2)]


@trick("Peek at you", 0.8)
def peek(r):
    return [F(2, turn="side"), F(3, turn="back"), F(10, turn="back", fx=(("?",),)),
            F(2, turn="side", mirror=True, eyes="wide"), F(1, eyes="wide", lift=3),
            F(5, eyes="happy", lflip=1, rflip=2, fx=(("heart",),))]


@trick("Get dizzy", 0.4)
def dizzy(r):
    return [F(2, rot=0.18 if i % 2 else -0.18, eyes="dizzy", fx=(("stars", i),), mouth="open" if i % 3 == 0 else "closed")
            for i in range(14)] + [F(2, eyes="blink", squash=1), F(3, eyes="blink"), F(2)]


@trick("Love", 0.5)
def love(r):
    return [F(2, eyes="heart", blush=True, squash=1, fx=(("hearts", i),)) if i % 2 else
            F(2, eyes="heart", blush=True, lift=2, lflip=3, rflip=3, fx=(("hearts", i),)) for i in range(10)] + \
           [F(3, eyes="happy", blush=True)]


@trick("Celebrate", 0.5)
def celebrate(r):
    frames = [F(2, hat="party", fx=(("poof", 0),))]
    t = 0
    for _ in range(2):
        for f in _hop(7, hat="party", lflip=2, rflip=2, eyes="star"):
            pose = dict(f[1])
            pose["fx"] = tuple(pose.get("fx", ())) + (("confetti", t),)
            pose.setdefault("hat", "party")
            frames.append((f[0], pose))
            t += f[0]
    frames += [F(1, hat="party", eyes="happy", lflip=2, rflip=2, fx=(("confetti", t + i),)) for i in range(8)]
    return frames + [F(3, fx=(("poof", 1),)), F(2)]


@trick("Fall asleep", 0)
def doze(r):
    return [F(3, eyes="blink"), F(5, eyes="sleep", squash=1), F(2, eyes="blink"),
            F(4, mouth="wide", eyes="squint", lflip=2, rflip=2, squash=-1),
            F(4, eyes="sleep", squash=1, rot=0.1), F(4, eyes="sleep", squash=1, rot=0.05,
                                                     fx=(("zzz", 1),))]


@trick("Wake up", 0)
def surprised(r):
    return [F(1, squash=1, eyes="wide"), F(3, lift=6, eyes="wide", mouth="wide", lflip=2, rflip=2, fx=(("!",),)),
            F(2, lift=3, eyes="wide", fx=(("!",),)), F(1, squash=1), F(4, eyes="wide", fx=(("!",),)),
            F(2, eyes="blink"), F(3, eyes="happy", rflip=1)]


@trick("Drop in", 0)
def greet(r):
    return [F(1, lift=40), F(1, lift=30, lflip=2, rflip=2), F(1, lift=20, lflip=2, rflip=2),
            F(1, lift=10, lflip=1, rflip=1), F(1, squash=2, fx=(("dust", 0),)),
            F(2, squash=1, fx=(("dust", 1),)), F(2, fx=(("dust", 2),))] + wave(r)


@trick("Say goodbye", 0)
def goodbye(r):
    return wave(r) + [F(2, squash=1), F(1, lift=6, squash=-1, eyes="happy", lflip=2, rflip=2),
                      F(1, lift=16, eyes="happy"), F(1, lift=30), F(1, lift=48), F(2, lift=70)]


@trick("Land", 0)
def land(r):
    return [F(1, squash=2, fx=(("dust", 0),)), F(2, squash=1, eyes="squint", fx=(("dust", 1),)),
            F(2, fx=(("dust", 2),)), F(2, eyes="blink")]


@trick("Feel sad", 0)
def sad(r):
    return [F(3, eyes="wide", fx=(("?",),)), F(14, eyes="sad", squash=1, look=(0, 1), fx=(("sweat",),)),
            F(3, eyes="blink", squash=1), F(4, eyes="sad", rflip=3)]


@trick("Get petted", 0)
def pet(r):
    return [F(2, eyes="happy", blush=True, squash=1), F(2, eyes="happy", blush=True, rot=0.08),
            F(2, eyes="happy", blush=True, rot=-0.08), F(2, eyes="happy", blush=True, rot=0.08),
            F(6, eyes="heart", blush=True, fx=(("hearts", 0),)),
            F(4, eyes="heart", blush=True, fx=(("hearts", 3),)), F(2, eyes="happy")]


@trick("Boing", 0)
def boing(r):
    return [F(1, squash=1), F(1, lift=3, squash=-1, eyes="happy"), F(1, lift=1), F(1, squash=1), F(1)]


# reactions picked at random for finished tasks
DONE_TRICKS = ["cheer", "hop", "wave", "spin", "boing"]


def build(name, rng=None, **kw):
    return TRICKS[name][1](rng or random.Random(), **kw)


def pick_idle(rng, can_move):
    names = [n for n, (_, _, w, moves) in TRICKS.items() if w > 0 and (can_move or not moves)]
    weights = [TRICKS[n][2] for n in names]
    return rng.choices(names, weights)[0]
