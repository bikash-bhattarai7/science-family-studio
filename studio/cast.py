"""The show's original cartoon cast. Each character has a personality (used by the
AI writer), its own English voice, and talks/blinks when it is speaking."""
from __future__ import annotations

import math

from .visuals import Ctx, draw_mascot, lerp_col

OUTLINE = (40, 30, 60)

CAST = {
    "zippy": {"desc": "Zippy, a cheerful little robot and the show's host; curious, kind, loves saying 'Let's find out!'",
              "voice": "en-US-AriaNeural", "gender": "f", "pitch": "+0Hz", "rate": "+0%"},
    "hoot": {"desc": "Professor Hoot, a wise purple owl in a graduation cap; explains the science clearly, a bit proud, loves big words then explains them",
             "voice": "en-GB-RyanNeural", "gender": "m", "pitch": "-6Hz", "rate": "-5%"},
    "bubbles": {"desc": "Bubbles, a bubbly pink axolotl kid; asks the questions kids ask, gets amazed easily ('Whoa!')",
                "voice": "en-US-AnaNeural", "gender": "f", "pitch": "+25Hz", "rate": "+5%"},
    "sparky": {"desc": "Sparky, a hyper-energetic little comet; super fast talker, loves wow-facts and space, always excited",
               "voice": "en-US-ChristopherNeural", "gender": "m", "pitch": "+15Hz", "rate": "+15%"},
    "rocky": {"desc": "Rocky, a grumpy-but-lovable pebble; sceptical, dry jokes ('Hmph, prove it'), secretly loves science",
              "voice": "en-US-RogerNeural", "gender": "m", "pitch": "-15Hz", "rate": "-8%", "en_pitch": "-8Hz"},
    "dot": {"desc": "Dot, a giggly green cell; tiny but brave, knows about bodies, germs, and living things",
            "voice": "en-AU-NatashaNeural", "gender": "f", "pitch": "+12Hz", "rate": "+8%"},
}


def voice_for(cfg: dict, lang: str, speaker: str | None) -> tuple[str, str, str]:
    """(voice, rate, pitch) for a character in a language. English has a unique voice per
    character; other languages use the language's male/female voice, shifted in pitch and speed."""
    lc = cfg["languages"][lang]
    ch = CAST.get(speaker or "zippy", CAST["zippy"])
    if lang == "en":
        return ch["voice"], ch["rate"], ch.get("en_pitch", "+0Hz")
    voice = lc.get("voice_male" if ch["gender"] == "m" else "voice_female", lc["voice"])
    return voice, ch["rate"], ch["pitch"]


# ---------------------------------------------------------------- parts
def eye(d, ctx, x, y, r, iris, t, look=0.0, blink=False, lid=0.0, lid_col=None):
    if blink:
        ctx.line(d, [(x - r, y), (x + r, y)], OUTLINE, r * 0.22)
        return
    ctx.circle(d, x, y, r, (255, 255, 255), outline=OUTLINE, width=r * 0.12)
    ix = x + look * r * 0.25
    ctx.circle(d, ix, y + r * 0.08, r * 0.55, iris)
    ctx.circle(d, ix, y + r * 0.08, r * 0.3, (15, 15, 25))
    ctx.circle(d, ix - r * 0.18, y - r * 0.12, r * 0.14, (255, 255, 255))
    if lid > 0:  # sleepy / grumpy eyelid
        ctx.poly(d, [(x - r * 1.1, y - r * 1.1), (x + r * 1.1, y - r * 1.1),
                     (x + r * 1.1, y - r + 2 * r * lid), (x - r * 1.1, y - r + 2 * r * lid)], lid_col)
        ctx.line(d, [(x - r * 0.95, y - r + 2 * r * lid), (x + r * 0.95, y - r + 2 * r * lid)], OUTLINE, r * 0.12)


