"""Voices (edge-tts), scene timing shared by all languages, mixed tracks and captions."""
from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from .common import SAMPLE_RATE, decode_audio, lang_codes, write_json, write_wav

# rough speaking speeds (words/sec) for demo mode without real voices
_DEMO_WPS = {"en": 2.5, "ar": 2.1, "hi": 2.3, "ne": 2.2}


# ---------------------------------------------------------------- voices
def make_voices(cfg, ep: Path, data: dict, demo: bool = False) -> None:
    vdir = ep / "voices"
    vdir.mkdir(exist_ok=True)
    jobs = []
    for i, scene in enumerate(data["scenes"]):
        for code in lang_codes(cfg):
            out = vdir / f"{code}_{i:02d}.mp3"
            if out.exists():
                continue
            text = scene["narration"][code]
            if demo:
                secs = max(1.5, len(text.split()) / _DEMO_WPS.get(code, 2.3))
                _demo_voice(out.with_suffix(".wav"), secs)
            else:
                from .cast import voice_for
                jobs.append((text, *voice_for(cfg, code, scene.get("speaker")), out, cfg["languages"][code]["voice"]))
    if jobs:
        asyncio.run(_tts_all(jobs))


async def _tts_all(jobs):
    import edge_tts

    sem = asyncio.Semaphore(4)

    async def one(text, voice, rate, pitch, out, backup_voice):
        async with sem:
            for attempt in range(4):
                if attempt == 2 and voice != backup_voice:  # this voice keeps failing: use the language's main voice
                    print(f"  {out.name}: switching voice {voice} -> {backup_voice}")
                    voice = backup_voice
                try:
                    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(out))
                    print(f"  voice ok: {out.name}")
                    return
                except Exception as e:  # network hiccups
                    print(f"  retry {out.name}: {e}")
                    await asyncio.sleep(2 + attempt * 3)
            raise RuntimeError(f"TTS failed for {out.name}")

    await asyncio.gather(*(one(*j) for j in jobs))


def _demo_voice(path: Path, secs: float) -> None:
    """Placeholder 'voice' for offline demo: soft blips so you can hear the timing."""
    t = np.arange(int(secs * SAMPLE_RATE)) / SAMPLE_RATE
    syll = (np.sin(2 * np.pi * 4.2 * t) > 0.2).astype(np.float32)
    voice = 0.06 * np.sin(2 * np.pi * (180 + 30 * np.sin(2 * np.pi * 0.7 * t)) * t) * syll
    write_wav(path, voice)


def _voice_file(ep: Path, code: str, i: int) -> Path:
    for ext in (".mp3", ".wav"):
        p = ep / "voices" / f"{code}_{i:02d}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"missing voice {code}_{i:02d}")


# ---------------------------------------------------------------- timeline
def build_timeline(cfg, ep: Path, data: dict, scene_ids: list[int]) -> dict:
    """Each scene lasts as long as its LONGEST language, so one animation fits all tracks."""
    v = cfg["video"]
    lead, tail = v["scene_lead_in"], v["scene_tail"]
    clips, scenes, t = {}, [], 0.0
    for i in scene_ids:
        lens = {}
        for code in lang_codes(cfg):
            a = decode_audio(_voice_file(ep, code, i))
            clips[(code, i)] = a
            lens[code] = len(a) / SAMPLE_RATE
        dur = lead + max(lens.values()) + tail
        scenes.append({"index": i, "visual": data["scenes"][i]["visual"],
                       "speaker": data["scenes"][i].get("speaker", "leo"),
                       "emotion": data["scenes"][i].get("emotion", "happy"), "start": t,
                       "duration": dur, "speech": {c: [t + lead, t + lead + l] for c, l in lens.items()}})
        t += dur
    return {"total": t, "scenes": scenes, "_clips": clips}


