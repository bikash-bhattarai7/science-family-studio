# Science Family Studio

This project makes animated science videos for families. Each video gets narration in **English, Arabic, Hindi and Nepali**, and the project turns every episode into a YouTube video, Shorts/Reels and ready-to-post social captions.

```
topic idea → AI script → translations → HUMAN REVIEW → 4 voices → animation
   → main video (4 audio tracks) + vertical Shorts in 4 languages + captions
   → YouTube upload (localized titles) → social media package
```

## The cast (original characters)
Zippy (robot host), Professor Hoot (wise owl), Bubbles (curious axolotl kid), Sparky (hyper comet),
Rocky (grumpy pebble) and Dot (giggly cell). The AI writes each episode as funny dialogue between them.
Each character has its own voice in English. In Arabic, Hindi and Nepali they use male/female voices
with their own pitch and speed. To change voices or add characters, edit `studio/cast.py`.

## What you get per episode (`episodes/<id>/`)
| File | Use |
|---|---|
| `output/video_main.mp4` | 1080p video with English audio, which gets uploaded to YouTube |
| `output/audio_track_ar.mp3`, `_hi.mp3`, `_ne.mp3` | Extra audio tracks to add in YouTube Studio |
| `output/video_<lang>.mp4` | The full video in each language (for Facebook, WhatsApp, a 2nd channel) |
| `output/short_<lang>.mp4` | 9:16 Short/Reel/TikTok in each language |
| `captions/*.srt` | Subtitles in all 4 languages (uploaded automatically) |
| `output/thumbnail.jpg` | 1280×720 thumbnail |
| `social/<lang>/*.txt` | Captions for Instagram, TikTok, Facebook and Shorts |
| `REVIEW.md` | Facts and translations to check before building |

## Setup (one time, about 30 min)
1. **Install** Python 3.10+ and [ffmpeg](https://ffmpeg.org/download.html). Then run:
   `pip install -r requirements.txt`
2. **Test offline:** run `python run.py demo`. This renders a sample episode, "Why is the sky blue?", with placeholder beeps instead of voices.
3. **AI writer (free):** get a free Google Gemini key at https://aistudio.google.com/apikey. Copy `.env.example` to `.env` and paste the key into it. (Claude is supported too: set `llm.provider: anthropic`.)
4. **YouTube:**
   - In Google Cloud Console, create a project and enable **YouTube Data API v3**.
   - Create an OAuth client ID with type **Desktop app**. Download it as `client_secret.json` into this folder.
   - The first time you run `upload`, a browser opens so you can sign in. After that it's remembered in `token.json`.
   - Verify your channel by phone (needed for custom thumbnails).
5. Edit `config.yaml` to set the channel name, voices, schedule and hashtags.

## Weekly routine
```
python run.py new                 # AI picks a topic, writes and translates (≈1 min)
# open episodes/<id>/REVIEW.md, check the facts and ask a native speaker to check
# the translations; fix anything directly in script.json
python run.py approve <id>
python run.py build <id>          # voices + rendering (≈3-5 min)
python run.py upload <id>         # uploads, then shows the Studio steps for the audio tracks
```
After upload, add the 3 extra audio tracks in YouTube Studio. The exact steps are saved in `STUDIO_AUDIO_STEPS.txt`. This is the one manual step, because the public YouTube API can't upload audio tracks. If you don't see the **Audio** option, multi-language audio isn't enabled for your channel yet.

**Fully automatic:** set `review.require_approval: false` and schedule `python run.py weekly` (Windows Task Scheduler, cron, or the GitHub Actions file in `.github/workflows`). For a kids/family channel, keeping a human check is strongly recommended.

## Social media
- `social/manifest.json` lists every post: platform, language, video file and caption.
- To auto-post, create a Make.com or Zapier scenario with a webhook trigger and put its URL in `social.webhook_url`. Those tools need the video at a public link, so sync the `social/` folder to Google Drive or Dropbox first.
- Or post by hand with Meta Business Suite (Instagram + Facebook) and TikTok's scheduler, using the ready-made captions.

## Family audience settings
- `made_for_kids: false` aims the channel at families. YouTube expects you to answer honestly: if a video is mainly for children, mark it Made for Kids. That setting turns off comments and personalised ads (COPPA rules).
- When YouTube asks about altered or synthetic content, follow its current disclosure rules. AI voices on cartoon content usually don't need a label, but check YouTube's policy.
- Upload quota: the default API quota fits roughly 3 uploads plus captions a day.

## Customising
- **Voices:** run `edge-tts --list-voices`. Good options include `ar-SA-HamedNeural` (male Arabic), `hi-IN-MadhurNeural` and `ne-NP-SagarNeural`. For premium voices, swap `_tts_all` in `studio/audio.py` for ElevenLabs.
- **Music:** set `video.music` to your own royalty-free track.
- **New scene types:** add a drawing function to `VISUAL_LIBRARY` in `studio/visuals.py`. The AI writer can use it automatically.
- **Smoother edges:** set `video.supersample: 2`. This makes rendering about 3× slower.
