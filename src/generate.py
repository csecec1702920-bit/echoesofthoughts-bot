"""Generate an original, deep quote + a short caption.

Order of preference (all optional, the bot always works):
  1. Google Gemini  - FREE tier, set GEMINI_API_KEY   (default)
  2. Anthropic Claude - paid, set ANTHROPIC_API_KEY
  3. Built-in bank  - data/quote_bank.json, no key needed (60 quotes)
"""
import json
import os
import random
import re
from datetime import date
from pathlib import Path

import requests

BANK = Path(__file__).resolve().parent.parent / "data" / "quote_bank.json"

PROMPT = """You write for an Instagram page of deep, thoughtful, ORIGINAL quotes.

Today's theme: {theme}

Write ONE original quote (never quote or paraphrase a famous person) that:
- is at most {max_words} words, and reads well on an image
- has a twist, contrast or quiet insight; avoid cliché motivational language
- uses plain, timeless English

Also write:
- "reflection": one or two sentences expanding the idea for the caption (max 35 words)
- "question": one open question that invites people to comment (max 15 words)

Do NOT reuse or closely resemble any of these previous quotes:
{previous}

Reply with ONLY a JSON object: {{"quote": "...", "reflection": "...", "question": "..."}}"""


def pick_theme(themes, today=None):
    today = today or date.today()
    return themes[today.toordinal() % len(themes)]


def _parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    q = json.loads(m.group(0))
    return q if all(k in q for k in ("quote", "reflection", "question")) else None


def _gemini(prompt, model):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "content-type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json"}},
        timeout=60,
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return _parse("".join(p.get("text", "") for p in parts))


def _claude(prompt, model):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 400, "temperature": 1.0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    r.raise_for_status()
    return _parse("".join(b.get("text", "") for b in r.json()["content"]))


def _norm(s):
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def generate(cfg, history):
    theme = pick_theme(cfg["themes"])
    seen = {_norm(h["quote"]) for h in history}
    previous = "\n".join(f"- {h['quote']}" for h in history[-40:]) or "- (none yet)"
    prompt = PROMPT.format(theme=theme, max_words=cfg["max_quote_words"], previous=previous)

    providers = [("Gemini", _gemini, cfg.get("gemini_model", "gemini-flash-latest")),
                 ("Claude", _claude, cfg.get("claude_model", "claude-sonnet-4-5"))]
    for name, fn, model in providers:
        for _ in range(3):
            try:
                q = fn(prompt, model)
            except Exception as e:  # quota, network, bad model name...
                print(f"[generate] {name} failed: {e}")
                q = None
            if q is None:
                break
            if _norm(q["quote"]) not in seen and len(q["quote"].split()) <= cfg["max_quote_words"] + 4:
                q["theme"] = theme
                q["source"] = name
                return q

    bank = json.loads(BANK.read_text())
    unused = [b for b in bank if _norm(b["quote"]) not in seen]
    if not unused:
        raise RuntimeError("Quote bank exhausted. Add GEMINI_API_KEY (free) or more quotes to data/quote_bank.json.")
    q = dict(random.choice(unused))
    q["theme"] = theme
    q["source"] = "bank"
    print(f"[generate] Using built-in quote bank ({len(unused) - 1} left).")
    return q
