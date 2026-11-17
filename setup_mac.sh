#!/bin/bash
# One-click setup for Mac/Linux. Run:  bash setup_mac.sh
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { command -v brew >/dev/null && brew install ffmpeg || echo "Please install ffmpeg (https://ffmpeg.org)"; }
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "Setup done. Rendering a test video (about 3 minutes)..."
python run.py demo
echo "Your test video is in episodes/demo-why-is-the-sky-blue/output"
