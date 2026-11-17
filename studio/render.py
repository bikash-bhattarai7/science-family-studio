"""Draw every frame with Pillow and stream it into ffmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .cast import DRAW, draw_lineup, draw_speaker
from .visuals import VISUAL_LIBRARY, Ctx, font, gradient


def _frame(ctx, scene, lt, talking, total_t):
    v = VISUAL_LIBRARY.get(scene["visual"], VISUAL_LIBRARY["question"])
    img = gradient(ctx.W, ctx.H, *v["bg"]).copy()
    d = ImageDraw.Draw(img)
    p = min(1.0, lt / max(scene["duration"], 0.01))
    v["fn"](d, ctx, lt, p)
    speaker = scene.get("speaker", "zippy")
    if scene["visual"] in ("intro", "outro"):
        draw_lineup(d, ctx, total_t, speaker, talking)
    else:
        draw_speaker(d, ctx, speaker, total_t, talking)
    return img


def render_video(cfg, tl: dict, audio: Path, out: Path, size: tuple[int, int], talk_lang: str | None = None) -> Path:
    """talk_lang: whose speech moves the robot's mouth (None = any language)."""
    fps = cfg["video"]["fps"]
    ss = max(1, int(cfg["video"].get("supersample", 1)))
    W, H = size
    ctx = Ctx(W * ss, H * ss)
    n = int(tl["total"] * fps)
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-i", str(audio),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    scenes = tl["scenes"]
    si = 0
    white = Image.new("RGB", (W, H), (255, 255, 255))
    for f in range(n):
        t = f / fps
        while si < len(scenes) - 1 and t >= scenes[si + 1]["start"]:
            si += 1
        sc = scenes[si]
        lt = t - sc["start"]
        langs = [talk_lang] if talk_lang else list(sc["speech"].keys())
        talking = any(sc["speech"][c][0] <= t <= sc["speech"][c][1] for c in langs)
        img = _frame(ctx, sc, lt, talking, t)
        if ss > 1:
            img = img.resize((W, H), Image.LANCZOS)
        if si > 0 and lt < 0.22:  # soft flash transition between scenes
            img = Image.blend(img, white, 0.55 * (1 - lt / 0.22))
        proc.stdin.write(img.tobytes())
        if f % (fps * 10) == 0:
            print(f"    {out.name}: {t:5.1f}s / {tl['total']:.1f}s")
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out}")
    return out


def render_thumbnail(cfg, tl: dict, data: dict, out: Path, variant: int = 0, text: str | None = None) -> Path:
    """3 different looks (variant 0/1/2) for YouTube's thumbnail Test & Compare."""
    W, H = 1280, 720
    ctx = Ctx(W, H)
    content = [s for s in tl["scenes"] if s["visual"] not in ("question", "intro", "outro")] or tl["scenes"]
    title = data["title"]
    if isinstance(title, dict):
        title = next(iter(title.values()))
    text = (text or data.get("thumbnail_text") or title).upper()

    if variant == 0:  # science scene + speaker, yellow headline on top
        sc = content[0]
        bg_vis, chars, pos = sc["visual"], [(sc.get("speaker", "zippy"), W / 2 / ctx.s - 210, H / 2 / ctx.s - 220, 1.25)], "top"
        fill, stroke = (255, 230, 50), (30, 20, 60)
    elif variant == 1:  # different scene, two characters reacting, banner at bottom
        sc = content[len(content) // 2]
        sp = sc.get("speaker", "zippy")
        other = "bubbles" if sp != "bubbles" else "sparky"
        bg_vis = sc["visual"]
        chars = [(other, -ctx.half_w + 200, -60, 1.2), (sp, ctx.half_w - 200, -60, 1.2)]
        pos, fill, stroke = "bottom", (255, 255, 255), (200, 30, 60)
    else:  # big character close-up on a question background
        sc = content[-1]
        bg_vis = "question"
        chars = [(sc.get("speaker", "zippy"), -ctx.half_w + 330, 120, 2.1)]
        pos, fill, stroke = "right", (120, 240, 255), (20, 30, 80)

    v = VISUAL_LIBRARY[bg_vis]
    img = gradient(W, H, *v["bg"]).copy()
    d = ImageDraw.Draw(img)
    (VISUAL_LIBRARY["intro"]["fn"] if variant == 2 else v["fn"])(d, ctx, 2.0, 0.85)
    for name, x, y, sc_ in chars:
        DRAW.get(name, DRAW["zippy"])(d, ctx, 0.4, True, x, y, sc_)

    maxw = W * (0.55 if pos == "right" else 0.9)
    words = text.split()
    lines = [text] if pos != "right" else [" ".join(words[: (len(words) + 1) // 2]), " ".join(words[(len(words) + 1) // 2:])]
    lines = [ln for ln in lines if ln]
    size = 130
    while size > 50 and max(d.textlength(ln, font=font(size)) for ln in lines) > maxw:
        size -= 6
    if pos == "top":
        d.text((W / 2, 95), lines[0], font=font(size), fill=fill, anchor="mm", stroke_width=12, stroke_fill=stroke)
    elif pos == "bottom":
        d.rectangle([0, H - 150, W, H], fill=stroke)
        d.text((W / 2, H - 75), lines[0], font=font(size), fill=fill, anchor="mm", stroke_width=6, stroke_fill=(40, 10, 20))
    else:
        y0 = H / 2 - (len(lines) - 1) * size * 0.55
        for i, ln in enumerate(lines):
            d.text((W * 0.72, y0 + i * size * 1.1), ln, font=font(size), fill=fill, anchor="mm",
                   stroke_width=12, stroke_fill=stroke)
    img.save(out, quality=92)
    return out
