"""Original chibi-style school kids: big heads, big shiny eyes, rosy cheeks, school uniform.
Each kid can show an emotion: happy, excited, surprised, thinking, grumpy, worried."""
from __future__ import annotations

import math

OUT = (60, 40, 50)
SKIN = {"light": (255, 226, 205), "tan": (238, 196, 160), "brown": (196, 145, 108)}

KIDS = {
    "leo": {"desc": "Leo, a curious 9-year-old boy who asks 'but WHY?' about everything and loves experiments",
            "voice": "en-US-AnaNeural", "gender": "f", "pitch": "+5Hz", "rate": "+5%", "en_pitch": "-4Hz",
            "skin": "light", "hair": (120, 70, 45), "style": "short", "eyes": (90, 55, 35),
            "bottom": "shorts", "plaid": (120, 160, 210), "vest": (70, 90, 150), "shoes": (220, 70, 70)},
    "maya": {"desc": "Maya, a clever 10-year-old girl, quick with facts, a little bossy, loves quizzes",
             "voice": "en-US-EmmaNeural", "gender": "f", "pitch": "+18Hz", "rate": "+5%", "en_pitch": "+14Hz",
             "skin": "tan", "hair": (45, 30, 30), "style": "ponytails", "eyes": (60, 35, 25), "bow": (255, 110, 150),
             "bottom": "skirt", "plaid": (210, 120, 150), "vest": (110, 70, 140), "shoes": (90, 60, 160)},
    "arjun": {"desc": "Arjun, a funny 8-year-old boy with curly hair, always hungry, makes food comparisons",
              "voice": "en-US-AnaNeural", "gender": "f", "pitch": "+0Hz", "rate": "+8%", "en_pitch": "-8Hz",
              "skin": "brown", "hair": (30, 22, 20), "style": "curly", "eyes": (50, 30, 20),
              "bottom": "shorts", "plaid": (100, 150, 110), "vest": (60, 110, 80), "shoes": (240, 160, 40)},
    "noor": {"desc": "Noor, a kind, brave 9-year-old girl in a hijab who loves space and animals",
             "voice": "en-US-AvaNeural", "gender": "f", "pitch": "+15Hz", "rate": "+0%", "en_pitch": "+12Hz",
             "skin": "light", "hair": None, "style": "hijab", "hijab": (120, 190, 230), "eyes": (70, 45, 30),
             "bottom": "skirt", "plaid": (120, 170, 220), "vest": (60, 100, 160), "shoes": (230, 90, 110)},
}

POSE = {"happy": "wave", "excited": "wave", "surprised": "hands_up", "thinking": "chin",
        "grumpy": "cross", "worried": "hands_up", "explaining": "point"}


def _arm(ctx, d, u, S, shoulder, hand, sleeve, skin, w=24):
    sx, sy = u(*shoulder)
    hx, hy = u(*hand)
    mx, my = sx + (hx - sx) * 0.45, sy + (hy - sy) * 0.45
    ctx.line(d, [(sx, sy), (mx, my)], sleeve, w * S)
    ctx.line(d, [(mx, my), (hx, hy)], skin, (w - 6) * S)
    ctx.circle(d, hx, hy, 13 * S, skin, outline=OUT, width=3 * S)


