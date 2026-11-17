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
    """Ask the AI writer. provider: gemini (free tier) or anthropic (paid)."""
    import time
    import requests

    llm = cfg["llm"]
    provider = llm.get("provider", "gemini")
    for attempt in range(5):
        if provider == "gemini":
            key = os.environ.get("GEMINI_API_KEY")
            if not key:
                raise SystemExit("Set GEMINI_API_KEY (free at https://aistudio.google.com/apikey).")
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{llm['model']}:generateContent",
                headers={"x-goog-api-key": key, "content-type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": llm.get("max_tokens", 8000),
                                         "responseMimeType": "application/json"},
                },
                timeout=300,
            )
            if r.status_code == 200:
                parts = r.json()["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts)
        else:
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise SystemExit("Set ANTHROPIC_API_KEY in your environment or in a .env file.")
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": llm["model"], "max_tokens": llm.get("max_tokens", 8000),
                      "system": system, "messages": [{"role": "user", "content": prompt}]},
                timeout=300,
            )
            if r.status_code == 200:
                return "".join(b.get("text", "") for b in r.json()["content"])
        if provider == "gemini" and r.status_code == 404:  # model retired: follow Google's suggestion
            m = re.search(r"use models/([\w.\-]+)", r.text)
            if m and m.group(1) != llm["model"]:
                print(f"  model {llm['model']} retired, switching to {m.group(1)}")
                llm["model"] = m.group(1)
                continue
        if r.status_code in (429, 500, 503, 529):  # busy / free-tier rate limit: wait and retry
            wait = 20 * (attempt + 1)
            print(f"  AI busy ({r.status_code}), retrying in {wait}s")
            time.sleep(wait)
            continue
        raise SystemExit(f"AI error {r.status_code}: {r.text[:500]}")
    raise SystemExit("AI still busy after 5 tries - try again later.")


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
