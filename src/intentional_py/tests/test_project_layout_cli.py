from pathlib import Path

import pytest
from typer.testing import CliRunner

from intentional_py import intentional, user_settings
from intentional_py.models import ProjectLayout

runner = CliRunner()
app = intentional.app


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path: Path) -> None:
    """Keep these tests from reading or writing the real user's settings file."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


def test_project_layout_shows_the_defaults_when_nothing_is_saved() -> None:
    result = runner.invoke(app, ["project-layout"])

    assert result.exit_code == 0
    assert "Training phrases folder: 'Training Phrases'" in result.stdout
    assert "Intents output folder: 'intents'" in result.stdout
    assert "NL phrases subfolder: 'NL'" in result.stdout
    assert "Directed dialog config file: 'intents.cfg'" in result.stdout
    assert "Natural language config file: 'intents_nl.cfg'" in result.stdout


def test_project_layout_can_set_and_persist_a_value() -> None:
    result = runner.invoke(app, ["project-layout", "--set-intents-dir", "output"])

    assert result.exit_code == 0
    assert "Saved to" in result.stdout
    assert user_settings.load_project_layout() == ProjectLayout(intents_dir="output")

    # a later, unrelated invocation still sees the saved value
    shown = runner.invoke(app, ["project-layout"])
    assert "Intents output folder: 'output'" in shown.stdout


def test_project_layout_can_reset_to_defaults() -> None:
    runner.invoke(app, ["project-layout", "--set-intents-dir", "output"])

    result = runner.invoke(app, ["project-layout", "--reset"])

    assert result.exit_code == 0
    assert user_settings.load_project_layout() == ProjectLayout()
