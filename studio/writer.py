"""AI writer: topic ideas, the English script, translations and the review sheet."""
from __future__ import annotations

from pathlib import Path

from .common import ROOT, ask_claude, extract_json, lang_codes, new_episode_dir, read_json, write_json
from .visuals import VISUAL_LIBRARY

TOPICS_FILE = ROOT / "topics.json"


def _system(cfg):
    return (
        f"You are the head writer of '{cfg['channel_name']}', an animated science channel. "
        f"Audience: {cfg['audience']} "
        f"The host is a friendly robot called {cfg['mascot_name']}. "
        "Be accurate first, fun second. No scary or gory content. Reply with JSON only."
    )


# ---------------------------------------------------------------- ideas
def load_topics() -> dict:
    if TOPICS_FILE.exists():
        return read_json(TOPICS_FILE)
    return {"queue": [], "done": []}


def generate_ideas(cfg, count: int = 12) -> list[str]:
    topics = load_topics()
    used = topics["queue"] + topics["done"]
    prompt = (
        f"Suggest {count} new video topics phrased as questions a curious child would ask "
        "(e.g. 'Why is the sky blue?'). Mix space, earth, body, animals, chemistry, physics, plants, weather. "
        "Each must be explainable in 90 seconds and fun to animate. "
        f"Do NOT repeat or closely overlap these: {used[-200:]}\n"
        'Return JSON: {"topics": ["...", "..."]}'
    )
    new = extract_json(ask_claude(cfg, _system(cfg), prompt))["topics"]
    topics["queue"].extend(t for t in new if t not in used)
    write_json(TOPICS_FILE, topics)
    return new


def next_topic(cfg) -> str:
    topics = load_topics()
    if not topics["queue"]:
        generate_ideas(cfg)
        topics = load_topics()
    return topics["queue"][0]


def mark_topic_done(topic: str) -> None:
    topics = load_topics()
    if topic in topics["queue"]:
        topics["queue"].remove(topic)
    if topic not in topics["done"]:
        topics["done"].append(topic)
    write_json(TOPICS_FILE, topics)


# ---------------------------------------------------------------- script
def write_script(cfg, topic: str) -> Path:
    visuals = "\n".join(f"- {k}: {v['desc']}" for k, v in VISUAL_LIBRARY.items())
    secs = cfg["video"]["target_seconds"]
    prompt = f"""Write a {secs}-second animated science video answering: "{topic}"

Structure (7-10 scenes, each 1-3 short sentences, ~2.3 spoken words per second overall):
1. Hook: a surprising question or "did you know" (scene visual 'question' or a fitting one).
2. Explain step by step with a simple everyday comparison kids know.
3. One "wow" fact that grown-ups will enjoy too.
4. A safe try-at-home idea or quick quiz question for the family (no fire, no chemicals beyond kitchen basics).
5. Short outro inviting families to subscribe (visual 'outro').

Rules:
- Narration is spoken only; nothing is written on screen, so never say "as you can see here written".
- {cfg['mascot_name']} the robot is the narrator and can make one gentle joke per video.
- For each scene pick the visual that best matches from this library:
{visuals}

Return JSON:
{{
  "topic": "{topic}",
  "title": "catchy YouTube title under 70 chars, no clickbait lies",
  "description": "2-3 sentence YouTube description",
  "tags": ["10-15 tags"],
  "thumbnail_text": "2-4 punchy words",
  "scenes": [{{"visual": "<library key>", "narration": "..."}}],
  "short_scenes": [indices of 3-5 consecutive-or-not scenes that make a strong standalone vertical Short under 55 seconds, starting with the hook],
  "fact_check": [{{"claim": "...", "why_true": "...", "source_hint": "e.g. NASA, NOAA, a textbook topic"}}]
}}"""
    data = extract_json(ask_claude(cfg, _system(cfg), prompt))

    for s in data["scenes"]:
        if s["visual"] not in VISUAL_LIBRARY:
            s["visual"] = "question"

    # ---- translate every spoken/written string
    data = translate(cfg, data)
    ep = new_episode_dir(topic)
    write_json(ep / "script.json", data)
    write_review(cfg, ep, data)
    return ep


def translate(cfg, data: dict) -> dict:
    codes = lang_codes(cfg)
    primary, others = codes[0], codes[1:]
    if not others:  # English-only mode: just wrap strings per language
        data["title"] = {primary: data["title"]}
        data["description"] = {primary: data["description"]}
        for s in data["scenes"]:
            s["narration"] = {primary: s["narration"]}
        return data
    names = {c: cfg["languages"][c]["name"] for c in others}
    payload = {
        "title": data["title"],
        "description": data["description"],
        "scenes": [s["narration"] for s in data["scenes"]],
    }
    prompt = f"""Translate this kids' science video into: {names}.

Rules:
- Natural, warm, spoken style a parent would use with a child. Not word-for-word.
- Keep each scene about the SAME LENGTH as the English (videos share one animation).
- Keep scientific terms correct; use the common local word if one exists.
- Arabic: Modern Standard Arabic, simple. Hindi: everyday Hindi (avoid heavy Sanskrit words).
  Nepali: standard Nepali in Devanagari.
- Keep the robot's name "{cfg['mascot_name']}" unchanged.

English source:
{payload}

Return JSON:
{{"<lang code>": {{"title": "...", "description": "...", "scenes": ["...one per English scene, same order..."]}} }}"""
    out = extract_json(ask_claude(cfg, _system(cfg), prompt))

    data["title"] = {primary: data["title"], **{c: out[c]["title"] for c in others}}
    data["description"] = {primary: data["description"], **{c: out[c]["description"] for c in others}}
    for i, s in enumerate(data["scenes"]):
        s["narration"] = {primary: s["narration"], **{c: out[c]["scenes"][i] for c in others}}
    return data


def write_review(cfg, ep: Path, data: dict) -> None:
    codes = lang_codes(cfg)
    lines = [f"# Review: {data['topic']}", "",
             "Check every fact and translation. Edit script.json directly if needed,",
             f"then run:  python run.py approve {ep.name}", "",
             "## Fact check"]
    for f in data.get("fact_check", []):
        lines.append(f"- [ ] **{f['claim']}** - {f['why_true']} _(check: {f.get('source_hint', '')})_")
    lines += ["", "## Titles"]
    lines += [f"- **{c}**: {data['title'][c]}" for c in codes]
    lines += ["", "## Scenes"]
    for i, s in enumerate(data["scenes"]):
        lines.append(f"### Scene {i + 1}  (visual: {s['visual']})")
        lines += [f"- **{c}**: {s['narration'][c]}" for c in codes]
        lines.append("")
    (ep / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