def mouth(d, ctx, x, y, w, talking, t, grumpy=False):
    if talking:
        o = 0.35 + 0.65 * abs(math.sin(t * 11))
        h = w * 0.75 * o
        ctx.ellipse(d, x, y + h * 0.3, w, h + 4, (110, 25, 45), outline=OUTLINE, width=w * 0.08)
        ctx.ellipse(d, x, y + h * 0.75, w * 0.55, h * 0.35, (255, 120, 140))
        if h > w * 0.3:
            ctx.rect(d, x - w * 0.6, y + h * 0.3 - h + 2, x + w * 0.6, y + h * 0.3 - h + w * 0.22, (255, 255, 255))
    else:
        X, Y = ctx.P(x, y - (w * 0.2 if grumpy else w * 0.6))
        R = w * ctx.s
        if grumpy:
            d.arc([X - R * 0.6, Y, X + R * 0.6, Y + R * 0.8], 200, 340, fill=OUTLINE, width=max(2, int(w * 0.12 * ctx.s)))
        else:
            d.arc([X - R, Y - R * 0.6, X + R, Y + R * 0.6], 20, 160, fill=OUTLINE, width=max(2, int(w * 0.12 * ctx.s)))


def _blink(t, seed):
    return ((t + seed * 1.37) % 3.9) < 0.13


# ---------------------------------------------------------------- characters
# each draws centred on (bx, by), roughly 300*S tall, feet near by + 140*S
def hoot(d, ctx, t, talking, bx, by, S):
    u = lambda x, y: (bx + x * S, by + y * S)  # noqa: E731
    flap = math.sin(t * 9) * 12 if talking else math.sin(t * 2) * 3
    for sgn in (-1, 1):
        ctx.ellipse(d, *u(sgn * 115, 50 - flap * sgn * 0.3), 40 * S, 85 * S, (95, 60, 170), outline=OUTLINE, width=5 * S)
    ctx.ellipse(d, *u(-35, 140), 28 * S, 12 * S, (255, 160, 40))
    ctx.ellipse(d, *u(35, 140), 28 * S, 12 * S, (255, 160, 40))
    ctx.ellipse(d, *u(0, 30), 120 * S, 120 * S, (130, 85, 210), outline=OUTLINE, width=6 * S)
    for sgn in (-1, 1):
        ctx.poly(d, [u(sgn * 55, -70), u(sgn * 115, -150), u(sgn * 105, -40)], (130, 85, 210), outline=OUTLINE, width=5 * S)
    ctx.ellipse(d, *u(0, 75), 70 * S, 65 * S, (215, 195, 250))
    for i in range(3):
        for j in (-1, 0, 1):
            x, y = 25 * j, 55 + i * 25
            ctx.line(d, [u(x - 9, y), u(x, y + 8), u(x + 9, y)], (160, 130, 220), 4 * S)
    blink = _blink(t, 1)
    look = math.sin(t * 0.7)
    for sgn in (-1, 1):
        ctx.circle(d, *u(sgn * 48, -25), 54 * S, (255, 175, 60), outline=OUTLINE, width=5 * S)
        eye(d, ctx, *u(sgn * 48, -25), 42 * S, (255, 140, 30), t, look, blink)
    beak_open = (0.3 + 0.7 * abs(math.sin(t * 11))) if talking else 0
    ctx.poly(d, [u(-16, 8), u(16, 8), u(0, 32)], (255, 150, 30), outline=OUTLINE, width=4 * S)
    if beak_open:
        ctx.poly(d, [u(-12, 30), u(12, 30), u(0, 30 + 26 * beak_open)], (230, 120, 20), outline=OUTLINE, width=4 * S)
    # graduation cap
    ctx.poly(d, [u(-85, -112), u(0, -142), u(85, -112), u(0, -82)], (35, 35, 50))
    ctx.rect(d, *u(-40, -112), *u(40, -88), (35, 35, 50))
    sw = math.sin(t * 3) * 10
    ctx.line(d, [u(0, -112), u(70, -112), u(72 + sw * 0.3, -62)], (255, 210, 50), 5 * S)
    ctx.circle(d, *u(72 + sw * 0.3, -58), 9 * S, (255, 210, 50))


