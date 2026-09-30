"""Naming-rule overrides kept between sessions, in the user's profile, shared by the CLI
and the GUI (unlike gui/settings.py, which is GUI-only convenience preferences).

Windows: %APPDATA%\\Intentional\\naming_rules.json; elsewhere ~/.config/intentional/naming_rules.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from intentional_py.models import NamingRules


def naming_rules_path() -> Path:
    if os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"], "Intentional", "naming_rules.json")
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base, "intentional", "naming_rules.json")


def load_naming_rules(path: Path | None = None) -> NamingRules:
    """The saved naming rules; a missing or damaged file gives the original defaults."""
    path = path or naming_rules_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return NamingRules()
    try:
        return NamingRules.model_validate(data)
    except ValidationError:
        return NamingRules()


def save_naming_rules(rules: NamingRules, path: Path | None = None) -> None:
    """Best effort: a failure to save is ignored, same as gui/settings.py."""
    path = path or naming_rules_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rules.model_dump_json(indent=2), encoding="utf-8")
    except OSError:
        pass
