from pathlib import Path

import pytest
from typer.testing import CliRunner

from intentional_py import intentional, user_settings
from intentional_py.models import NamingRules

runner = CliRunner()
app = intentional.app


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path: Path) -> None:
    """Keep these tests from reading or writing the real user's settings file."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


def test_naming_rules_shows_the_defaults_when_nothing_is_saved() -> None:
    result = runner.invoke(app, ["naming-rules"])

    assert result.exit_code == 0
    assert "Intent forbidden characters: '-'" in result.stdout
    assert "Context discouraged characters: '.'" in result.stdout


def test_naming_rules_can_set_and_persist_a_value() -> None:
    result = runner.invoke(app, ["naming-rules", "--set-intent-forbidden-chars", "_"])

    assert result.exit_code == 0
    assert "Saved to" in result.stdout
    assert user_settings.load_naming_rules() == NamingRules(intent_forbidden_chars="_")

    # a later, unrelated invocation still sees the saved value
    shown = runner.invoke(app, ["naming-rules"])
    assert "Intent forbidden characters: '_'" in shown.stdout


def test_naming_rules_can_reset_to_defaults() -> None:
    runner.invoke(app, ["naming-rules", "--set-intent-forbidden-chars", "_"])

    result = runner.invoke(app, ["naming-rules", "--reset"])

    assert result.exit_code == 0
    assert user_settings.load_naming_rules() == NamingRules()