def mix_tracks(cfg, ep: Path, tl: dict, name: str) -> dict[str, Path]:
    """One complete audio track per language (voice + music), all identical length."""
    tdir = ep / "tracks"
    tdir.mkdir(exist_ok=True)
    n = int(tl["total"] * SAMPLE_RATE) + SAMPLE_RATE // 2
    music = _music(cfg, n, seed=sum(ep.name.encode()) % 10000)
    out = {}
    for code in lang_codes(cfg):
        voice = np.zeros(n, np.float32)
        for sc in tl["scenes"]:
            a = tl["_clips"][(code, sc["index"])]
            s = int(sc["speech"][code][0] * SAMPLE_RATE)
            voice[s:s + len(a)] += a[: n - s]
        peak = np.abs(voice).max() or 1.0
        voice *= min(1.0, 0.89 / peak)
        duck = 1.0 - 0.55 * _envelope(np.abs(voice) > 0.01, 0.25)
        mix = voice + music * duck
        p = tdir / f"{name}_{code}.wav"
        write_wav(p, mix)
        out[code] = p
    return out


def _envelope(mask: np.ndarray, secs: float) -> np.ndarray:
    k = int(secs * SAMPLE_RATE)
    c = np.convolve(mask.astype(np.float32), np.ones(k) / k, mode="same")
    return np.clip(c * 3, 0, 1)


def _music(cfg, n: int, seed: int) -> np.ndarray:
    choice = cfg["video"].get("music", "builtin")
    vol = cfg["video"].get("music_volume", 0.1)
    if choice in (None, "none"):
        return np.zeros(n, np.float32)
    if choice != "builtin":
        m = decode_audio(Path(choice))
        m = np.tile(m, n // len(m) + 1)[:n]
        return (m / (np.abs(m).max() or 1) * vol).astype(np.float32)
    # builtin: cheerful pentatonic music-box loop
    rng = np.random.default_rng(seed)
    scale = [0, 2, 4, 7, 9, 12, 14, 16]
    base = 523.25  # C5
    bpm, out = 104, np.zeros(n, np.float32)
    step = int(SAMPLE_RATE * 60 / bpm / 2)
    note_len = int(SAMPLE_RATE * 0.9)
    t = np.arange(note_len) / SAMPLE_RATE
    env = np.exp(-t * 5)
    pattern = rng.choice(scale, 16)
    chords = [0, -5, -3, -7]  # C, G, A, F-ish roots for a soft bass
    for k, pos in enumerate(range(0, n, step)):
        if rng.random() < 0.82:
            f = base * 2 ** (pattern[k % 16] / 12)
            tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * env * 0.35
            seg = out[pos:pos + note_len]
            seg += tone[: len(seg)]
        if k % 8 == 0:
            f = 130.81 * 2 ** (chords[(k // 8) % 4] / 12)
            tb = np.arange(step * 8) / SAMPLE_RATE
            bass = np.sin(2 * np.pi * f * tb) * np.exp(-tb * 1.2) * 0.4
            seg = out[pos:pos + len(bass)]
            seg += bass[: len(seg)]
    return (out / (np.abs(out).max() or 1) * vol).astype(np.float32)


# ---------------------------------------------------------------- captions
def write_captions(cfg, ep: Path, data: dict, tl: dict, name: str) -> dict[str, Path]:
    cdir = ep / "captions"
    cdir.mkdir(exist_ok=True)
    out = {}
    for code in lang_codes(cfg):
        cues = []
        for sc in tl["scenes"]:
            text = data["scenes"][sc["index"]]["narration"][code]
            a, b = sc["speech"][code]
            parts = _split_sentences(text)
            total = sum(len(p) for p in parts) or 1
            t = a
            for p in parts:
                d = (b - a) * len(p) / total
                cues.append((t, t + d, p))
                t += d
        p = cdir / f"{name}_{code}.srt"
        p.write_text("\n".join(f"{i}\n{_ts(s)} --> {_ts(e)}\n{txt}\n" for i, (s, e, txt) in enumerate(cues, 1)),
                     encoding="utf-8")
        out[code] = p
    return out


def _split_sentences(text: str) -> list[str]:
    import re
    parts = [p.strip() for p in re.split(r"(?<=[.!?।؟])\s+", text) if p.strip()]
    return parts or [text]


def _ts(s: float) -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def save_timeline(ep: Path, tl: dict, name: str) -> None:
    write_json(ep / f"timeline_{name}.json", {k: v for k, v in tl.items() if not k.startswith("_")})
