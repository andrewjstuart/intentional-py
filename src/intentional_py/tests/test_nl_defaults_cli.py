from pathlib import Path

import pytest
from typer.testing import CliRunner

from intentional_py import intentional, user_settings
from intentional_py.models import NlDefaults

runner = CliRunner()
app = intentional.app


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path: Path) -> None:
    """Keep these tests from reading or writing the real user's settings file."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


def test_nl_defaults_shows_the_default_when_nothing_is_saved() -> None:
    result = runner.invoke(app, ["nl-defaults"])

    assert result.exit_code == 0
    assert "Default NL context: 'GetIntent'" in result.stdout


def test_nl_defaults_can_set_and_persist_a_value() -> None:
    result = runner.invoke(app, ["nl-defaults", "--set-context", "MainContext"])

    assert result.exit_code == 0
    assert "Saved to" in result.stdout
    assert user_settings.load_nl_defaults() == NlDefaults(context="MainContext")

    # a later, unrelated invocation still sees the saved value
    shown = runner.invoke(app, ["nl-defaults"])
    assert "Default NL context: 'MainContext'" in shown.stdout


def test_nl_defaults_can_reset_to_defaults() -> None:
    runner.invoke(app, ["nl-defaults", "--set-context", "MainContext"])

    result = runner.invoke(app, ["nl-defaults", "--reset"])

    assert result.exit_code == 0
    assert user_settings.load_nl_defaults() == NlDefaults()


def test_nl_cli_uses_the_saved_default_context(tmp_path: Path) -> None:
    from intentional_py.tests.conftest import make_nl_phrases

    runner.invoke(app, ["nl-defaults", "--set-context", "MainContext"])
    config = make_nl_phrases(tmp_path)

    result = runner.invoke(
        app, ["nl", "--config", str(config), "-v", "RTL"], input="y\n"
    )

    assert result.exit_code == 0, result.stdout
    assert "MainContext" in config.read_text(encoding="utf-8")
