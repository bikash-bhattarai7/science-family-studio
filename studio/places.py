"""Natural cartoon locations (classroom, garden, playground...) behind the characters.
The science animation is shown inside a whiteboard / imagination window in the scene."""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

from .visuals import Ctx, cloud, gradient, lerp_col, sun

OUT = (70, 50, 50)


def _ground(ctx):
    return ctx.half_h * 0.42


def _tree(ctx, d, x, y, k=1.0, col=(80, 170, 80)):
    ctx.rect(d, x - 22 * k, y - 160 * k, x + 22 * k, y, (130, 90, 60))
    for dx, dy, r in [(0, -230, 110), (-80, -170, 85), (80, -170, 85), (-40, -280, 70), (45, -290, 70)]:
        ctx.circle(d, x + dx * k, y + dy * k, r * k, lerp_col(col, (40, 120, 50), 0.15 if dy > -200 else 0))


def _flowers(ctx, d, y, seed=1, n=18):
    rnd = random.Random(seed)
    for _ in range(n):
        x = rnd.uniform(-ctx.half_w, ctx.half_w)
        yy = y + rnd.uniform(10, ctx.half_h - y - 10)
        c = rnd.choice([(255, 110, 150), (255, 210, 60), (255, 255, 255), (170, 120, 255), (255, 150, 60)])
        ctx.line(d, [(x, yy), (x, yy - 26)], (70, 150, 60), 4)
        for a in range(5):
            ang = a * 2 * math.pi / 5
            ctx.circle(d, x + math.cos(ang) * 9, yy - 30 + math.sin(ang) * 9, 7, c)
        ctx.circle(d, x, yy - 30, 6, (255, 230, 90))


