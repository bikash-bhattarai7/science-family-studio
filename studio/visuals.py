"""Procedural cartoon scenes + Zippy the robot host. No on-screen words, so one
animation works for every language. Each scene is drawn from simple shapes and
adapts to landscape (16:9) and portrait (9:16, Shorts)."""
from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- helpers
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


@lru_cache(maxsize=32)
def font(size: int):
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def pop(x: float) -> float:
    """overshoot pop-in 0..1"""
    x = max(0.0, min(1.0, x))
    return 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2


def lerp_col(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class Ctx:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.s = min(W, H) / 1080.0
        self.cx, self.cy = W / 2, H / 2
        self.portrait = H > W

    def P(self, x, y):
        """units (1080-high design space, origin at centre) -> pixels"""
        return self.cx + x * self.s, self.cy + y * self.s

    def circle(self, d, x, y, r, fill, outline=None, width=0):
        X, Y = self.P(x, y)
        R = r * self.s
        d.ellipse([X - R, Y - R, X + R, Y + R], fill=fill, outline=outline, width=int(width * self.s))

    def ellipse(self, d, x, y, rx, ry, fill, outline=None, width=0):
        X, Y = self.P(x, y)
        d.ellipse([X - rx * self.s, Y - ry * self.s, X + rx * self.s, Y + ry * self.s], fill=fill,
                  outline=outline, width=int(width * self.s))

    def poly(self, d, pts, fill, outline=None, width=0):
        d.polygon([self.P(*p) for p in pts], fill=fill, outline=outline, width=int(width * self.s) if outline else 1)

    def line(self, d, pts, fill, width):
        d.line([self.P(*p) for p in pts], fill=fill, width=max(1, int(width * self.s)), joint="curve")

    def rect(self, d, x0, y0, x1, y1, fill, r=0, outline=None, width=0):
        a, b = self.P(x0, y0), self.P(x1, y1)
        d.rounded_rectangle([a, b], radius=r * self.s, fill=fill, outline=outline, width=int(width * self.s))

    @property
    def half_w(self):
        return self.W / 2 / self.s

    @property
    def half_h(self):
        return self.H / 2 / self.s


@lru_cache(maxsize=64)
def gradient(W, H, top, bottom):
    img = Image.new("RGB", (1, 256))
    for y in range(256):
        img.putpixel((0, y), lerp_col(top, bottom, y / 255))
    return img.resize((W, H), Image.BILINEAR)


def stars(ctx, d, t, n=90, seed=1):
    rnd = random.Random(seed)
    for _ in range(n):
        x = rnd.uniform(-ctx.half_w, ctx.half_w)
        y = rnd.uniform(-ctx.half_h, ctx.half_h)
        tw = 0.5 + 0.5 * math.sin(t * rnd.uniform(1, 4) + rnd.uniform(0, 6))
        r = rnd.uniform(1.5, 4) * (0.6 + 0.6 * tw)
        ctx.circle(d, x, y, r, lerp_col((90, 90, 140), (255, 255, 230), tw))


def cloud(ctx, d, x, y, k=1.0, col=(255, 255, 255)):
    for dx, dy, r in [(-70, 10, 55), (0, -20, 75), (75, 5, 60), (30, 25, 55), (-30, 28, 50)]:
        ctx.circle(d, x + dx * k, y + dy * k, r * k, col)


def sun(ctx, d, x, y, r, t, rays=True):
    if rays:
        for i in range(12):
            a = t * 0.6 + i * math.pi / 6
            p1 = (x + math.cos(a - 0.12) * r * 1.2, y + math.sin(a - 0.12) * r * 1.2)
            p2 = (x + math.cos(a + 0.12) * r * 1.2, y + math.sin(a + 0.12) * r * 1.2)
            tip = (x + math.cos(a) * r * (1.65 + 0.1 * math.sin(t * 3 + i)), y + math.sin(a) * r * (1.65 + 0.1 * math.sin(t * 3 + i)))
            ctx.poly(d, [p1, tip, p2], (255, 196, 40))
    ctx.circle(d, x, y, r * 1.12, (255, 214, 80))
    ctx.circle(d, x, y, r, (255, 235, 110))
    # smile
    ctx.circle(d, x - r * 0.3, y - r * 0.15, r * 0.09, (120, 70, 20))
    ctx.circle(d, x + r * 0.3, y - r * 0.15, r * 0.09, (120, 70, 20))
    X, Y = ctx.P(x, y + r * 0.1)
    R = r * 0.45 * ctx.s
    d.arc([X - R, Y - R, X + R, Y + R], 20, 160, fill=(120, 70, 20), width=max(2, int(r * 0.07 * ctx.s)))


# ---------------------------------------------------------------- scenes
# each: fn(d, ctx, t, p) where t = seconds into scene, p = progress 0..1
def sc_question(d, ctx, t, p):
    rnd = random.Random(3)
    for i in range(14):
        a = t * 0.5 + i * 2 * math.pi / 14
        rr = 330 + 40 * math.sin(t * 2 + i)
        ctx.circle(d, math.cos(a) * rr * 1.2, math.sin(a) * rr * 0.8, 10 + rnd.random() * 10,
                   [(255, 230, 90), (120, 230, 255), (255, 140, 200)][i % 3])
    k = pop(t / 0.6)
    size = int(520 * ctx.s * max(0.05, k))
    f = font(size)
    bob = math.sin(t * 3) * 20
    X, Y = ctx.P(0, -40 + bob)
    d.text((X + 10 * ctx.s, Y + 12 * ctx.s), "?", font=f, fill=(70, 30, 120), anchor="mm")
    d.text((X, Y), "?", font=f, fill=(255, 220, 60), anchor="mm", stroke_width=int(10 * ctx.s), stroke_fill=(255, 255, 255))


def sc_intro(d, ctx, t, p):
    rnd = random.Random(5)
    for i in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        sp = rnd.uniform(200, 700)
        r = ease(t / 1.2) * sp
        ctx.circle(d, math.cos(a) * r, math.sin(a) * r * 0.8, 8 + 6 * rnd.random(),
                   [(255, 230, 90), (120, 230, 255), (255, 140, 200), (140, 255, 160)][i % 4])


def sc_space_orbit(d, ctx, t, p):
    stars(ctx, d, t)
    for k, col in [(1.9, (60, 50, 20)), (1.5, (120, 90, 20))]:
        ctx.circle(d, 0, 0, 110 * k * 0.8, col)
    sun(ctx, d, 0, 0, 110, t, rays=False)
    ctx.ellipse(d, 0, 0, 380, 200, None, outline=(90, 110, 170), width=3)
    a = t * 0.8
    px, py = math.cos(a) * 380, math.sin(a) * 200
    ctx.circle(d, px, py, 52, (60, 140, 255))
    ctx.circle(d, px - 15, py - 10, 22, (90, 200, 110))
    ctx.circle(d, px + 20, py + 18, 14, (90, 200, 110))
    ma = t * 3
    ctx.circle(d, px + math.cos(ma) * 95, py + math.sin(ma) * 95, 15, (220, 220, 230))


def sc_sun_rays(d, ctx, t, p):
    sun(ctx, d, -ctx.half_w * 0.45, -ctx.half_h * 0.4, 120, t)
    for i, (y, k, sp) in enumerate([(-300, 0.8, 30), (-150, 1.1, 18), (-380, 0.6, 45)]):
        x = ((t * sp + i * 500) % (ctx.half_w * 2 + 400)) - ctx.half_w - 200
        cloud(ctx, d, x, y, k)
    ctx.ellipse(d, -300, ctx.half_h + 160, 900, 400, (110, 200, 90))
    ctx.ellipse(d, 450, ctx.half_h + 220, 800, 400, (90, 180, 80))
    for i in range(6):
        x = -ctx.half_w * 0.7 + i * ctx.half_w * 0.28
        y = ctx.half_h - 120 - 20 * math.sin(i)
        ctx.line(d, [(x, y), (x, y - 70)], (60, 140, 50), 6)
        for j, c in enumerate([(255, 120, 160), (255, 200, 60), (255, 255, 255)]):
            a = t * 2 + j * 2.1 + i
            ctx.circle(d, x + math.cos(a) * 14, y - 75 + math.sin(a) * 14, 12, c)
        ctx.circle(d, x, y - 75, 9, (255, 220, 50))


def sc_rain_cycle(d, ctx, t, p):
    W2 = ctx.half_w
    sea_y = ctx.half_h * 0.45
    pts = [(-W2 - 20, ctx.half_h + 20)]
    for i in range(41):
        x = -W2 - 20 + i * (2 * W2 + 40) / 40
        pts.append((x, sea_y + 15 * math.sin(x / 60 + t * 2.5)))
    pts.append((W2 + 20, ctx.half_h + 20))
    ctx.poly(d, pts, (40, 120, 220))
    sun(ctx, d, W2 * 0.7, -ctx.half_h * 0.6, 80, t)
    # evaporation
    for i in range(10):
        ph = (t * 0.45 + i / 10) % 1
        x = -W2 * 0.1 + (i % 5) * 70 + 20 * math.sin(ph * 10 + i)
        y = sea_y - ph * (sea_y + ctx.half_h * 0.45)
        ctx.circle(d, x, y, 9 * (1 - ph) + 3, (200, 235, 255))
    cx_ = -W2 * 0.4
    cloud(ctx, d, cx_, -ctx.half_h * 0.55, 1.3, (235, 240, 250))
    for i in range(18):
        ph = (t * 1.3 + i * 0.137) % 1
        x = cx_ - 120 + (i * 53) % 240
        y = -ctx.half_h * 0.45 + ph * (sea_y + ctx.half_h * 0.45)
        ctx.line(d, [(x, y), (x - 4, y + 30)], (120, 190, 255), 6)


def sc_atom(d, ctx, t, p):
    for k in range(3):
        rot = k * math.pi / 3
        pts = []
        for i in range(73):
            a = i * 2 * math.pi / 72
            x, y = math.cos(a) * 380, math.sin(a) * 130
            pts.append((x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)))
        ctx.line(d, pts, (120, 220, 255), 4)
        a = t * (2.2 + k * 0.4) + k * 2
        x, y = math.cos(a) * 380, math.sin(a) * 130
        ex, ey = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        ctx.circle(d, ex, ey, 26, (255, 240, 90), outline=(255, 255, 255), width=4)
    beat = 1 + 0.06 * math.sin(t * 6)
    rnd = random.Random(2)
    for i in range(9):
        a, r = rnd.uniform(0, 6.3), rnd.uniform(0, 45)
        ctx.circle(d, math.cos(a) * r * beat, math.sin(a) * r * beat, 34,
                   (240, 80, 90) if i % 2 else (90, 130, 255), outline=(255, 255, 255), width=3)


