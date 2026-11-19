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
    """Ask the AI writer. Gemini (free tier) rotates through several free models when one is busy."""
    import time
    import requests

    llm = cfg["llm"]
    provider = llm.get("provider", "gemini")
    if os.environ.get("AI_MODEL"):  # chosen in the Run workflow menu (or set on your PC)
        llm["model"] = os.environ["AI_MODEL"]
    chain = model_chain(llm) if provider == "gemini" else [llm["model"]]
    i = llm.get("_chain_pos", 0) % len(chain)
    for attempt in range(1, 11):
        model = chain[i]
        try:
            r = _call(dict(llm, model=model), provider, system, prompt)
        except requests.exceptions.RequestException as e:
            r, why = None, type(e).__name__
        else:
            why = str(r.status_code)
        if r is not None and r.status_code == 200:
            llm["_chain_pos"] = i  # stick with the model that works
            if provider == "gemini":
                try:
                    parts = r.json()["candidates"][0]["content"]["parts"]
                    return "".join(p.get("text", "") for p in parts if not p.get("thought"))
                except (KeyError, IndexError):
                    why = "empty answer"
            else:
                return "".join(b.get("text", "") for b in r.json()["content"])
        elif r is not None and r.status_code not in (404, 408, 429, 500, 502, 503, 504, 529) and \
                not (r.status_code == 400 and "think" in r.text.lower()):
            raise SystemExit(f"AI error {r.status_code} ({model}): {r.text[:400]}")
        if r is not None and r.status_code == 400:  # model doesn't support the thinking setting
            llm["fast_thinking"] = False
            continue
        nxt = (i + 1) % len(chain)
        wait = min(10 * attempt, 45) if nxt <= i else 3  # a full lap of busy models -> wait longer
        print(f"  {model}: {why} -> trying {chain[nxt]} in {wait}s")
        time.sleep(wait)
        i = nxt
    raise SystemExit("Google's free AI is overloaded right now (all free models busy). Try again in 30-60 minutes.")


def ask_json(cfg: dict, system: str, prompt: str, tries: int = 3):
    """ask_claude + parse JSON; repairs small mistakes and asks again if the reply is broken."""
    last = None
    for k in range(tries):
        text = ask_claude(cfg, system, prompt if k == 0 else
                          prompt + "\n\nIMPORTANT: your last reply was not valid JSON. Reply with valid JSON only.")
        try:
            return extract_json(text)
        except ValueError as e:
            last = e
            print(f"  AI reply was not valid JSON ({e}); asking again")
            cfg["llm"]["_chain_pos"] = cfg["llm"].get("_chain_pos", 0) + 1  # try another model
    raise SystemExit(f"AI kept returning broken JSON: {last}")


_RESOLVED: dict = {}
_MODELS: list | None = None


def _list_models() -> list[dict]:
    global _MODELS
    if _MODELS is None:
        import requests
        try:
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=300",
                             headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}, timeout=30)
            r.raise_for_status()
            _MODELS = [m for m in r.json().get("models", [])
                       if "generateContent" in m.get("supportedGenerationMethods", [])]
        except Exception as e:  # noqa: BLE001
            print(f"  could not list Gemini models ({e})")
            _MODELS = []
    return _MODELS


def resolve_model(name: str) -> str:
    """'auto-lite' / 'auto-flash' / 'auto-pro' -> newest matching Gemini model your key can use."""
    if not name.startswith("auto-"):
        return name
    if name not in _RESOLVED:
        kind = {"auto-lite": "flash-lite", "auto-flash": "flash", "auto-pro": "pro"}.get(name, "flash")
        best = pick_model(_list_models(), kind)
        _RESOLVED[name] = best or ("gemini-flash-lite-latest" if kind == "flash-lite" else "gemini-flash-latest")
        print(f"  {name} -> {_RESOLVED[name]}")
    return _RESOLVED[name]


def model_chain(llm: dict) -> list[str]:
    """Chosen model first, then other free Flash / Flash-Lite models as backups (newest first)."""
    if "_chain" in llm:
        return llm["_chain"]
    chain = [resolve_model(llm["model"])]
    for extra in [llm.get("fallback_model", "auto-lite"), "auto-flash", "auto-lite"]:
        chain.append(resolve_model(extra))
    for kind in ("flash", "flash-lite"):  # every other stable flash model, newest first
        for n in ranked_models(_list_models(), kind):
            chain.append(n)
    seen, out = set(), []
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    llm["_chain"] = out[:6]
    print(f"  AI models to try: {', '.join(llm['_chain'])}")
    return llm["_chain"]


def ranked_models(models: list[dict], kind: str) -> list[str]:
    def ver(n):
        m = re.match(r"gemini-(\d+(?:\.\d+)?)-(.*)$", n)
        return (float(m.group(1)), m.group(2)) if m else (0, "")
    cands = []
    for m in models:
        n = m["name"].split("/")[-1]
        v, rest = ver(n)
        if not v or any(x in rest for x in ("preview", "exp", "image", "tts", "audio", "live", "embedding", "thinking")):
            continue
        base = rest.split("-0")[0]
        if base == kind:
            cands.append((v, n))
    return [n for _, n in sorted(cands, reverse=True)]


def pick_model(models: list[dict], kind: str) -> str | None:
    r = ranked_models(models, kind)
    return r[0] if r else None


def _call(llm, provider, system, prompt):
    import requests

    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("Set GEMINI_API_KEY (free at https://aistudio.google.com/apikey).")
        gen = {"maxOutputTokens": llm.get("max_tokens", 16000), "responseMimeType": "application/json"}
        if llm.get("fast_thinking", True) and "lite" not in llm["model"]:
            gen["thinkingConfig"] = {"thinkingLevel": "low"}
        return requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{llm['model']}:generateContent",
            headers={"x-goog-api-key": key, "content-type": "application/json"},
            json={"systemInstruction": {"parts": [{"text": system}]},
                  "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                  "generationConfig": gen},
            timeout=llm.get("timeout_seconds", 150),
        )
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("Set ANTHROPIC_API_KEY in your environment or in a .env file.")
    return requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": llm["model"], "max_tokens": llm.get("max_tokens", 8000),
              "system": system, "messages": [{"role": "user", "content": prompt}]},
        timeout=600,
    )


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply, fixing common small mistakes."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON found")
    text = text[min(starts):]
    try:
        return json.JSONDecoder().raw_decode(text)[0]
    except json.JSONDecodeError:
        pass
    fixed = re.sub(r"//[^\n\"]*$", "", text, flags=re.M)          # // comments
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)                    # trailing commas
    fixed = re.sub(r"([{,]\s*)([A-Za-z_]\w*)(\s*:)", r'\1"\2"\3', fixed)  # unquoted keys
    try:
        return json.JSONDecoder().raw_decode(fixed)[0]
    except json.JSONDecodeError as e:
        raise ValueError(str(e)) from None


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
