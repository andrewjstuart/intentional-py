from pathlib import Path

from intentional_py import user_settings
from intentional_py.models import NamingRules


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
