from pathlib import Path

from intentional_py import user_settings
from intentional_py.models import NamingRules, ProjectLayout


def test_load_naming_rules_defaults_when_file_is_missing(tmp_path: Path) -> None:
    rules = user_settings.load_naming_rules(tmp_path / "does-not-exist.json")

    assert rules == NamingRules()


def test_load_naming_rules_defaults_when_file_is_damaged(tmp_path: Path) -> None:
    path = tmp_path / "naming_rules.json"
    path.write_text("not json", encoding="utf-8")

    assert user_settings.load_naming_rules(path) == NamingRules()


def test_load_naming_rules_defaults_when_file_has_the_wrong_shape(
    tmp_path: Path,
) -> None:
    path = tmp_path / "naming_rules.json"
    path.write_text('["not", "a", "dict"]', encoding="utf-8")

    assert user_settings.load_naming_rules(path) == NamingRules()


def test_save_and_load_naming_rules_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "settings" / "naming_rules.json"
    rules = NamingRules(intent_forbidden_chars="_", context_discouraged_chars="")

    user_settings.save_naming_rules(rules, path)

    assert user_settings.load_naming_rules(path) == rules


def test_naming_rules_path_uses_appdata_or_xdg_config(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert (
        user_settings.naming_rules_path()
        == tmp_path / "Intentional" / "naming_rules.json"
    )

    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert (
        user_settings.naming_rules_path()
        == tmp_path / "intentional" / "naming_rules.json"
    )


def test_load_project_layout_defaults_when_file_is_missing(tmp_path: Path) -> None:
    layout = user_settings.load_project_layout(tmp_path / "does-not-exist.json")

    assert layout == ProjectLayout()


def test_load_project_layout_defaults_when_file_is_damaged(tmp_path: Path) -> None:
    path = tmp_path / "project_layout.json"
    path.write_text("not json", encoding="utf-8")

    assert user_settings.load_project_layout(path) == ProjectLayout()


def test_load_project_layout_defaults_when_file_has_the_wrong_shape(
    tmp_path: Path,
) -> None:
    path = tmp_path / "project_layout.json"
    path.write_text('["not", "a", "dict"]', encoding="utf-8")

    assert user_settings.load_project_layout(path) == ProjectLayout()


def test_save_and_load_project_layout_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "settings" / "project_layout.json"
    layout = ProjectLayout(intents_dir="output", nl_subfolder="natural-language")

    user_settings.save_project_layout(layout, path)

    assert user_settings.load_project_layout(path) == layout


def test_project_layout_path_uses_appdata_or_xdg_config(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert (
        user_settings.project_layout_path()
        == tmp_path / "Intentional" / "project_layout.json"
    )

    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert (
        user_settings.project_layout_path()
        == tmp_path / "intentional" / "project_layout.json"
    )
