"""Social media package: vertical clip + ready-to-paste caption per platform and language.
Optionally sends the package to a Make.com / Zapier webhook for automatic posting."""
from __future__ import annotations

import shutil
from pathlib import Path

from .common import lang_codes, read_json, write_json

PLATFORMS = {
    "instagram_reels": {"max": 2200, "tags": 8},
    "tiktok": {"max": 2200, "tags": 5},
    "facebook_reels": {"max": 2000, "tags": 4},
    "youtube_shorts": {"max": 5000, "tags": 3},
}
CTA = {
    "en": "Watch the full video on our YouTube channel! Which fact surprised you?",
    "ar": "شاهدوا الفيديو الكامل على قناتنا في يوتيوب! أي معلومة فاجأتكم؟",
    "hi": "पूरा वीडियो हमारे YouTube चैनल पर देखें! आपको कौन-सी बात सबसे हैरान करने वाली लगी?",
    "ne": "पूरा भिडियो हाम्रो YouTube च्यानलमा हेर्नुहोस्! तपाईंलाई कुन कुराले सबैभन्दा अचम्म लाग्यो?",
}


def build_package(cfg, ep: Path) -> Path:
    data = read_json(ep / "script.json")
    out = ep / "social"
    out.mkdir(exist_ok=True)
    manifest = {"topic": data["topic"], "posts": []}
    for c in lang_codes(cfg):
        clip = ep / "output" / f"short_{c}.mp4"
        if not clip.exists():
            continue
        ldir = out / c
        ldir.mkdir(exist_ok=True)
        shutil.copy(clip, ldir / clip.name)
        for plat, rule in PLATFORMS.items():
            tags = " ".join(cfg["social"]["hashtags"][: rule["tags"]])
            text = f"{data['title'][c]}\n\n{CTA.get(c, CTA['en'])}\n\n{tags}"[: rule["max"]]
            (ldir / f"{plat}.txt").write_text(text, encoding="utf-8")
            manifest["posts"].append({"platform": plat, "language": c, "video": str(ldir / clip.name), "caption": text})
    write_json(out / "manifest.json", manifest)

    hook = cfg["social"].get("webhook_url")
    if hook:
        import requests
        r = requests.post(hook, json=manifest, timeout=30)
        print(f"  webhook -> {r.status_code}")
    return out
