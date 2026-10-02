"""Naming-rule, project-layout, NL-default and language-settings overrides kept between
sessions, in the user's profile, shared by the CLI and the GUI (unlike gui/settings.py,
which is GUI-only convenience preferences).

Windows: %APPDATA%\\Intentional\\<name>.json; elsewhere ~/.config/intentional/<name>.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from intentional_py.models import (
    LanguageSettings,
    NamingRules,
    NlDefaults,
    ProjectLayout,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def _settings_path(file_name: str) -> Path:
    if os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"], "Intentional", file_name)
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base, "intentional", file_name)


def _load(model: type[ModelT], path: Path) -> ModelT:
    """The saved settings; a missing or damaged file gives the model's defaults."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return model()
    try:
        return model.model_validate(data)
    except ValidationError:
        return model()


def _save(value: BaseModel, path: Path) -> None:
    """Best effort: a failure to save is ignored, same as gui/settings.py."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value.model_dump_json(indent=2), encoding="utf-8")
    except OSError:
        pass


def naming_rules_path() -> Path:
    return _settings_path("naming_rules.json")


def load_naming_rules(path: Path | None = None) -> NamingRules:
    return _load(NamingRules, path or naming_rules_path())


def save_naming_rules(rules: NamingRules, path: Path | None = None) -> None:
    _save(rules, path or naming_rules_path())


def project_layout_path() -> Path:
    return _settings_path("project_layout.json")


def load_project_layout(path: Path | None = None) -> ProjectLayout:
    return _load(ProjectLayout, path or project_layout_path())


def save_project_layout(layout: ProjectLayout, path: Path | None = None) -> None:
    _save(layout, path or project_layout_path())


def nl_defaults_path() -> Path:
    return _settings_path("nl_defaults.json")


def load_nl_defaults(path: Path | None = None) -> NlDefaults:
    return _load(NlDefaults, path or nl_defaults_path())


def save_nl_defaults(nl_defaults: NlDefaults, path: Path | None = None) -> None:
    _save(nl_defaults, path or nl_defaults_path())


def language_settings_path() -> Path:
    return _settings_path("language_settings.json")


def load_language_settings(path: Path | None = None) -> LanguageSettings:
    return _load(LanguageSettings, path or language_settings_path())


def save_language_settings(
    settings: LanguageSettings, path: Path | None = None
) -> None:
    _save(settings, path or language_settings_path())