def sc_volcano(d, ctx, t, p):
    base = ctx.half_h
    ctx.poly(d, [(-520, base), (-110, -60), (110, -60), (520, base)], (130, 85, 60))
    ctx.poly(d, [(-300, base), (-90, -20), (-20, base)], (110, 70, 50))
    ctx.ellipse(d, 0, -60, 115, 26, (230, 70, 30))
    for i in range(14):
        ph = (t * 0.8 + i / 14) % 1
        rnd = random.Random(i)
        vx = rnd.uniform(-260, 260)
        vy = rnd.uniform(650, 900)
        x = vx * ph
        y = -60 - vy * ph + 900 * ph * ph
        ctx.circle(d, x, y, 22 * (1 - ph * 0.5), (255, 120 + int(100 * (1 - ph)), 30))
    for i in range(6):
        ph = (t * 0.25 + i / 6) % 1
        ctx.circle(d, 40 * math.sin(i + t) + ph * 120, -140 - ph * 420, 40 + ph * 70,
                   lerp_col((120, 110, 110), (210, 200, 200), ph))
    # lava rivers
    k = ease(p * 2)
    ctx.line(d, [(-60, -50), (-120, 80), (-180, 80 + 300 * k)], (255, 110, 30), 22)
    ctx.line(d, [(50, -50), (130, 120), (160, 120 + 260 * k)], (255, 140, 30), 18)


