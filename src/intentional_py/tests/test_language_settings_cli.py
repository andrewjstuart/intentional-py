from pathlib import Path

import pytest
from typer.testing import CliRunner

from intentional_py import intentional, user_settings
from intentional_py.models import LanguageSettings

runner = CliRunner()
app = intentional.app


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path: Path) -> None:
    """Keep these tests from reading or writing the real user's settings file."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


def test_language_settings_shows_the_defaults_when_nothing_is_saved() -> None:
    result = runner.invoke(app, ["language-settings"])

    assert result.exit_code == 0
    assert "Default language: 'en'" in result.stdout
    assert "en: English" in result.stdout
    assert "es: Spanish" in result.stdout
    assert "fr: French" in result.stdout


def test_language_settings_can_add_a_language_with_a_catalog_lookup() -> None:
    result = runner.invoke(app, ["language-settings", "--add", "de"])

    assert result.exit_code == 0
    assert "Saved to" in result.stdout
    assert user_settings.load_language_settings().languages["de"] == "German"


def test_language_settings_can_add_a_language_with_an_explicit_name() -> None:
    result = runner.invoke(app, ["language-settings", "--add", "xx=Madeup"])

    assert result.exit_code == 0
    assert user_settings.load_language_settings().languages["xx"] == "Madeup"


def test_language_settings_rejects_an_unknown_code_without_a_name() -> None:
    result = runner.invoke(app, ["language-settings", "--add", "xx"])

    assert result.exit_code == 1
    assert "not in the Dialogflow ES catalog" in result.stdout


def test_language_settings_can_remove_a_language() -> None:
    result = runner.invoke(app, ["language-settings", "--remove", "fr"])

    assert result.exit_code == 0
    assert "fr" not in user_settings.load_language_settings().languages


def test_language_settings_cannot_remove_the_default_language() -> None:
    result = runner.invoke(app, ["language-settings", "--remove", "en"])

    assert result.exit_code == 1
    assert "is the default language" in result.stdout
    assert "en" in user_settings.load_language_settings().languages


def test_language_settings_can_change_the_default() -> None:
    runner.invoke(app, ["language-settings", "--add", "de"])

    result = runner.invoke(app, ["language-settings", "--set-default", "de"])

    assert result.exit_code == 0
    assert user_settings.load_language_settings().default_language == "de"


def test_language_settings_rejects_a_default_not_in_the_set() -> None:
    result = runner.invoke(app, ["language-settings", "--set-default", "de"])

    assert result.exit_code == 1
    assert "add it first" in result.stdout


def test_language_settings_can_reset_to_defaults() -> None:
    runner.invoke(app, ["language-settings", "--add", "de"])
    runner.invoke(app, ["language-settings", "--set-default", "de"])

    result = runner.invoke(app, ["language-settings", "--reset"])

    assert result.exit_code == 0
    assert user_settings.load_language_settings() == LanguageSettings()