def bubbles(d, ctx, t, talking, bx, by, S):
    u = lambda x, y: (bx + x * S, by + y * S)  # noqa: E731
    wag = math.sin(t * 4) * 15
    ctx.poly(d, [u(60, 90), u(170, 60 + wag), u(150, 105 + wag * 0.5), u(60, 125)], (255, 140, 180), outline=OUTLINE, width=5 * S)
    ctx.ellipse(d, *u(0, 95), 85 * S, 55 * S, (255, 160, 195), outline=OUTLINE, width=5 * S)
    for sgn in (-1, 1):
        ctx.ellipse(d, *u(sgn * 45, 140), 22 * S, 12 * S, (255, 140, 180), outline=OUTLINE, width=4 * S)
    # gills
    for sgn in (-1, 1):
        for k, ang in enumerate((-35, -5, 25)):
            a = math.radians(ang + 8 * math.sin(t * 5 + k))
            sx, sy = u(sgn * 120, -25 + k * 18)
            ex = sx + sgn * math.cos(a) * 75 * S
            ey = sy + math.sin(a) * 75 * S
            ctx.line(d, [(sx, sy), (ex, ey)], (225, 60, 140), 14 * S)
            for f in (0.45, 0.75, 1.0):
                ctx.circle(d, sx + (ex - sx) * f, sy + (ey - sy) * f, 10 * S, (240, 90, 160))
    ctx.ellipse(d, *u(0, -15), 135 * S, 95 * S, (255, 175, 205), outline=OUTLINE, width=6 * S)
    blink = _blink(t, 2)
    look = math.sin(t * 1.1)
    for sgn in (-1, 1):
        eye(d, ctx, *u(sgn * 55, -30), 32 * S, (60, 40, 30), t, look, blink)
        ctx.circle(d, *u(sgn * 95, 15), 16 * S, (255, 120, 150))
    mouth(d, ctx, *u(0, 25), 30 * S, talking, t)


def sparky(d, ctx, t, talking, bx, by, S):
    u = lambda x, y: (bx + x * S, by + y * S)  # noqa: E731
    by_hover = math.sin(t * 5) * 10
    u2 = lambda x, y: u(x, y + by_hover)  # noqa: E731
    for k, (col, w, L) in enumerate([((255, 110, 40), 95, 260), ((255, 175, 40), 70, 220), ((255, 240, 130), 42, 170)]):
        pts = [u2(0, -w)]
        for i in range(1, 9):
            f = i / 8
            pts.append(u2(-L * f, -w * (1 - f) - 60 * f + math.sin(t * 8 + f * 5 + k) * 14 * f))
        for i in range(8, -1, -1):
            f = i / 8
            pts.append(u2(-L * f, w * (1 - f) - 60 * f + math.sin(t * 8 + f * 5 + k) * 14 * f))
        ctx.poly(d, pts, col)
    ctx.circle(d, *u2(0, 0), 105 * S, (255, 205, 60), outline=(220, 110, 30), width=7 * S)
    ctx.circle(d, *u2(-35, -50), 22 * S, (255, 235, 140))
    blink = _blink(t, 3)
    for sgn in (-1, 1):
        eye(d, ctx, *u2(sgn * 40, -18), 33 * S, (40, 120, 230), t, 0.6, blink)
        lift = 8 * abs(math.sin(t * 6)) if talking else 0
        ctx.line(d, [u2(sgn * 22, -62 - lift), u2(sgn * 62, -70 - lift)], OUTLINE, 8 * S)
    mouth(d, ctx, *u2(0, 42), 34 * S, talking, t)
    for i in range(4):
        a = t * 3 + i * 1.6
        x, y = u2(math.cos(a) * 150, math.sin(a) * 120)
        r = (6 + 5 * abs(math.sin(t * 6 + i))) * S
        ctx.poly(d, [(x, y - r * 2), (x + r * 0.5, y - r * 0.5), (x + r * 2, y), (x + r * 0.5, y + r * 0.5),
                     (x, y + r * 2), (x - r * 0.5, y + r * 0.5), (x - r * 2, y), (x - r * 0.5, y - r * 0.5)], (255, 250, 200))