def sc_plant_grow(d, ctx, t, p):
    ground = ctx.half_h * 0.5
    ctx.rect(d, -ctx.half_w - 5, ground, ctx.half_w + 5, ctx.half_h + 5, (120, 80, 50))
    ctx.rect(d, -ctx.half_w - 5, ground, ctx.half_w + 5, ground + 25, (90, 170, 70))
    sun(ctx, d, ctx.half_w * 0.65, -ctx.half_h * 0.6, 85, t)
    g = ease(p / 0.8)
    h = 40 + 480 * g
    sway = math.sin(t * 1.5) * 15 * g
    pts = [(math.sin(i / 10 * 3) * 18 * g + sway * i / 10, ground - h * i / 10) for i in range(11)]
    ctx.line(d, pts, (60, 160, 60), 18)
    for i, frac in enumerate([0.3, 0.5, 0.7]):
        if g > frac:
            k = pop((g - frac) * 4)
            x, y = pts[int(frac * 10)]
            sgn = -1 if i % 2 else 1
            ctx.ellipse(d, x + sgn * 70 * k, y, 70 * k, 28 * k, (80, 200, 80))
    if g > 0.9:
        k = pop((g - 0.9) * 10)
        x, y = pts[-1]
        for j in range(6):
            a = j * math.pi / 3 + t
            ctx.circle(d, x + math.cos(a) * 45 * k, y + math.sin(a) * 45 * k, 32 * k, (255, 120, 170))
        ctx.circle(d, x, y, 30 * k, (255, 215, 60))
    ctx.circle(d, 0, ground + 60, 22, (150, 100, 60))  # seed
    for i in range(5):
        ph = (t * 0.9 + i / 5) % 1
        ctx.circle(d, -260 + i * 30, ground + 30 + ph * 150, 8, (90, 170, 255))


