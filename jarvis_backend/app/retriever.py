import json
import os
from typing import List, Optional

KB_PATH = os.path.join(os.path.dirname(__file__), "hotkeys.json")


def _load_kb():
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"entries": []}


def _score_entry(text: str, keywords: List[str]) -> int:
    t = text.lower()
    score = 0
    for k in keywords:
        if k.lower() in t:
            score += 1
    return score


def get_structured_hotkeys(user_text: str, platform: Optional[str] = None):
    """
    Return a structured list of actions for the user's platform based on simple keyword overlap.
    The structure matches what `script_generator` can consume.
    """
    kb = _load_kb()
    entries = kb.get("entries", [])
    scored = []
    for e in entries:
        kws = e.get("keywords", [])
        score = _score_entry(user_text, kws)
        if score > 0:
            scored.append((score, e))

    if not scored:
        return None

    # pick the best scoring entry
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]

    platform = (platform or "").lower()
    plat_actions = best.get("platforms", {}).get(platform) or best.get("platforms", {}).get("mac") or best.get("platforms", {}).get("windows")
    return plat_actions


def get_relevant_facts(user_text: str) -> List[str]:
    """Return human readable facts extracted from the KB for prompt augmentation (optional)."""
    kb = _load_kb()
    entries = kb.get("entries", [])
    facts = []
    for e in entries:
        kws = e.get("keywords", [])
        for k in kws:
            if k.lower() in user_text.lower():
                facts.append(e.get("summary", ""))
                break
    return facts
