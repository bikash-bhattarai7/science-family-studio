"""AI writer: topic ideas, the English script, translations and the review sheet."""
from __future__ import annotations

from pathlib import Path

from .common import ROOT, ask_claude, extract_json, lang_codes, new_episode_dir, read_json, write_json
from .cast import CAST
from .places import PLACES
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
    t = read_json(TOPICS_FILE) if TOPICS_FILE.exists() else {}
    if t.get("version") != 2:  # older, less engaging ideas: keep history, refill the queue with new-style topics
        t = {"version": 2, "queue": [], "done": t.get("done", []), "old_ideas": t.get("queue", [])}
    return t


def generate_ideas(cfg, count: int = 12) -> list[str]:
    topics = load_topics()
    used = topics["queue"] + topics["done"] + topics.get("old_ideas", [])
    prompt = f"""Suggest {count} NEW science video topics for a family channel (kids 6-12 + parents).
Make them irresistible to click and easy to search. Mix these formats:
- "Why does my body...?" (hiccups, goosebumps, brain freeze, tummy rumbles)
- "What would happen if...?" (no Moon, you fell into Jupiter, the Earth stopped spinning)
- "Myth or fact?" (do goldfish have 3-second memory? does lightning never strike twice?)
- "Which is bigger / faster / stronger...?" (fastest animal vs fastest car, biggest star)
- everyday kid life: school, food, sleep, pets, playground, screens, weather today
- gross-but-safe and funny (why do farts smell? why is snot green?)
- amazing animals and space records
Rules: phrased as a short question a child would actually say; answerable in 90 seconds; fun to animate;
nothing scary, gory or dangerous to try. Put the 4 most clickable first.
Do NOT repeat or closely overlap these: {used[-200:]}
Return JSON: {{"topics": ["...", "..."]}}"""
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
    cast = "\n".join(f"- {k}: {v['desc']}" for k, v in CAST.items())
    places = "\n".join(f"- {k}: {v['desc']}" for k, v in PLACES.items())
    secs = cfg["video"]["target_seconds"]
    prompt = f"""Write a {secs}-second animated science video answering: "{topic}"

It's a funny, fast animated show. Four original school kids are the main characters; guest
characters appear when they fit the topic. Write it as DIALOGUE: each scene is ONE character speaking.
Use 2-3 kids + at most 1-2 guests. Cast (use these exact keys as "speaker"):
{cast}

Structure (8-11 scenes, each 1-3 SHORT sentences, ~2.3 spoken words per second overall):
1. HOOK in the first 5 seconds: a kid says something surprising, funny or relatable
   ("My hiccups won't STOP!"), then the big question. Visual 'question' or a fitting one.
2. OPEN LOOP: tease the wow fact ("...and wait till you hear what happens on Mars!") to keep viewers watching.
3. Explain step by step with a comparison kids know (food, toys, school, playground). Characters react,
   disagree, joke ("No way!", "Hmph, prove it."). Every 2-3 scenes something surprising happens.
4. The WOW fact that grown-ups enjoy too.
5. A family challenge: a safe try-at-home idea or a quick "pause and guess" quiz.
6. Outro (visual 'outro'): a kid asks viewers a question to answer in the comments, then invites them to subscribe.

Rules:
- Narration is spoken only; nothing is written on screen.
- Give each scene an "emotion" for the speaker: happy, excited, surprised, thinking, grumpy, worried, explaining.
  Vary them - expressions make it fun to watch.
- Never mention or imitate characters from existing films, TV shows or brands.
- Science must be correct. No scary, gory or unsafe content.
- For each scene pick the visual that best matches from this library (never use 'comment_prompt' in "scenes"):
{visuals}

- Give each scene a "place" where the kids are (a real-feeling location; the science animation appears on a
  whiteboard or "imagination window" there). Use 2-3 places per episode that fit the story, and keep the same
  place for several scenes in a row (e.g. start in the classroom, go out to the garden to test it). Places:
{places}

ALSO write "short_question": the last line of the vertical Short. One kid asks an A-or-B question that is easy
to answer in a comment, about the topic, e.g. "Which is faster: A, a cheetah... or B, a race car? Comment A or B!"
Keep it under 20 words. Do not give the answer.

Return JSON:
{{
  "topic": "{topic}",
  "title": "catchy YouTube title under 70 chars, no clickbait lies",
  "description": "2-3 sentence YouTube description",
  "tags": ["10-15 tags"],
  "thumbnail_text": "2-4 punchy words",
  "title_options": ["3 different curiosity-driven titles under 60 chars for A/B testing; honest, no ALL CAPS"],
  "thumbnail_texts": ["3 different 2-4 word thumbnail texts, one per title idea"],
  "chapters": [{{"scene": 0, "title": "short chapter name"}}, "...4-6 chapters, first at scene 0, in order"],
  "pinned_comment": "a fun A-or-B question or mini-quiz for families to answer in the comments, written by one of the kids (e.g. 'Maya here! ...')",
  "community_poll": {{"question": "poll for the YouTube Community tab, posted the day before", "options": ["2-4 short options"]}},
  "playlist": "which series playlist this belongs to, e.g. 'Space Questions', 'Amazing Bodies', 'Earth & Weather', 'Animals', 'Everyday Science'",
  "next_topics": ["2 follow-up topics viewers would want next (for the end screen / next video)"],
  "scenes": [{{"visual": "<library key>", "speaker": "<cast key>", "emotion": "<emotion>", "place": "<place key>", "narration": "..."}}],
  "short_question": {{"speaker": "<kid key>", "narration": "...Comment A or B!", "answer": "the correct answer + one-line reason (for a pinned reply after 24h)"}},
  "short_scenes": [indices of 3-5 consecutive-or-not scenes that make a strong standalone vertical Short under 55 seconds, starting with the hook],
  "fact_check": [{{"claim": "...", "why_true": "...", "source_hint": "e.g. NASA, NOAA, a textbook topic"}}]
}}"""
    data = extract_json(ask_claude(cfg, _system(cfg), prompt))

    emotions = {"happy", "excited", "surprised", "thinking", "grumpy", "worried", "explaining"}
    for s in data["scenes"]:
        if s["visual"] not in VISUAL_LIBRARY or s["visual"] == "comment_prompt":
            s["visual"] = "question"
        if s.get("speaker") not in CAST:
            s["speaker"] = "leo"
        if s.get("emotion") not in emotions:
            s["emotion"] = "happy"
        if s.get("place") not in PLACES:
            s.pop("place", None)  # renderer picks a fitting default
    q = data.get("short_question") or {}
    if q.get("narration"):  # extra scene used only at the end of the Shorts
        data["scenes"].append({"visual": "comment_prompt", "speaker": q.get("speaker") if q.get("speaker") in CAST else "maya",
                               "emotion": "excited", "narration": q["narration"], "short_only": True})

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
    out = {}
    for code in others:  # one language per request: faster and more reliable
        print(f"  translating -> {names[code]}")
        prompt = f"""Translate this kids' science video into {names[code]}.

Rules:
- Natural, warm, spoken style a parent would use with a child. Not word-for-word.
- Keep each scene about the SAME LENGTH as the English (videos share one animation).
- Keep scientific terms correct; use the common local word if one exists.
- Arabic: Modern Standard Arabic, simple. Hindi: everyday Hindi (avoid heavy Sanskrit words).
  Nepali: standard Nepali in Devanagari.
- Character names (Zippy, Professor Hoot, Bubbles, Sparky, Rocky, Dot): keep them, written in the target script.
- Keep each character's personality and jokes (adapt jokes so they work in that language).

English source:
{payload}

Return JSON:
{{"title": "...", "description": "...", "scenes": ["...one per English scene, same order..."]}}"""
        res = extract_json(ask_claude(cfg, _system(cfg), prompt))
        if len(res["scenes"]) != len(data["scenes"]):
            raise SystemExit(f"{names[code]} translation has the wrong number of scenes - run again.")
        out[code] = res

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
        tag = " - SHORT-ONLY comment question" if s.get("short_only") else ""
        lines.append(f"### Scene {i + 1}  ({s.get('speaker', 'leo')}, {s.get('emotion', 'happy')}, {s.get('place', 'auto')}, visual: {s['visual']}){tag}")
        lines += [f"- **{c}**: {s['narration'][c]}" for c in codes]
        lines.append("")
    (ep / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