def draw_kid(name, d, ctx, t, talking, bx, by, S, emotion="happy"):
    k = KIDS[name]
    skin = SKIN[k["skin"]]
    emotion = emotion if emotion in POSE else "happy"
    pose = "point" if (talking and emotion == "happy" and int(t / 2.5) % 2) else POSE[emotion]
    bob = math.sin(t * (6 if emotion == "excited" else 2.2)) * (10 if emotion == "excited" else 4)
    u = lambda x, y: (bx + x * S, by + (y + bob) * S)  # noqa: E731
    shirt = (250, 250, 252)

    # ---- legs + shoes
    for sgn in (-1, 1):
        ctx.rect(d, *u(sgn * 22 - 10, 120), *u(sgn * 22 + 10, 165), skin)
        ctx.rect(d, *u(sgn * 22 - 11, 150), *u(sgn * 22 + 11, 168), (255, 255, 255))
        ctx.ellipse(d, *u(sgn * 26, 175), 22 * S, 12 * S, k["shoes"], outline=OUT, width=3 * S)
    # ---- shorts / skirt (plaid)
    if k["bottom"] == "skirt":
        ctx.poly(d, [u(-50, 82), u(50, 82), u(70, 135), u(-70, 135)], k["plaid"], outline=OUT, width=3 * S)
        lines_x = range(-60, 61, 20)
    else:
        ctx.rect(d, *u(-50, 82), *u(50, 130), k["plaid"], r=6 * S, outline=OUT, width=3 * S)
        ctx.line(d, [u(0, 100), u(0, 130)], OUT, 3 * S)
        lines_x = range(-40, 41, 20)
    dark = tuple(max(0, c - 45) for c in k["plaid"])
    for x in lines_x:
        ctx.line(d, [u(x, 84), u(x * 1.15, 132)], dark, 3 * S)
    ctx.line(d, [u(-50, 108), u(50, 108)], dark, 3 * S)

    # ---- body: shirt + vest + tie
    ctx.rect(d, *u(-55, 0), *u(55, 92), shirt, r=18 * S, outline=OUT, width=3 * S)
    ctx.poly(d, [u(-50, 12), u(-14, 12), u(0, 52), u(14, 12), u(50, 12), u(48, 92), u(-48, 92)], k["vest"])
    ctx.line(d, [u(-14, 12), u(0, 52), u(14, 12)], OUT, 3 * S)
    ctx.poly(d, [u(-8, 5), u(8, 5), u(5, 16), u(-5, 16)], k["plaid"])
    ctx.poly(d, [u(-5, 16), u(5, 16), u(9, 50), u(0, 60), u(-9, 50)], k["plaid"], outline=OUT, width=2 * S)
    ctx.poly(d, [u(-22, -2), u(0, 8), u(-6, 18)], shirt, outline=OUT, width=2 * S)  # collar
    ctx.poly(d, [u(22, -2), u(0, 8), u(6, 18)], shirt, outline=OUT, width=2 * S)

    # ---- arms (behind-head poses drawn later)
    wav = math.sin(t * 9) * 18
    L, R = (-50, 18), (50, 18)
    if pose == "cross":
        for sgn in (-1, 1):
            ctx.line(d, [u(sgn * 55, 18), u(sgn * 58, 40)], shirt, 26 * S)
        ctx.line(d, [u(-58, 40), u(40, 52)], OUT, 22 * S)
        ctx.line(d, [u(-58, 40), u(40, 52)], skin, 17 * S)
        ctx.line(d, [u(58, 34), u(-40, 46)], OUT, 22 * S)
        ctx.line(d, [u(58, 34), u(-40, 46)], skin, 17 * S)
        ctx.circle(d, *u(44, 52), 12 * S, skin, outline=OUT, width=3 * S)
        ctx.circle(d, *u(-44, 46), 12 * S, skin, outline=OUT, width=3 * S)
    elif pose == "wave":
        _arm(ctx, d, u, S, L, (-72, 80), shirt, skin)
        _arm(ctx, d, u, S, R, (95 + wav * 0.4, -40 + wav * 0.2), shirt, skin)
    elif pose == "point":
        _arm(ctx, d, u, S, L, (-72, 80), shirt, skin)
        _arm(ctx, d, u, S, R, (120, 10 + math.sin(t * 3) * 6), shirt, skin)
        ctx.line(d, [u(130, 8), u(150, 4)], skin, 9 * S)
    elif pose == "chin":
        _arm(ctx, d, u, S, L, (-72, 80), shirt, skin)
        _arm(ctx, d, u, S, R, (30, -28), shirt, skin)
    elif pose == "hands_up":
        _arm(ctx, d, u, S, L, (-95, -55 - wav * 0.2), shirt, skin)
        _arm(ctx, d, u, S, R, (95, -55 + wav * 0.2), shirt, skin)

    # ---- head
    hx, hy, hr = 0, -95, 100
    style = k["style"]
    hair = k["hair"]
    if style == "hijab":
        ctx.poly(d, [u(-70, -40), u(70, -40), u(78, 22), u(0, 34), u(-78, 22)], k["hijab"], outline=OUT, width=3 * S)
        ctx.ellipse(d, *u(0, -95), 116 * S, 118 * S, k["hijab"], outline=OUT, width=4 * S)
    elif style == "ponytails":
        for sgn in (-1, 1):
            sw = math.sin(t * 3 + sgn) * 6
            ctx.ellipse(d, *u(sgn * (118 + sw * 0.3), -55 + sw), 34 * S, 55 * S, hair, outline=OUT, width=3 * S)
            ctx.circle(d, *u(sgn * 98, -95), 16 * S, k["bow"], outline=OUT, width=3 * S)
    if style != "hijab":
        for sgn in (-1, 1):  # ears
            ctx.circle(d, *u(sgn * 96, -80), 20 * S, skin, outline=OUT, width=3 * S)
    if style == "hijab":
        ctx.ellipse(d, *u(0, -80), 84 * S, 90 * S, skin)
    else:
        ctx.ellipse(d, *u(hx, hy), hr * S, hr * 0.95 * S, skin, outline=OUT, width=4 * S)

    # hair on top
    if style == "short":
        ctx.poly(d, [u(-100, -95), u(-92, -150), u(-50, -192), u(10, -200), u(70, -180), u(102, -130), u(100, -95),
                     u(78, -130), u(55, -118), u(40, -140), u(10, -122), u(-15, -145), u(-40, -120), u(-70, -135)],
                 hair, outline=OUT, width=3 * S)
        ctx.poly(d, [u(10, -200), u(35, -228), u(28, -195)], hair, outline=OUT, width=3 * S)
    elif style == "ponytails":
        ctx.poly(d, [u(-102, -85), u(-95, -150), u(-55, -190), u(0, -198), u(55, -190), u(95, -150), u(102, -85),
                     u(80, -120), u(30, -140), u(0, -125), u(-30, -140), u(-80, -120)], hair, outline=OUT, width=3 * S)
    elif style == "curly":
        for i in range(17):
            a = math.pi + i / 16 * math.pi
            ctx.circle(d, *u(math.cos(a) * 92, -105 + math.sin(a) * 88), 30 * S, hair)
        for x in (-70, -35, 0, 35, 70):
            ctx.circle(d, *u(x, -150 + abs(x) * 0.5), 30 * S, hair)
        for x in (-55, -18, 18, 55):
            ctx.circle(d, *u(x, -125), 22 * S, hair)
    elif style == "hijab":
        ctx.poly(d, [u(-86, -110), u(-60, -160), u(0, -176), u(60, -160), u(86, -110), u(40, -150), u(0, -158),
                     u(-40, -150)], k["hijab"])
        ctx.line(d, [u(-84, -112), u(-40, -148), u(0, -156), u(40, -148), u(84, -112)],
                 tuple(max(0, c - 40) for c in k["hijab"]), 4 * S)

    # ---- face
    blink = ((t + sum(name.encode()) % 7) % 4.1) < 0.12
    look_x = {"thinking": 0.5}.get(emotion, math.sin(t * 0.8) * 0.4)
    look_y = -0.5 if emotion == "thinking" else 0.1
    er = 1.25 if emotion == "surprised" else 1.0
    for sgn in (-1, 1):
        ex, ey = u(sgn * 40, -78)
        if blink:
            ctx.line(d, [(ex - 18 * S, ey), (ex + 18 * S, ey)], OUT, 5 * S)
        else:
            ctx.ellipse(d, ex, ey, 19 * S * er, 25 * S * er, (255, 255, 255), outline=OUT, width=3 * S)
            px, py = ex + look_x * 6 * S, ey + look_y * 8 * S
            ctx.ellipse(d, px, py + 2 * S, 15 * S * er, 20 * S * er, k["eyes"])
            ctx.ellipse(d, px, py + 4 * S, 8 * S * er, 11 * S * er, (25, 15, 15))
            ctx.circle(d, px - 6 * S, py - 7 * S, 6 * S, (255, 255, 255))
            ctx.circle(d, px + 5 * S, py + 8 * S, 3 * S, (255, 255, 255))
        # eyebrows by emotion: (inner y, outer y)
        inner, outer = {"grumpy": (-100, -118), "worried": (-120, -106), "surprised": (-126, -122),
                        "thinking": ((-120, -124) if sgn > 0 else (-110, -110))}.get(emotion, (-112, -114))
        brow_col = tuple(max(0, c - 20) for c in (hair or (60, 40, 30)))
        ctx.line(d, [u(sgn * 22, inner), u(sgn * 58, outer)], brow_col, 7 * S)
        ctx.ellipse(d, *u(sgn * 66, -45), 18 * S, 10 * S, (255, 150, 160))  # blush
    # mouth
    mx, my = u(0, -32)
    if talking:
        o = 0.35 + 0.65 * abs(math.sin(t * 11))
        ctx.ellipse(d, mx, my + 4 * S, 16 * S, (6 + 14 * o) * S, (150, 40, 60), outline=OUT, width=3 * S)
        ctx.ellipse(d, mx, my + (8 + 8 * o) * S, 9 * S, 5 * o * S + 1, (255, 130, 150))
    elif emotion == "surprised" or emotion == "thinking":
        ctx.ellipse(d, mx + (8 * S if emotion == "thinking" else 0), my, 8 * S, 10 * S, (150, 40, 60), outline=OUT, width=3 * S)
    elif emotion in ("grumpy", "worried"):
        X, Y = ctx.P(mx, my + 6 * S)
        d.arc([X - 16 * S * ctx.s, Y - 4 * S * ctx.s, X + 16 * S * ctx.s, Y + 20 * S * ctx.s], 200, 340,
              fill=OUT, width=max(2, int(4 * S * ctx.s)))
    else:
        X, Y = ctx.P(mx, my - 10 * S)
        d.arc([X - 18 * S * ctx.s, Y - 10 * S * ctx.s, X + 18 * S * ctx.s, Y + 16 * S * ctx.s], 20, 160,
              fill=OUT, width=max(2, int(4 * S * ctx.s)))
    if emotion == "thinking":  # little thought bubbles
        for i, r in enumerate((8, 12, 18)):
            ctx.circle(d, *u(80 + i * 25, -200 - i * 30 + math.sin(t * 2 + i) * 5), r * S, (255, 255, 255), outline=OUT, width=2 * S)