def sc_lightning(d, ctx, t, p):
    for i in range(30):
        ph = (t * 1.8 + i * 0.173) % 1
        x = -ctx.half_w + (i * 97) % (2 * ctx.half_w)
        y = -ctx.half_h * 0.4 + ph * ctx.half_h * 1.6
        ctx.line(d, [(x, y), (x - 10, y + 40)], (150, 170, 220), 4)
    for x, y, k in [(-300, -330, 1.6), (100, -360, 1.9), (450, -320, 1.4)]:
        cloud(ctx, d, x, y, k, (80, 85, 110))
    cyc = t % 2.2
    if cyc < 0.35:
        rnd = random.Random(int(t / 2.2))
        x, y = rnd.uniform(-250, 250), -260
        pts = [(x, y)]
        while y < ctx.half_h * 0.8:
            x += rnd.uniform(-70, 70)
            y += rnd.uniform(60, 110)
            pts.append((x, y))
        ctx.line(d, pts, (255, 255, 200), 22)
        ctx.line(d, pts, (255, 255, 255), 8)


def sc_magnet(d, ctx, t, p):
    for k in range(1, 6):
        r = 130 + k * 55
        pts = [(math.cos(a / 40 * math.pi) * r * 1.25, -60 - math.sin(a / 40 * math.pi) * r)
               for a in range(0, 41)]
        ctx.line(d, pts, (160, 170, 220), 3)
        ph = (t * 0.25 + k * 0.2) % 1
        a = ph * math.pi
        ctx.circle(d, math.cos(a) * r * 1.25, -60 - math.sin(a) * r, 9, (255, 220, 70))
    # horseshoe
    pts_o = [(math.cos(a / 30 * math.pi) * 170, 60 + math.sin(a / 30 * math.pi) * 170) for a in range(0, 31)]
    ctx.line(d, pts_o, (220, 60, 60), 90)
    ctx.rect(d, -215, -120, -125, 60, (220, 60, 60))
    ctx.rect(d, 125, -120, 215, 60, (60, 90, 220))
    ctx.rect(d, -215, -150, -125, -100, (235, 235, 240))
    ctx.rect(d, 125, -150, 215, -100, (235, 235, 240))
    for i in range(10):
        ph = ease(((t * 0.5) + i * 0.1) % 1)
        x0 = -500 + (i % 5) * 230
        ctx.rect(d, x0 * (1 - ph) - 15, -350 + ph * 180 - 6, x0 * (1 - ph) + 15, -350 + ph * 180 + 6, (90, 90, 100), r=4)


def heart_pts(x, y, k):
    pts = []
    for i in range(60):
        a = i / 60 * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((x + hx * k, y + hy * k))
    return pts


def sc_body_heart(d, ctx, t, p):
    for i in range(24):
        a = t * 0.9 + i * 2 * math.pi / 24
        x, y = math.cos(a) * 420, math.sin(a) * 300
        col = (220, 40, 60) if (math.sin(a) > 0) else (90, 110, 230)
        ctx.ellipse(d, x, y, 20, 14, col, outline=(255, 255, 255), width=2)
    beat = 1 + 0.12 * max(0, math.sin(t * 7.5)) ** 4
    ctx.poly(d, heart_pts(0, 0, 14 * beat), (230, 50, 80))
    ctx.poly(d, heart_pts(-40, -50, 4 * beat), (255, 130, 150))


def fish(ctx, d, x, y, k, col, flip=False, t=0):
    s = -1 if flip else 1
    wag = math.sin(t * 8) * 12
    ctx.poly(d, [(x - 60 * k * s, y), (x - 105 * k * s, y - 35 * k + wag), (x - 105 * k * s, y + 35 * k + wag)], col)
    ctx.ellipse(d, x, y, 70 * k, 42 * k, col)
    ctx.circle(d, x + 35 * k * s, y - 10 * k, 11 * k, (255, 255, 255))
    ctx.circle(d, x + 38 * k * s, y - 10 * k, 5 * k, (20, 20, 40))


def sc_ocean(d, ctx, t, p):
    for i in range(5):
        x = -ctx.half_w * 0.8 + i * ctx.half_w * 0.4
        ctx.poly(d, [(x - 30, -ctx.half_h), (x + 30, -ctx.half_h), (x + 160, ctx.half_h), (x + 60, ctx.half_h)], (70, 150, 210))
    for i in range(7):
        x = -ctx.half_w + 80 + i * ctx.half_w * 0.3
        pts = [(x + math.sin(t * 1.5 + j * 0.6 + i) * j * 3, ctx.half_h - j * 30) for j in range(9)]
        ctx.line(d, pts, (60, 170, 90), 16)
    W = ctx.half_w * 2 + 400
    for i, (y, k, sp, col) in enumerate([(-200, 1.0, 110, (255, 150, 40)), (60, 0.8, 80, (255, 220, 60)),
                                          (250, 1.2, 60, (240, 90, 130))]):
        flip = i == 1
        x = ((t * sp + i * 600) % W) - W / 2
        fish(ctx, d, -x if flip else x, y + 20 * math.sin(t * 2 + i), k, col, flip, t + i)
    for i in range(14):
        ph = (t * 0.4 + i / 14) % 1
        ctx.circle(d, -ctx.half_w * 0.6 + (i * 151) % (ctx.half_w * 1.2) + 10 * math.sin(t * 3 + i),
                   ctx.half_h - ph * ctx.half_h * 2, 6 + (i % 4) * 3, None, outline=(210, 240, 255), width=3)


