import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

if getattr(sys, 'frozen', False):
    if sys.platform == 'darwin':
        _BASE = Path.home() / "Library" / "Application Support" / "LaybackPassion"
    elif sys.platform == 'win32':
        _BASE = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / "LaybackPassion"
    else:
        _BASE = Path.home() / ".local" / "share" / "LaybackPassion"
else:
    _BASE = Path(__file__).parent.parent / "data"

DATA_DIR = _BASE
BOOKMARK_PATH = DATA_DIR / "bookmark.json"

MatchDict = dict


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load() -> list[MatchDict]:
    if not BOOKMARK_PATH.exists():
        return []
    try:
        with open(BOOKMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("matches", [])
    except (json.JSONDecodeError, KeyError):
        return []


def save(matches: list[MatchDict]):
    _ensure_dir()
    with open(BOOKMARK_PATH, "w", encoding="utf-8") as f:
        json.dump({"matches": matches, "last_update": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def get_overnight(matches: list[MatchDict]) -> list[MatchDict]:
    now = datetime.now(timezone(timedelta(hours=8)))
    return [m for m in matches if _is_overnight(m, now)]


def get_unwatched(matches: list[MatchDict]) -> list[MatchDict]:
    return [m for m in matches if not m.get("watched", False)]


def get_unwatched_overnight(matches: list[MatchDict]) -> list[MatchDict]:
    now = datetime.now(timezone(timedelta(hours=8)))
    return [m for m in matches if not m.get("watched", False) and _is_overnight(m, now)]


def _is_overnight(match: MatchDict, now: datetime) -> bool:
    try:
        match_time = datetime.fromisoformat(match["time"])
        hours_ago = (now - match_time).total_seconds() / 3600
        return 0 <= hours_ago < 18 and match_time.hour < 10
    except (ValueError, KeyError):
        return False


def mark_watched(match_id: str):
    matches = load()
    for m in matches:
        if m["id"] == match_id:
            m["watched"] = True
            break
    save(matches)


def update_matches(new_matches: list[MatchDict]):
    existing = {m["id"]: m for m in load()}
    for m in new_matches:
        if m["id"] in existing:
            existing[m["id"]]["replay_available"] = m.get("replay_available", False)
            existing[m["id"]]["replay_url"] = m.get("replay_url", "")
        else:
            existing[m["id"]] = m
    save(list(existing.values()))
