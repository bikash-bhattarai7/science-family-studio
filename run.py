#!/usr/bin/env python3
"""Science Family Studio - one command per step, or `weekly` for everything.

  python run.py demo                 offline test (no API keys): renders a sample episode
  python run.py ideas                add new topic ideas to topics.json
  python run.py new [--topic "..."]  write script + translations -> episodes/<id>/REVIEW.md
  python run.py approve <id>         mark an episode as human-checked
  python run.py build <id>           voices, animation, 4 audio tracks, Shorts, captions, social posts
  python run.py upload <id>          upload to YouTube (+ prints the Studio audio-track steps)
  python run.py weekly               new episode; if review is off, also build + upload
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from studio import audio, render, social, writer
from studio.common import ROOT, episode_dir, lang_codes, load_config, read_json, run


def build(cfg, ep: Path, demo: bool = False) -> None:
    data = read_json(ep / "script.json")
    if cfg["review"]["require_approval"] and not demo and not (ep / "APPROVED").exists():
        sys.exit(f"Not approved yet. Read {ep / 'REVIEW.md'}, then: python run.py approve {ep.name}")
    codes = lang_codes(cfg)
    primary = codes[0]
    out = ep / "output"
    out.mkdir(exist_ok=True)
    t0 = time.time()

    print("1/5 voices")
    audio.make_voices(cfg, ep, data, demo=demo)

    print("2/5 main video timeline + audio tracks")
    tl = audio.build_timeline(cfg, ep, data, list(range(len(data["scenes"]))))
    tracks = audio.mix_tracks(cfg, ep, tl, "main")
    audio.write_captions(cfg, ep, data, tl, "main")
    audio.save_timeline(ep, tl, "main")

    print(f"3/5 rendering main video ({tl['total']:.0f}s)")
    main = render.render_video(cfg, tl, tracks[primary], out / "video_main.mp4", (1920, 1080))
    for c in codes:  # same picture, each language's audio (for Facebook, WhatsApp, etc.)
        run(["ffmpeg", "-v", "error", "-y", "-i", str(main), "-i", str(tracks[c]), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out / f"video_{c}.mp4")])
    render.render_thumbnail(cfg, tl, data, out / "thumbnail.jpg")

    if cfg["shorts"]["enabled"]:
        print("4/5 Shorts / Reels (vertical)")
        ids = [i for i in data.get("short_scenes", [0, 1, 2]) if i < len(data["scenes"])]
        stl = audio.build_timeline(cfg, ep, data, ids)
        while stl["total"] > cfg["shorts"]["max_seconds"] and len(ids) > 1:
            ids = ids[:-1]
            stl = audio.build_timeline(cfg, ep, data, ids)
        strk = audio.mix_tracks(cfg, ep, stl, "short")
        audio.write_captions(cfg, ep, data, stl, "short")
        audio.save_timeline(ep, stl, "short")
        base = render.render_video(cfg, stl, strk[primary], out / "_short_base.mp4", (1080, 1920))
        for c in cfg["shorts"]["languages"]:
            srt = ep / "captions" / f"short_{c}.srt"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-i", str(strk[c]), "-map", "0:v", "-map", "1:a",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out / f"short_{c}.mp4")])
            shutil.copy(srt, out / f"short_{c}.srt")
        (out / "_short_base.mp4").unlink()

    print("5/5 social package")
    social.build_package(cfg, ep)
    print(f"\nDone in {time.time() - t0:.0f}s -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["demo", "ideas", "new", "approve", "build", "upload", "weekly"])
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--topic")
    a = ap.parse_args()
    cfg = load_config()

    if a.cmd == "demo":
        src = ROOT / "demo" / "sample_script.json"
        ep = ROOT / "episodes" / "demo-why-is-the-sky-blue"
        ep.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, ep / "script.json")
        build(cfg, ep, demo=True)
    elif a.cmd == "ideas":
        for t in writer.generate_ideas(cfg):
            print(" -", t)
    elif a.cmd == "new":
        topic = a.topic or writer.next_topic(cfg)
        print(f"Writing: {topic}")
        ep = writer.write_script(cfg, topic)
        writer.mark_topic_done(topic)
        print(f"Review: {ep / 'REVIEW.md'}\nThen:   python run.py approve {ep.name}")
    elif a.cmd == "approve":
        ep = episode_dir(a.episode)
        (ep / "APPROVED").write_text("ok")
        print(f"Approved {ep.name}. Next: python run.py build {ep.name}")
    elif a.cmd == "build":
        build(cfg, episode_dir(a.episode))
    elif a.cmd == "upload":
        from studio.youtube import upload_episode
        upload_episode(cfg, episode_dir(a.episode))
    elif a.cmd == "weekly":
        topic = writer.next_topic(cfg)
        ep = writer.write_script(cfg, topic)
        writer.mark_topic_done(topic)
        if cfg["review"]["require_approval"]:
            print(f"New episode ready for review: {ep / 'REVIEW.md'}")
        else:
            build(cfg, ep)
            from studio.youtube import upload_episode
            upload_episode(cfg, ep)


if __name__ == "__main__":
    main()