def sc_earth_layers(d, ctx, t, p):
    stars(ctx, d, t, 60, 9)
    layers = [(400, (70, 140, 230)), (370, (150, 100, 70)), (330, (230, 110, 50)), (220, (255, 170, 40)), (110, (255, 235, 120))]
    for i, (r, col) in enumerate(layers):
        k = pop((t - i * 0.35) / 0.6) if i else 1
        ctx.circle(d, 0, 0, max(1, r * k), col)
    glow = 0.5 + 0.5 * math.sin(t * 4)
    ctx.circle(d, 0, 0, 60 + 10 * glow, (255, 255, 200))
    for a0, r in [(0.3, 70), (2.0, 90), (4.0, 60)]:
        a = a0 + t * 0.15
        ctx.circle(d, math.cos(a) * 385, math.sin(a) * 385, r * 0.5, (90, 190, 100))


def sc_chemistry(d, ctx, t, p):
    hue = (math.sin(t * 0.8) + 1) / 2
    liquid = lerp_col((80, 220, 160), (190, 90, 255), hue)
    ctx.rect(d, -60, -340, 60, -120, (225, 240, 250), outline=(255, 255, 255), width=6)
    ctx.poly(d, [(-60, -120), (60, -120), (260, 260), (-260, 260)], (225, 240, 250), outline=(255, 255, 255), width=6)
    lvl = 40 + 10 * math.sin(t * 2)
    ctx.poly(d, [(-60 - (lvl + 120) * 0.526 + 5, lvl), (60 + (lvl + 120) * 0.526 - 5, lvl), (252, 252), (-252, 252)], liquid)
    for i in range(16):
        ph = (t * 0.7 + i / 16) % 1
        x = math.sin(i * 2.3 + t) * 120 * (1 - ph * 0.7)
        y = 230 - ph * 600
        ctx.circle(d, x, y, 10 + (i % 3) * 6, None, outline=lerp_col(liquid, (255, 255, 255), 0.5), width=4)
    for i in range(6):
        a = t * 2 + i
        r = 0.5 + 0.5 * math.sin(t * 5 + i * 1.7)
        x, y = math.cos(a) * 330, -150 + math.sin(a * 1.3) * 200
        ctx.circle(d, x, y, 8 + 10 * r, (255, 240, 120))


def sc_light_prism(d, ctx, t, p):
    k = ease(t / 1.2)
    ctx.line(d, [(-ctx.half_w, 40), (-ctx.half_w + (ctx.half_w - 60) * k, 0)], (255, 255, 255), 20)
    ctx.poly(d, [(0, -200), (-190, 150), (190, 150)], (190, 220, 255), outline=(255, 255, 255), width=6)
    cols = [(255, 60, 60), (255, 150, 40), (255, 235, 60), (70, 210, 90), (60, 140, 255), (110, 70, 220), (180, 80, 230)]
    if t > 1.0:
        k2 = ease((t - 1.0) / 1.2)
        L = (ctx.half_w + 100) * k2
        for i, c in enumerate(cols):
            y_end = -180 + i * 70
            ctx.line(d, [(60, 10 + i * 6), (60 + L, 10 + i * 6 + (y_end - 10) * L / (ctx.half_w + 100))], c, 22)


def sc_sound_waves(d, ctx, t, p):
    beat = 1 + 0.08 * math.sin(t * 14)
    ctx.rect(d, -480, -160, -300, 160, (60, 60, 80), r=20)
    ctx.poly(d, [(-300, -160), (-150, -280), (-150, 280), (-300, 160)], (90, 90, 120))
    ctx.circle(d, -390, 0, 70 * beat, (40, 40, 50), outline=(200, 200, 220), width=6)
    for i in range(6):
        ph = (t * 0.6 + i / 6) % 1
        r = 120 + ph * 700
        X, Y = ctx.P(-150, 0)
        R = r * ctx.s
        col = lerp_col((255, 220, 80), (60, 40, 110), ph)
        d.arc([X - R, Y - R, X + R, Y + R], -45, 45, fill=col, width=max(2, int(16 * (1 - ph) * ctx.s)))