def _window(ctx, d, x0, y0, x1, y1, night=False):
    ctx.rect(d, x0 - 14, y0 - 14, x1 + 14, y1 + 14, (250, 250, 250), r=8)
    ctx.rect(d, x0, y0, x1, y1, (25, 30, 70) if night else (140, 205, 250))
    if not night:
        ctx.ellipse(d, (x0 + x1) / 2, y1 + 40, (x1 - x0) * 0.7, 90, (110, 190, 90))
    ctx.line(d, [((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], (250, 250, 250), 12)
    ctx.line(d, [(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], (250, 250, 250), 12)


# ---------------------------------------------------------------- static backdrops
def st_classroom(d, ctx):
    g = _ground(ctx)
    ctx.rect(d, -ctx.half_w - 5, -ctx.half_h - 5, ctx.half_w + 5, g, (252, 236, 200))
    ctx.rect(d, -ctx.half_w - 5, g - 120, ctx.half_w + 5, g, (180, 215, 190))  # wall panel
    ctx.rect(d, -ctx.half_w - 5, g, ctx.half_w + 5, ctx.half_h + 5, (205, 160, 110))
    for i in range(-12, 13):
        ctx.line(d, [(i * 90, g), (i * 140, ctx.half_h + 5)], (185, 140, 95), 3)
    ctx.line(d, [(-ctx.half_w, g), (ctx.half_w, g)], (150, 110, 80), 10)
    # bunting
    for i in range(24):
        x = -ctx.half_w + i * (ctx.half_w * 2 / 23)
        y = -ctx.half_h + 40 + 18 * math.sin(i / 23 * math.pi)
        ctx.poly(d, [(x - 28, y), (x + 28, y), (x, y + 50)], [(255, 120, 120), (255, 210, 80), (120, 200, 255), (140, 220, 140)][i % 4])
    ctx.line(d, [(-ctx.half_w, -ctx.half_h + 40), (ctx.half_w, -ctx.half_h + 40)], (120, 90, 70), 3)
    if not ctx.portrait:
        _window(ctx, d, 470, -380, 820, -110)
    # wall clock
    cx, cy = (-ctx.half_w + 120, -ctx.half_h + 170) if not ctx.portrait else (ctx.half_w - 130, -ctx.half_h + 170)
    ctx.circle(d, cx, cy, 60, (255, 255, 255), outline=OUT, width=8)
    ctx.line(d, [(cx, cy), (cx, cy - 40)], OUT, 6)
    ctx.line(d, [(cx, cy), (cx + 28, cy + 10)], OUT, 6)
    # desks
    for x in ([-700, -380] if not ctx.portrait else [-330]):
        y = ctx.half_h - 60
        ctx.rect(d, x - 140, y - 110, x + 140, y - 80, (215, 165, 110), r=6, outline=OUT, width=3)
        ctx.rect(d, x - 120, y - 80, x - 105, y + 40, (150, 150, 160))
        ctx.rect(d, x + 105, y - 80, x + 120, y + 40, (150, 150, 160))
        ctx.rect(d, x - 60, y - 140, x + 20, y - 110, (120, 180, 255), r=4)  # book
    # plant
    px = ctx.half_w - 90 if ctx.portrait else -ctx.half_w + 90
    ctx.rect(d, px - 40, g - 90, px + 40, g, (220, 120, 80), r=8)
    for a in range(-3, 4):
        ctx.ellipse(d, px + a * 20, g - 130 - abs(a) * -8, 18, 45, (80, 170, 90))


def st_garden(d, ctx):
    g = _ground(ctx)
    ctx.ellipse(d, -500, g + 40, 900, 260, (150, 210, 130))
    ctx.ellipse(d, 600, g + 60, 900, 240, (130, 200, 120))
    for x, k in [(-ctx.half_w + 150, 1.1), (ctx.half_w - 140, 0.9), (-80, 0.7)]:
        _tree(ctx, d, x, g + 10, k)
    # fence
    for i in range(-30, 31):
        x = i * 60
        ctx.poly(d, [(x - 22, g + 70), (x + 22, g + 70), (x + 22, g - 30), (x, g - 55), (x - 22, g - 30)], (250, 245, 235), outline=(200, 190, 180), width=2)
    ctx.rect(d, -ctx.half_w - 5, g - 10, ctx.half_w + 5, g + 5, (240, 230, 215))
    ctx.rect(d, -ctx.half_w - 5, g + 70, ctx.half_w + 5, ctx.half_h + 5, (120, 200, 90))
    ctx.poly(d, [(-140, ctx.half_h + 5), (140, ctx.half_h + 5), (60, g + 70), (-60, g + 70)], (230, 205, 160))
    _flowers(ctx, d, g + 80, 3, 26)


def st_playground(d, ctx):
    g = _ground(ctx)
    for x, k in [(-ctx.half_w + 120, 1.0), (ctx.half_w - 120, 1.1)]:
        _tree(ctx, d, x, g + 20, k)
    ctx.rect(d, -ctx.half_w - 5, g, ctx.half_w + 5, ctx.half_h + 5, (130, 205, 100))
    sx = -ctx.half_w * 0.45
    # slide
    ctx.line(d, [(sx - 90, g + 80), (sx - 90, g - 200)], (240, 90, 90), 14)
    ctx.line(d, [(sx - 30, g + 80), (sx - 30, g - 200)], (240, 90, 90), 14)
    for j in range(6):
        ctx.line(d, [(sx - 90, g + 60 - j * 45), (sx - 30, g + 60 - j * 45)], (240, 90, 90), 8)
    ctx.rect(d, sx - 100, g - 215, sx + 20, g - 190, (90, 150, 240))
    ctx.poly(d, [(sx + 10, g - 210), (sx + 50, g - 210), (sx + 260, g + 70), (sx + 220, g + 80)], (255, 200, 60), outline=OUT, width=3)
    # sandbox
    ctx.rect(d, -120, g + 120, 220, g + 200, (230, 205, 150), r=10, outline=(170, 120, 80), width=10)
    ctx.circle(d, 30, g + 150, 26, (255, 120, 120))


def st_school_yard(d, ctx):
    g = _ground(ctx)
    bx0, bx1 = -ctx.half_w * 0.85, ctx.half_w * 0.85
    top = g - 420
    ctx.poly(d, [(bx0 - 30, top), (0, top - 160), (bx1 + 30, top)], (200, 80, 70))
    ctx.rect(d, bx0, top, bx1, g, (230, 140, 110))
    for row in range(2):
        for i in range(8):
            x = bx0 + 70 + i * (bx1 - bx0 - 140) / 7
            y = top + 70 + row * 150
            ctx.rect(d, x - 40, y - 40, x + 40, y + 50, (170, 220, 255), outline=(255, 255, 255), width=6)
    ctx.rect(d, -90, g - 190, 90, g, (140, 90, 60))
    ctx.circle(d, 0, top - 60, 50, (255, 255, 255), outline=OUT, width=6)
    ctx.line(d, [(0, top - 60), (0, top - 95)], OUT, 5)
    ctx.line(d, [(0, top - 60), (25, top - 50)], OUT, 5)
    ctx.rect(d, -ctx.half_w - 5, g, ctx.half_w + 5, ctx.half_h + 5, (200, 200, 205))
    ctx.rect(d, -ctx.half_w - 5, g + 110, ctx.half_w + 5, ctx.half_h + 5, (130, 200, 100))
    for x in range(-int(ctx.half_w), int(ctx.half_w), 180):
        ctx.circle(d, x, g + 10, 55, (90, 170, 90))
    for i in range(5):  # hopscotch
        ctx.rect(d, -ctx.half_w + 80 + i * 70, g + 40, -ctx.half_w + 140 + i * 70, g + 100, None, outline=(255, 255, 255), width=4)


def st_kitchen(d, ctx):
    g = _ground(ctx)
    ctx.rect(d, -ctx.half_w - 5, -ctx.half_h - 5, ctx.half_w + 5, g, (255, 245, 225))
    for i in range(-20, 21):
        for j in range(4):
            ctx.rect(d, i * 70, g - 330 + j * 70, i * 70 + 66, g - 330 + j * 70 + 66, (225, 240, 245))
    ctx.rect(d, -ctx.half_w - 5, g - 70, ctx.half_w + 5, g - 40, (180, 140, 110))  # counter top
    ctx.rect(d, -ctx.half_w - 5, g - 40, ctx.half_w + 5, ctx.half_h + 5, (120, 175, 200))
    for i in range(-10, 11):
        ctx.rect(d, i * 200 + 10, g - 20, i * 200 + 190, ctx.half_h - 20, None, outline=(95, 150, 180), width=4)
        ctx.circle(d, i * 200 + 170, g + 60, 9, (240, 240, 240))
    fx = ctx.half_w - 160 if not ctx.portrait else -ctx.half_w + 140
    ctx.rect(d, fx - 120, g - 520, fx + 120, ctx.half_h, (240, 245, 250), r=20, outline=(170, 180, 190), width=5)
    ctx.line(d, [(fx - 120, g - 250), (fx + 120, g - 250)], (170, 180, 190), 5)
    ctx.circle(d, -260, g - 110, 60, (240, 240, 245), outline=OUT, width=4)  # fruit bowl
    for x, c in [(-290, (255, 80, 80)), (-250, (255, 200, 60)), (-215, (120, 200, 80))]:
        ctx.circle(d, x, g - 140, 30, c)


def st_bedroom_night(d, ctx):
    g = _ground(ctx)
    ctx.rect(d, -ctx.half_w - 5, g, ctx.half_w + 5, ctx.half_h + 5, (110, 80, 120))
    ctx.ellipse(d, 0, g + 170, 500, 90, (200, 120, 170))
    if not ctx.portrait:
        _window(ctx, d, 460, -400, 820, -100, night=True)
        ctx.circle(d, 720, -320, 45, (255, 245, 200))
    # bed
    bx = -ctx.half_w * 0.55
    ctx.rect(d, bx - 260, g - 40, bx + 260, g + 120, (150, 100, 70), r=12)
    ctx.rect(d, bx - 250, g - 90, bx + 250, g + 30, (120, 170, 255), r=20)
    ctx.rect(d, bx - 240, g - 120, bx - 120, g - 70, (255, 255, 255), r=20)
    ctx.rect(d, bx - 285, g - 220, bx - 250, g + 120, (150, 100, 70), r=10)
    # lamp
    lx = bx + 360
    ctx.rect(d, lx - 50, g - 20, lx + 50, g + 100, (190, 140, 100))
    ctx.ellipse(d, lx, g - 120, 140, 110, (90, 80, 100))
    ctx.line(d, [(lx, g - 20), (lx, g - 110)], (230, 230, 230), 8)
    ctx.poly(d, [(lx - 60, g - 110), (lx + 60, g - 110), (lx + 40, g - 170), (lx - 40, g - 170)], (255, 220, 120))


def st_lab(d, ctx):
    g = _ground(ctx)
    ctx.rect(d, -ctx.half_w - 5, g, ctx.half_w + 5, ctx.half_h + 5, (210, 215, 225))
    for i in range(-14, 15):
        ctx.line(d, [(i * 100, g), (i * 100, ctx.half_h)], (190, 195, 205), 3)
    for row in (g - 330, g - 200):  # shelves with flasks
        ctx.rect(d, -ctx.half_w - 5, row, ctx.half_w + 5, row + 16, (150, 110, 80))
        rnd = random.Random(int(row))
        x = -ctx.half_w + 60
        while x < ctx.half_w:
            c = rnd.choice([(255, 100, 140), (90, 200, 255), (120, 230, 120), (255, 200, 60), (180, 120, 255)])
            ctx.rect(d, x - 18, row - 70, x + 18, row, (230, 240, 250), r=6)
            ctx.rect(d, x - 18, row - 40, x + 18, row, c, r=6)
            x += rnd.uniform(70, 130)
    ctx.rect(d, -ctx.half_w - 5, g + 40, ctx.half_w + 5, g + 70, (60, 70, 90))  # bench


def st_beach(d, ctx):
    g = _ground(ctx)
    ctx.rect(d, -ctx.half_w - 5, g - 140, ctx.half_w + 5, g + 40, (60, 160, 220))
    ctx.rect(d, -ctx.half_w - 5, g + 30, ctx.half_w + 5, ctx.half_h + 5, (245, 220, 160))
    px = -ctx.half_w + 160
    ctx.line(d, [(px, g + 60), (px + 40, g - 260)], (150, 100, 60), 30)
    for a in range(6):
        ang = -math.pi / 2 + (a - 2.5) * 0.55
        ctx.ellipse(d, px + 40 + math.cos(ang) * 110, g - 270 + math.sin(ang) * 60, 110, 30, (70, 170, 80))
    ux = 240
    ctx.line(d, [(ux, g + 160), (ux, g - 120)], (240, 240, 240), 10)
    ctx.poly(d, [(ux - 200, g - 100), (ux, g - 190), (ux + 200, g - 100)], (255, 110, 110))
    ctx.poly(d, [(ux - 70, g - 100), (ux, g - 190), (ux + 70, g - 100)], (255, 255, 255))
    ctx.rect(d, -120, g + 160, 20, g + 230, (220, 180, 110))  # sandcastle
    ctx.rect(d, -100, g + 110, 0, g + 160, (220, 180, 110))


PLACES = {
    "classroom": {"static": st_classroom, "sky": ((252, 236, 200), (252, 236, 200)), "panel": "board",
                  "desc": "school classroom (whiteboard shows the science)"},
    "science_lab": {"static": st_lab, "sky": ((200, 235, 235), (220, 245, 245)), "panel": "board",
                    "desc": "school science lab with flasks"},
    "garden": {"static": st_garden, "sky": ((120, 200, 255), (210, 240, 255)), "panel": "window", "outdoor": True,
               "desc": "sunny garden with flowers, trees and a fence"},
    "playground": {"static": st_playground, "sky": ((110, 195, 255), (215, 240, 255)), "panel": "window", "outdoor": True,
                   "desc": "school playground with a slide and sandbox"},
    "school_yard": {"static": st_school_yard, "sky": ((120, 200, 255), (220, 240, 255)), "panel": "window", "outdoor": True,
                    "desc": "outside the school building"},
    "kitchen": {"static": st_kitchen, "sky": ((255, 245, 225), (255, 245, 225)), "panel": "window",
                "desc": "home kitchen (food, cooking, body topics)"},
    "bedroom_night": {"static": st_bedroom_night, "sky": ((40, 40, 90), (70, 60, 120)), "panel": "window",
                      "desc": "kid's bedroom at night (sleep, dreams, stars, space)"},
    "beach": {"static": st_beach, "sky": ((110, 200, 255), (220, 245, 255)), "panel": "window", "outdoor": True,
              "desc": "sunny beach with sea, palm tree and sandcastle"},
}


@lru_cache(maxsize=16)
def backdrop(place: str, W: int, H: int) -> Image.Image:
    p = PLACES.get(place, PLACES["classroom"])
    img = gradient(W, H, *p["sky"]).copy()
    d = ImageDraw.Draw(img)
    p["static"](d, Ctx(W, H))
    return img


def animate(d, ctx, place: str, t: float) -> None:
    """Small moving details on top of the cached backdrop."""
    p = PLACES.get(place, PLACES["classroom"])
    if p.get("outdoor"):
        for i, (y, k, sp) in enumerate([(-ctx.half_h + 120, 0.7, 25), (-ctx.half_h + 230, 0.5, 40)]):
            x = ((t * sp + i * 700) % (ctx.half_w * 2 + 400)) - ctx.half_w - 200
            cloud(ctx, d, x, y, k)
        for i in range(3):  # butterflies / birds
            x = math.sin(t * 0.6 + i * 2) * ctx.half_w * 0.8
            y = -ctx.half_h * 0.2 + math.cos(t * 0.9 + i) * 80
            w = abs(math.sin(t * 12 + i)) * 14 + 4
            c = [(255, 140, 60), (255, 120, 200), (120, 160, 255)][i]
            ctx.ellipse(d, x - 10, y, w, 12, c)
            ctx.ellipse(d, x + 10, y, w, 12, c)
    if place == "playground":
        a = math.sin(t * 2.2) * 0.5
        x0 = ctx.half_w * 0.35
        g = _ground(ctx)
        ctx.line(d, [(x0 - 140, g + 60), (x0 - 100, g - 260), (x0 + 100, g - 260), (x0 + 140, g + 60)], (90, 150, 240), 12)
        sx, sy = x0 + math.sin(a) * 200, g - 260 + math.cos(a) * 200
        ctx.line(d, [(x0 - 30, g - 260), (sx - 30, sy)], (120, 120, 130), 4)
        ctx.line(d, [(x0 + 30, g - 260), (sx + 30, sy)], (120, 120, 130), 4)
        ctx.rect(d, sx - 45, sy - 8, sx + 45, sy + 10, (255, 200, 60))
    if place == "beach":
        g = _ground(ctx)
        for i in range(-10, 11):
            x = i * 110 + (t * 40) % 110
            ctx.ellipse(d, x, g + 32 + 6 * math.sin(t * 2 + i), 60, 10, (255, 255, 255))
    if place == "bedroom_night":
        rnd = random.Random(2)
        for i in range(14):
            x, y = rnd.uniform(-ctx.half_w, ctx.half_w), rnd.uniform(-ctx.half_h, -ctx.half_h * 0.2)
            tw = 0.5 + 0.5 * math.sin(t * 2 + i)
            ctx.circle(d, x, y, 5 + 4 * tw, lerp_col((120, 110, 170), (255, 250, 180), tw))


# ---------------------------------------------------------------- science panel
def panel_rect(ctx, place):
    if ctx.portrait:
        return (-460, -ctx.half_h + 130, 460, -ctx.half_h + 900)
    if PLACES.get(place, {}).get("panel") == "board":
        return (-820, -400, 340, 230)
    return (-800, -420, 330, 210)


def draw_panel(img, ctx, place, draw_visual):
    """draw_visual(sub_img, sub_ctx) paints the science animation; it is framed into the scene."""
    x0, y0, x1, y1 = panel_rect(ctx, place)
    (X0, Y0), (X1, Y1) = ctx.P(x0, y0), ctx.P(x1, y1)
    X0, Y0, X1, Y1 = int(X0), int(Y0), int(X1), int(Y1)
    pw, ph = X1 - X0, Y1 - Y0
    board = PLACES.get(place, {}).get("panel") == "board"
    d = ImageDraw.Draw(img)
    s = ctx.s
    if board:  # aluminium whiteboard frame + marker tray
        d.rounded_rectangle([X0 - 22 * s, Y0 - 22 * s, X1 + 22 * s, Y1 + 22 * s], radius=10 * s, fill=(170, 175, 185))
        d.rectangle([X0 + pw * 0.1, Y1 + 22 * s, X1 - pw * 0.1, Y1 + 40 * s], fill=(150, 155, 165))
        for i, c in enumerate([(220, 50, 50), (40, 90, 200), (40, 160, 70)]):
            d.rounded_rectangle([X0 + pw * 0.2 + i * 60 * s, Y1 + 12 * s, X0 + pw * 0.2 + i * 60 * s + 45 * s, Y1 + 24 * s], radius=4 * s, fill=c)
    else:  # glowing imagination window
        for k in range(3, 0, -1):
            d.rounded_rectangle([X0 - k * 12 * s, Y0 - k * 12 * s, X1 + k * 12 * s, Y1 + k * 12 * s], radius=(40 + k * 12) * s,
                                fill=lerp_col((255, 255, 255), (255, 230, 120), k / 3))
    sub = Image.new("RGB", (pw, ph))
    draw_visual(sub, Ctx(pw, ph))
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=int((8 if board else 34) * s), fill=255)
    img.paste(sub, (X0, Y0), mask)


DEFAULT_PLACE = {"space_orbit": "bedroom_night", "earth_layers": "classroom", "atom": "science_lab",
                 "chemistry": "science_lab", "cells": "science_lab", "brain": "classroom", "body_heart": "classroom",
                 "plant_grow": "garden", "sun_rays": "garden", "wind": "school_yard", "rain_cycle": "school_yard",
                 "lightning": "bedroom_night", "ocean": "beach", "volcano": "classroom", "gravity": "playground",
                 "magnet": "science_lab", "light_prism": "classroom", "sound_waves": "classroom",
                 "question": "classroom", "intro": "school_yard", "outro": "playground"}