def rocky(d, ctx, t, talking, bx, by, S):
    u = lambda x, y: (bx + x * S, by + y * S)  # noqa: E731
    pts = []
    for i in range(24):
        a = i / 24 * 2 * math.pi
        r = 125 + 12 * math.sin(a * 3 + 1) + 7 * math.sin(a * 5)
        pts.append(u(math.cos(a) * r * 1.12, 30 + math.sin(a) * r * 0.9))
    ctx.ellipse(d, *u(0, 140), 120 * S, 14 * S, (90, 90, 100))
    ctx.poly(d, pts, (160, 158, 170), outline=OUTLINE, width=6 * S)
    for x, y, r in [(-80, 80, 14), (70, 100, 10), (95, 0, 8), (-60, -40, 7)]:
        ctx.circle(d, *u(x, y), r * S, (130, 128, 140))
    for i in range(5):
        a = -1.9 + i * 0.25
        ctx.line(d, [u(-20 + i * 10, -75), u(-20 + i * 10 + math.cos(a) * 30, -75 + math.sin(a) * 30)], (90, 170, 80), 9 * S)
    blink = _blink(t, 4)
    for sgn in (-1, 1):
        eye(d, ctx, *u(sgn * 45, -5), 30 * S, (110, 80, 50), t, -0.4, blink, lid=0.42, lid_col=(160, 158, 170))
        lift = 10 * abs(math.sin(t * 5)) if talking else 0
        ctx.line(d, [u(sgn * 15, -38 - lift * 0.5), u(sgn * 80, -55 - lift)], (60, 55, 70), 16 * S)
    mouth(d, ctx, *u(0, 60), 28 * S, talking, t, grumpy=True)


def dot(d, ctx, t, talking, bx, by, S):
    u = lambda x, y: (bx + x * S, by + y * S)  # noqa: E731
    squish = 1 + 0.05 * math.sin(t * 4)
    for ring, col, k in [(0, (120, 210, 130), 1.0), (1, (160, 240, 170), 0.88)]:
        pts = []
        for i in range(36):
            a = i / 36 * 2 * math.pi
            r = (115 + 8 * math.sin(a * 5 + t * 3)) * k
            pts.append(u(math.cos(a) * r * squish, 25 + math.sin(a) * r / squish))
        ctx.poly(d, pts, col, outline=OUTLINE if ring == 0 else None, width=6 * S)
    ctx.circle(d, *u(55, 75), 24 * S, (150, 110, 220), outline=(110, 70, 180), width=4 * S)
    for x, y in [(-70, 70), (-40, 100), (75, 15), (-85, 0)]:
        ctx.ellipse(d, *u(x, y), 12 * S, 6 * S, (240, 170, 80))
    blink = _blink(t, 5)
    for sgn in (-1, 1):
        eye(d, ctx, *u(sgn * 34, -10), 30 * S, (30, 140, 90), t, math.sin(t), blink)
    mouth(d, ctx, *u(0, 40), 24 * S, talking, t)
    for sgn in (-1, 1):  # tiny waving arms
        a = math.radians(sgn * (120 + 20 * math.sin(t * 6 + sgn)))
        sx, sy = u(sgn * 108, 40)
        ctx.line(d, [(sx, sy), (sx + math.sin(a) * 45 * S, sy - math.cos(a) * 45 * S)], (120, 210, 130), 12 * S)


def zippy(d, ctx, t, talking, bx, by, S):
    draw_mascot(d, ctx, t, talking, scale=S, pos=(bx, by))


DRAW = {"zippy": zippy, "hoot": hoot, "bubbles": bubbles, "sparky": sparky, "rocky": rocky, "dot": dot}


# ---------------------------------------------------------------- placement
def draw_speaker(d, ctx: Ctx, name: str, t: float, talking: bool) -> None:
    """Speaking character in the corner (landscape) or bottom centre (Shorts)."""
    fn = DRAW.get(name, zippy)
    if ctx.portrait:
        fn(d, ctx, t, talking, 0, ctx.half_h - 220, 1.05)
    else:
        fn(d, ctx, t, talking, ctx.half_w - 200, ctx.half_h - 185, 1.0)


def draw_lineup(d, ctx: Ctx, t: float, speaker: str | None, talking: bool) -> None:
    """Whole cast together (intro / outro). The speaker bounces a little."""
    names = list(DRAW)
    if ctx.portrait:
        spots = [(-300, 120), (0, 120), (300, 120), (-300, 520), (0, 520), (300, 520)]
        S = 0.85
    else:
        n = len(names)
        span = min(ctx.half_w * 1.75, 1650)
        spots = [(-span / 2 + i * span / (n - 1), 230) for i in range(n)]
        S = 0.8
    for i, (name, (x, y)) in enumerate(zip(names, spots)):
        hop = -abs(math.sin(t * 5)) * 18 if name == speaker and talking else math.sin(t * 2 + i) * 5
        DRAW[name](d, ctx, t + i * 0.7, talking and name == speaker, x, y + hop, S)