def sc_cells(d, ctx, t, p):
    rnd = random.Random(11)
    for i in range(12):
        x, y = rnd.uniform(-ctx.half_w, ctx.half_w), rnd.uniform(-ctx.half_h, ctx.half_h)
        r = rnd.uniform(25, 60)
        ctx.circle(d, x + 20 * math.sin(t + i), y + 20 * math.cos(t * 0.8 + i), r, (170, 230, 200), outline=(120, 200, 170), width=3)
    split = ease(((t % 5) - 1.5) / 2)
    off = 170 * split
    for sgn in (-1, 1):
        x = sgn * off
        r = 200 - 40 * split
        ctx.circle(d, x, 0, r, (140, 230, 160), outline=(70, 170, 110), width=8)
        ctx.circle(d, x + sgn * 10, -10, 70 - 10 * split, (120, 90, 200))
        for j in range(5):
            a = t * 0.5 + j * 1.25
            ctx.ellipse(d, x + math.cos(a) * r * 0.6, math.sin(a) * r * 0.6, 22, 10, (240, 160, 80))


def sc_wind(d, ctx, t, p):
    ctx.ellipse(d, 0, ctx.half_h + 200, ctx.half_w + 300, 400, (110, 200, 90))
    for i, (x, k) in enumerate([(-ctx.half_w * 0.45, 1.0), (ctx.half_w * 0.35, 0.7)]):
        top = 30 - 260 * k
        ctx.poly(d, [(x - 22 * k, ctx.half_h), (x + 22 * k, ctx.half_h), (x + 8 * k, top), (x - 8 * k, top)], (240, 240, 245))
        for b in range(3):
            a = t * 3 * (1 + i * 0.3) + b * 2 * math.pi / 3
            ctx.poly(d, [(x, top), (x + math.cos(a - 0.15) * 230 * k, top + math.sin(a - 0.15) * 230 * k),
                         (x + math.cos(a + 0.05) * 240 * k, top + math.sin(a + 0.05) * 240 * k)], (250, 250, 255))
        ctx.circle(d, x, top, 18 * k, (200, 200, 210))
    for i in range(8):
        ph = (t * 0.5 + i / 8) % 1
        y = -300 + i * 70
        x0 = -ctx.half_w + ph * (ctx.half_w * 2 + 400) - 200
        pts = [(x0 + j * 25, y + 20 * math.sin(j * 0.5 + t * 3)) for j in range(10)]
        ctx.line(d, pts, (255, 255, 255), 5)
        ctx.ellipse(d, x0 + 260, y + 20 * math.sin(5 + t * 3), 18, 10, (240, 160, 40) if i % 2 else (230, 90, 60))


def sc_brain(d, ctx, t, p):
    rnd = random.Random(4)
    blobs = [(rnd.uniform(-260, 260), rnd.uniform(-170, 150), rnd.uniform(90, 140)) for _ in range(16)]
    for x, y, r in blobs:
        ctx.circle(d, x, y, r + 8, (210, 110, 150))
    for x, y, r in blobs:
        ctx.circle(d, x, y, r, (250, 160, 190))
    nodes = [(rnd.uniform(-250, 250), rnd.uniform(-160, 140)) for _ in range(12)]
    for i in range(len(nodes)):
        a, b = nodes[i], nodes[(i * 5 + 3) % len(nodes)]
        lit = 0.5 + 0.5 * math.sin(t * 4 + i)
        ctx.line(d, [a, b], lerp_col((230, 120, 160), (255, 255, 140), lit), 5)
        ph = (t * 0.8 + i * 0.13) % 1
        ctx.circle(d, a[0] + (b[0] - a[0]) * ph, a[1] + (b[1] - a[1]) * ph, 9, (255, 255, 200))
    for x, y in nodes:
        ctx.circle(d, x, y, 13, (255, 240, 120))
    ctx.rect(d, -40, 160, 40, 300, (240, 150, 180), r=30)


def sc_gravity(d, ctx, t, p):
    ground = ctx.half_h * 0.55
    ctx.rect(d, -ctx.half_w - 5, ground, ctx.half_w + 5, ctx.half_h + 5, (110, 190, 90))
    tx = -ctx.half_w * 0.45
    ctx.rect(d, tx - 30, -80, tx + 30, ground + 5, (140, 95, 60))
    for dx, dy, r in [(0, -260, 170), (-120, -170, 120), (120, -170, 120)]:
        ctx.circle(d, tx + dx, dy, r, (70, 170, 80))
    cyc = t % 2.4
    fall = min(1, cyc / 0.9)
    y = -200 + (ground - 40 + 200) * fall ** 2
    if cyc > 0.9:
        bt = cyc - 0.9
        y = ground - 40 - max(0, 220 * math.sin(min(math.pi, bt * 3.2)) * math.exp(-bt * 1.5))
    ax = tx + 110
    ctx.circle(d, ax, y, 40, (230, 50, 50))
    ctx.line(d, [(ax, y - 40), (ax + 5, y - 65)], (100, 70, 40), 6)
    ctx.ellipse(d, ax + 22, y - 58, 18, 9, (80, 180, 80))
    bx = ctx.half_w * 0.3
    ph = (t * 1.4) % 1
    by = ground - 50 - 450 * 4 * ph * (1 - ph)
    sq = 1 - 0.25 * max(0, 1 - abs(ph - 0) * 12) - 0.25 * max(0, 1 - abs(ph - 1) * 12)
    ctx.ellipse(d, bx, by, 50 / sq, 50 * sq, (60, 140, 255))
    for i in range(3):
        ctx.line(d, [(bx + 120, -200 + i * 90), (bx + 120, -150 + i * 90)], (255, 255, 255), 8)
        ctx.poly(d, [(bx + 100, -150 + i * 90), (bx + 140, -150 + i * 90), (bx + 120, -120 + i * 90)], (255, 255, 255))


