"""Local leaderboard: top 10 in a JSON file. Not part of the sim, so headless output is unaffected."""
import json, os, re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.environ.get("DDL_LEADERBOARD", os.path.join(ROOT, "leaderboard.json"))
NAME_RE = re.compile(r"[A-Za-z0-9_]{3,12}")
TOP = 10


def load(path=None):
    try:
        with open(path or PATH) as f:
            return json.load(f)["entries"]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def add(name, score, nights_won, seed, path=None, now=None):
    """Insert an entry; return the new top 10. Raises ValueError on bad input."""
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError("name must be 3-12 characters of A-Z a-z 0-9 _")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (score, nights_won, seed)) or score < 0 or not 0 <= nights_won <= 3:
        raise ValueError("score >= 0, nights_won 0-3, seed integer")
    entries = load(path)
    entries.append({"name": name, "score": score, "nights_won": nights_won,
                    "achieved_at": now or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "seed": seed})
    entries = sorted(entries, key=lambda e: -e["score"])[:TOP]   # sorted() is stable: earlier entry stays above on a tie
    with open(path or PATH, "w") as f:
        json.dump({"entries": entries}, f, indent=1)
    return entries


def export(out, path=None):
    with open(out, "w") as f:
        json.dump({"entries": load(path)}, f, indent=1)
