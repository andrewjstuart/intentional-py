"""GUI settings kept between sessions, in the user's profile.

Windows: %APPDATA%\\Intentional\\settings.json; elsewhere ~/.config/intentional/settings.json.
"""

import json
import os
from pathlib import Path

MAX_RECENT = 8
DEFAULTS: dict = {
    "recent_projects": [],
    "vertical": "",
    "context": "",
    "lowercase": False,
    "reuse": False,
    "clean": False,
    "extract_mode": "NL",
    "extract_language": "en",
    "compare_mode": "DD",
    "package_style": "restore",
    "check_updates": True,
    "appearance_mode": "system",
}


def settings_path() -> Path:
    if os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"], "Intentional", "settings.json")
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base, "intentional", "settings.json")


def load(path: Path | None = None) -> dict:
    """The saved settings over the defaults; a missing or damaged file gives the defaults."""
    path = path or settings_path()
    settings = dict(DEFAULTS)
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if isinstance(saved, dict):
        settings.update({key: value for key, value in saved.items() if key in DEFAULTS})
    return settings


def save(settings: dict, path: Path | None = None) -> None:
    """Best effort: settings are a convenience, so a failure to save is ignored."""
    path = path or settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def add_recent(settings: dict, project: str) -> None:
    recent = [project] + [
        p for p in settings.get("recent_projects", []) if p != project
    ]
    settings["recent_projects"] = recent[:MAX_RECENT]
