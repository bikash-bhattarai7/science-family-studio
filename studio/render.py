"""Draw every frame with Pillow and stream it into ffmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .visuals import VISUAL_LIBRARY, Ctx, draw_mascot, font, gradient


def _frame(ctx, scene, lt, talking, total_t):
    v = VISUAL_LIBRARY.get(scene["visual"], VISUAL_LIBRARY["question"])
    img = gradient(ctx.W, ctx.H, *v["bg"]).copy()
    d = ImageDraw.Draw(img)
    p = min(1.0, lt / max(scene["duration"], 0.01))
    v["fn"](d, ctx, lt, p)
    if scene["visual"] in ("intro", "outro"):
        draw_mascot(d, ctx, total_t, talking, "center", wave=True)
    else:
        draw_mascot(d, ctx, total_t, talking, "corner")
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


def render_thumbnail(cfg, tl: dict, data: dict, out: Path) -> Path:
    W, H = 1280, 720
    ctx = Ctx(W, H)
    pick = next((s for s in tl["scenes"] if s["visual"] not in ("question", "intro", "outro")), tl["scenes"][0])
    sc = dict(pick, duration=pick["duration"])
    v = VISUAL_LIBRARY[sc["visual"]]
    img = gradient(W, H, *v["bg"]).copy()
    d = ImageDraw.Draw(img)
    v["fn"](d, ctx, 2.0, 0.85)
    draw_mascot(d, ctx, 0.3, True, scale=1.3, pos=(ctx.half_w - 210, ctx.half_h - 230))
    title = data["title"]
    if isinstance(title, dict):
        title = next(iter(title.values()))
    text = (data.get("thumbnail_text") or title).upper()
    size = 120
    while size > 50 and d.textlength(text, font=font(size)) > W * 0.9:
        size -= 6
    d.text((W / 2, 95), text, font=font(size), fill=(255, 230, 50), anchor="mm",
           stroke_width=12, stroke_fill=(30, 20, 60))
    img.save(out, quality=92)
    return out