def sc_outro(d, ctx, t, p):
    rnd = random.Random(8)
    for i in range(60):
        x = rnd.uniform(-ctx.half_w, ctx.half_w)
        sp = rnd.uniform(120, 300)
        y = ((t * sp + rnd.uniform(0, 2000)) % (ctx.half_h * 2 + 100)) - ctx.half_h - 50
        a = t * rnd.uniform(2, 5)
        w = 16 * abs(math.cos(a)) + 2
        ctx.rect(d, x - w, y - 8, x + w, y + 8, [(255, 90, 120), (255, 220, 60), (90, 200, 255), (120, 230, 120)][i % 4])
    k = pop((t - 0.4) / 0.6)
    swing = math.sin(t * 6) * 0.25 * (1 if t % 3 < 1 else 0)
    bx, by = (0, -330) if ctx.portrait else (ctx.half_w * 0.5, -40)
    S = 1.6 * k
    pts = [(-60, 40), (-48, -30), (-30, -60), (0, -72), (30, -60), (48, -30), (60, 40)]
    rot = [(bx + (x * math.cos(swing) - y * math.sin(swing)) * S, by + (x * math.sin(swing) + y * math.cos(swing)) * S) for x, y in pts]
    if k > 0.05:
        ctx.poly(d, rot, (255, 205, 50), outline=(255, 255, 255), width=5)
        ctx.circle(d, bx, by + 50 * S, 16 * S, (255, 170, 40))
        ctx.circle(d, bx, by - 78 * S, 9 * S, (255, 205, 50))


VISUAL_LIBRARY = {
    "question": {"fn": sc_question, "bg": ((120, 70, 200), (60, 30, 120)), "desc": "big bouncing question mark (hooks, quiz moments)"},
    "intro": {"fn": sc_intro, "bg": ((80, 200, 255), (40, 90, 200)), "desc": "host robot waves hello with confetti burst"},
    "space_orbit": {"fn": sc_space_orbit, "bg": ((10, 10, 40), (30, 20, 70)), "desc": "sun, orbiting Earth and Moon in starry space"},
    "sun_rays": {"fn": sc_sun_rays, "bg": ((110, 200, 255), (200, 240, 255)), "desc": "smiling sun, drifting clouds, green hills, flowers (sunlight, sky, seasons)"},
    "rain_cycle": {"fn": sc_rain_cycle, "bg": ((140, 200, 250), (220, 240, 255)), "desc": "sea, rising water vapour, cloud and rain (water cycle, weather)"},
    "atom": {"fn": sc_atom, "bg": ((15, 40, 70), (5, 15, 35)), "desc": "atom with nucleus and orbiting electrons (matter, electricity, chemistry basics)"},
    "volcano": {"fn": sc_volcano, "bg": ((255, 170, 90), (255, 220, 160)), "desc": "erupting volcano with lava and smoke (earth science, heat)"},
    "plant_grow": {"fn": sc_plant_grow, "bg": ((150, 215, 255), (220, 245, 255)), "desc": "seed sprouting into a flower with sun and water (plants, photosynthesis, growth)"},
    "lightning": {"fn": sc_lightning, "bg": ((40, 40, 70), (80, 80, 110)), "desc": "storm clouds, rain and lightning bolts (electricity, storms)"},
    "magnet": {"fn": sc_magnet, "bg": ((235, 240, 255), (200, 210, 240)), "desc": "horseshoe magnet with field lines pulling iron bits (magnetism, forces)"},
    "body_heart": {"fn": sc_body_heart, "bg": ((255, 200, 210), (255, 150, 170)), "desc": "beating heart with blood cells circulating (human body, blood)"},
    "ocean": {"fn": sc_ocean, "bg": ((40, 140, 210), (10, 50, 120)), "desc": "underwater scene with fish, seaweed, bubbles (oceans, animals, breathing)"},
    "earth_layers": {"fn": sc_earth_layers, "bg": ((10, 10, 35), (25, 15, 50)), "desc": "Earth cut-away showing crust, mantle and glowing core (planet inside, earthquakes)"},
    "chemistry": {"fn": sc_chemistry, "bg": ((40, 50, 90), (20, 25, 50)), "desc": "bubbling colour-changing flask (reactions, mixtures, experiments)"},
    "light_prism": {"fn": sc_light_prism, "bg": ((30, 60, 130), (80, 40, 140)), "desc": "white light splitting into a rainbow through a prism (light, colour, rainbows)"},
    "sound_waves": {"fn": sc_sound_waves, "bg": ((60, 40, 110), (30, 20, 70)), "desc": "speaker sending out sound waves (sound, hearing, vibration)"},
    "cells": {"fn": sc_cells, "bg": ((200, 245, 230), (150, 220, 200)), "desc": "living cell dividing under a microscope (cells, germs, growth)"},
    "wind": {"fn": sc_wind, "bg": ((150, 210, 255), (225, 245, 255)), "desc": "wind turbines and blowing leaves (wind, air, energy)"},
    "brain": {"fn": sc_brain, "bg": ((60, 30, 90), (110, 50, 120)), "desc": "brain with sparkling neurons (brain, senses, sleep, memory)"},
    "gravity": {"fn": sc_gravity, "bg": ((150, 210, 255), (225, 245, 255)), "desc": "falling apple and bouncing ball (gravity, motion, forces)"},
    "outro": {"fn": sc_outro, "bg": ((255, 120, 150), (255, 180, 100)), "desc": "confetti and a ringing bell, host waves goodbye (ending, subscribe)"},
}


