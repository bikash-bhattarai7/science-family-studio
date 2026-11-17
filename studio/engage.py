"""YouTube engagement kit: titles to test, 3 thumbnails, chapters, pinned comment,
community poll and a step-by-step upload checklist (UPLOAD_KIT.md)."""
from __future__ import annotations

from pathlib import Path

from . import render
from .common import lang_codes

LANG = {"en": "English", "ar": "Arabic", "hi": "Hindi", "ne": "Nepali"}


def _ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def chapters(data: dict, tl: dict) -> list[str]:
    starts = {sc["index"]: sc["start"] for sc in tl["scenes"]}
    ch = [c for c in data.get("chapters", []) if isinstance(c, dict) and c.get("scene") in starts]
    if not ch or ch[0]["scene"] != 0:
        ch = [{"scene": 0, "title": "The big question"}] + ch
    out, last = [], -99.0
    for c in ch:  # YouTube needs 3+ chapters, first at 0:00, each at least 10 s
        t = starts[c["scene"]]
        if t - last >= 10:
            out.append(f"{_ts(t)} {c['title']}")
            last = t
    return out if len(out) >= 3 else []


def build_kit(cfg: dict, ep: Path, data: dict, tl: dict) -> Path:
    out = ep / "output"
    codes = lang_codes(cfg)
    title = data["title"]["en"] if isinstance(data["title"], dict) else data["title"]
    desc = data["description"]["en"] if isinstance(data["description"], dict) else data["description"]
    titles = (data.get("title_options") or [])[:3] or [title]
    texts = (data.get("thumbnail_texts") or [])[:3]
    for i in range(3):
        render.render_thumbnail(cfg, tl, data, out / f"thumbnail_{'ABC'[i]}.jpg", variant=i,
                                text=texts[i] if i < len(texts) else None)

    chap = chapters(data, tl)
    tags = data.get("tags", [])
    hashtags = " ".join(cfg["social"]["hashtags"][:3])
    langs = ", ".join(LANG.get(c, c) for c in codes)
    full_desc = (f"{desc}\n\n🎧 Watch in {langs}: tap ⚙️ Settings → Audio track\n\n"
                 + ("Chapters:\n" + "\n".join(chap) + "\n\n" if chap else "")
                 + f"🔔 Subscribe for a new science adventure every week!\n\n{hashtags}")
    poll = data.get("community_poll") or {}
    L = [f"# Upload kit: {title}", "",
         "## 1. Upload the main video",
         "studio.youtube.com → Create → Upload → `video_main.mp4`", "",
         f"**Title** (use #1, the others are for testing later):",
         *[f"{i + 1}. {t}" for i, t in enumerate(titles)], "",
         "**Description** (copy everything in the box):", "```", full_desc, "```", "",
         f"**Tags:** {', '.join(tags)}", "",
         "**Thumbnail:** click *Test & compare* and upload all three: `thumbnail_A.jpg`, `thumbnail_B.jpg`, "
         "`thumbnail_C.jpg`. YouTube shows each to viewers and keeps the one that gets the most watch time.", "",
         f"**Playlist:** {data.get('playlist', 'Everyday Science')} (create it once, then reuse)",
         "**Audience:** No, it's not made for kids", "",
         "## 2. Languages (same video, more viewers)",
         "Subtitles → Add language:"]
    for c in codes[1:]:
        L.append(f"- **{LANG.get(c, c)}**: Title & description → paste from `REVIEW.md` · "
                 f"Audio → upload `audio_track_{c}.mp3` · Subtitles → upload `captions/main_{c}.srt`")
    L += [f"- **English** subtitles → upload `captions/main_en.srt`", "",
          "## 3. End screen (last 20 s)",
          "Add: *Subscribe* + *Best for viewer* video. Good next videos to make: "
          + "; ".join(data.get("next_topics", [])), "",
          "## 4. Right after publishing",
          f"**Pin this comment:**\n> {data.get('pinned_comment', 'Which fact surprised you the most? Tell us below!')}", "",
          "Reply to the first comments in the first hour — early replies help the video get recommended.", "",
          "## 5. Shorts (post 1-2 days apart)",
          *[f"- `short_{c}.mp4`: title `{data['title'][c] if isinstance(data['title'], dict) else title} #Shorts`"
            for c in cfg['shorts']['languages']],
          "- In the Short's upload screen, set **Related video** to the main video so viewers jump to it.", "",
          "## 6. Community tab (the day before)",
          f"**Poll:** {poll.get('question', '')}",
          *[f"- {o}" for o in poll.get("options", [])], "",
          "## Weekly rhythm",
          "- Same day and time every week (consistency builds returning viewers).",
          "- Day -1: Community poll · Day 0: main video · Day +1 and +3: Shorts.",
          "- After 48 h: YouTube Studio → Analytics → check *Audience retention*; the dip shows which scene to shorten next time."]
    kit = out / "UPLOAD_KIT.md"
    kit.write_text("\n".join(L), encoding="utf-8")
    return kit
