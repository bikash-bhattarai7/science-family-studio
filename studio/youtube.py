"""YouTube upload: video, localized titles/descriptions, captions, thumbnail, Shorts.

Extra AUDIO tracks (ar/hi/ne) must be added in YouTube Studio - the public
YouTube Data API does not support uploading them. This module prints exactly
which file goes where."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .common import ROOT, lang_codes, read_json, write_json

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
LANG_LABEL = {"en": "English", "ar": "العربية", "hi": "हिन्दी", "ne": "नेपाली"}


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token = ROOT / "token.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret = ROOT / "client_secret.json"
            if not secret.exists():
                raise SystemExit("Put your Google OAuth file at client_secret.json (see README, step 4).")
            creds = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0)
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def _publish_at(cfg) -> str | None:
    y = cfg["youtube"]
    if y["privacy"] != "private" or y.get("publish_days_ahead") is None:
        return None
    tz = ZoneInfo(y.get("timezone", "UTC"))
    when = (datetime.now(tz) + timedelta(days=y["publish_days_ahead"])).replace(
        hour=y.get("publish_hour_local", 16), minute=0, second=0, microsecond=0)
    return when.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def _desc(cfg, data, code):
    langs = " · ".join(LANG_LABEL.get(c, c) for c in lang_codes(cfg))
    return (f"{data['description'][code]}\n\n"
            f"🎧 {langs}  (⚙️ Settings → Audio track)\n\n"
            + " ".join(cfg["social"]["hashtags"]))


def _upload(yt, path: Path, body: dict, part: str) -> str:
    from googleapiclient.http import MediaFileUpload

    req = yt.videos().insert(part=part, body=body,
                             media_body=MediaFileUpload(str(path), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"    upload {int(status.progress() * 100)}%")
    return resp["id"]


def upload_episode(cfg, ep: Path) -> dict:
    from googleapiclient.http import MediaFileUpload

    data = read_json(ep / "script.json")
    codes = lang_codes(cfg)
    primary = codes[0]
    y = cfg["youtube"]
    yt = service()
    publish_at = _publish_at(cfg)
    status = {"privacyStatus": y["privacy"], "selfDeclaredMadeForKids": bool(y["made_for_kids"])}
    if publish_at:
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": data["title"][primary][:100],
            "description": _desc(cfg, data, primary)[:5000],
            "tags": data.get("tags", [])[:30],
            "categoryId": y["category_id"],
            "defaultLanguage": primary,
            "defaultAudioLanguage": primary,
        },
        "status": status,
        "localizations": {c: {"title": data["title"][c][:100], "description": _desc(cfg, data, c)[:5000]}
                          for c in codes[1:]},
    }
    print("  uploading main video...")
    vid = _upload(yt, ep / "output" / "video_main.mp4", body, "snippet,status,localizations")
    result = {"main": vid, "shorts": {}, "publish_at": publish_at}

    thumb = ep / "output" / "thumbnail.jpg"
    if thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:  # needs a phone-verified channel
            print(f"  thumbnail skipped: {e}")

    if y.get("upload_captions", True):
        for c in codes:
            srt = ep / "captions" / f"main_{c}.srt"
            yt.captions().insert(part="snippet",
                                 body={"snippet": {"videoId": vid, "language": c,
                                                   "name": LANG_LABEL.get(c, c), "isDraft": False}},
                                 media_body=MediaFileUpload(str(srt))).execute()
            print(f"  captions {c} ok")

    for c in y.get("upload_shorts_languages", []):
        f = ep / "output" / f"short_{c}.mp4"
        if not f.exists():
            continue
        sbody = {
            "snippet": {"title": (data["title"][c][:90] + " #Shorts"), "description": _desc(cfg, data, c)[:5000],
                        "tags": data.get("tags", [])[:30], "categoryId": y["category_id"],
                        "defaultLanguage": c, "defaultAudioLanguage": c},
            "status": dict(status),
        }
        print(f"  uploading Short ({c})...")
        result["shorts"][c] = _upload(yt, f, sbody, "snippet,status")

    write_json(ep / "uploaded.json", result)
    print_studio_steps(cfg, ep, vid)
    return result


def print_studio_steps(cfg, ep: Path, vid: str) -> None:
    codes = lang_codes(cfg)
    if len(codes) < 2:
        print(f"Uploaded: https://youtu.be/{vid}")
        return
    lines = [f"Add the extra audio tracks in YouTube Studio (one-time per video, ~2 min):",
             f"  1. Open https://studio.youtube.com/video/{vid}/translations",
             "  2. For each language: Add language -> Audio -> Add -> select file:"]
    lines += [f"       {cfg['languages'][c]['name']:8s} {ep / 'tracks' / f'main_{c}.wav'}" for c in codes[1:]]
    lines += ["  3. Publish each track. Viewers pick it under ⚙️ -> Audio track.",
              "  If 'Audio' is missing, multi-language audio isn't enabled on your channel yet."]
    text = "\n".join(lines)
    (ep / "STUDIO_AUDIO_STEPS.txt").write_text(text, encoding="utf-8")
    print(text)