# ---------------------------------------------------------------- host robot
def draw_mascot(d, ctx, t, talking: bool, where: str = "corner", scale: float = 1.0, wave: bool = False, pos=None):
    if where == "center":
        bx, by, S = (0, 60, 2.2 * scale) if not ctx.portrait else (0, 250, 2.4 * scale)
    else:
        if ctx.portrait:
            bx, by, S = 0, ctx.half_h - 190, 0.95 * scale
        else:
            bx, by, S = ctx.half_w - 190, ctx.half_h - 175, 1.0 * scale
    if pos:
        bx, by, S = pos[0], pos[1], scale
    by += math.sin(t * 2.4) * 8
    u = lambda x, y: (bx + x * S, by + y * S)  # noqa: E731
    # shadow + body
    ctx.rect(d, *u(-70, 40), *u(70, 140), (60, 200, 210), r=30 * S, outline=(255, 255, 255), width=5 * S)
    ctx.circle(d, *u(0, 90), 22 * S, (255, 210, 60))
    # arms (angle measured from straight up)
    for sgn in (-1, 1):
        if wave and sgn == 1:
            a = math.radians(40 + 25 * math.sin(t * 9))
        else:
            a = sgn * math.radians(155 + 6 * math.sin(t * 2 + sgn))
        sx, sy = u(sgn * 70, 60)
        ex, ey = sx + math.sin(a) * 80 * S, sy - math.cos(a) * 80 * S
        ctx.line(d, [(sx, sy), (ex, ey)], (60, 200, 210), 18 * S)
        ctx.circle(d, ex, ey, 16 * S, (255, 210, 60))
    # head
    ctx.line(d, [u(0, -110), u(0, -150)], (200, 200, 210), 8 * S)
    blink_bulb = 0.5 + 0.5 * math.sin(t * 5)
    ctx.circle(d, *u(0, -158), 16 * S, lerp_col((255, 120, 120), (255, 240, 120), blink_bulb))
    ctx.rect(d, *u(-105, -115), *u(105, 45), (90, 220, 230), r=50 * S, outline=(255, 255, 255), width=6 * S)
    ctx.rect(d, *u(-85, -95), *u(85, 25), (25, 45, 70), r=38 * S)
    blink = (t % 3.7) < 0.12
    look = math.sin(t * 0.9) * 6
    for sgn in (-1, 1):
        ex, ey = u(sgn * 40, -45)
        if blink:
            ctx.line(d, [(ex - 20 * S, ey), (ex + 20 * S, ey)], (120, 240, 255), 6 * S)
        else:
            ctx.circle(d, ex, ey, 24 * S, (120, 240, 255))
            ctx.circle(d, ex + look * S, ey + 2 * S, 11 * S, (255, 255, 255))
    mo = (0.3 + 0.7 * abs(math.sin(t * 11))) if talking else 0.12
    mx, my = u(0, 2)
    ctx.ellipse(d, mx, my, 26 * S, 16 * S * mo + 2 * S, (255, 140, 160))
    # cheeks
    ctx.circle(d, *u(-68, -8), 10 * S, (255, 140, 160))
    ctx.circle(d, *u(68, -8), 10 * S, (255, 140, 160))
