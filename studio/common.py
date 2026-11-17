"""Shared helpers: config, paths, AI calls, audio I/O."""
from __future__ import annotations

import json
import os
import re
import subprocess
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / "episodes"
SAMPLE_RATE = 48000


# ---------------------------------------------------------------- config
def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config() -> dict:
    load_env()
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def lang_codes(cfg: dict) -> list[str]:
    return list(cfg["languages"].keys())


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "episode"


def new_episode_dir(topic: str) -> Path:
    d = EPISODES / f"{datetime.now():%Y%m%d}-{slugify(topic)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def episode_dir(ep_id: str) -> Path:
    d = EPISODES / ep_id
    if not d.exists():
        matches = sorted(EPISODES.glob(f"*{ep_id}*"))
        if not matches:
            raise SystemExit(f"Episode '{ep_id}' not found in {EPISODES}")
        d = matches[-1]
    return d


def read_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- AI
def ask_claude(cfg: dict, system: str, prompt: str) -> str:
    """Call the Anthropic Messages API with plain HTTP (no SDK needed)."""
    import requests

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("Set ANTHROPIC_API_KEY in your environment or in a .env file.")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": cfg["llm"]["model"],
            "max_tokens": cfg["llm"].get("max_tokens", 8000),
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=300,
    )
    if r.status_code != 200:
        raise SystemExit(f"Claude API error {r.status_code}: {r.text[:500]}")
    return "".join(b.get("text", "") for b in r.json()["content"])


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1])
    return json.loads(text[start:])


# ---------------------------------------------------------------- audio
def decode_audio(path: Path) -> np.ndarray:
    """Any audio file -> mono float32 at SAMPLE_RATE (via ffmpeg)."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1",
         "-ar", str(SAMPLE_RATE), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)
