import queue
import threading
from pathlib import Path

import pytest

from intentional_py import exceptions
from intentional_py.gui import actions
from intentional_py.gui.worker import GuiReporter, JobRunner
from intentional_py.reporting import BuildResult


def drain(events: queue.Queue, timeout: float = 30) -> list[tuple]:
    """Collect events until the job finishes."""
    collected = []
    while True:
        event = events.get(timeout=timeout)
        collected.append(event)
        if event[0] in ("done", "failed"):
            return collected


def make_nl_project(base: Path) -> Path:
    nl_dir = base / "Training Phrases" / "en" / "NL"
    nl_dir.mkdir(parents=True)
    (nl_dir / "BILLING.txt").write_text("pay my bill\n", encoding="utf-8")
    (nl_dir / "GREETING.txt").write_text("hello\n", encoding="utf-8")
    return base


def test_plain_text_strips_markup() -> None:
    assert actions.plain_text("[red]Bad[/red] [blue]x[/blue]") == "Bad x"
    assert actions.plain_text("row ['a', 'b']") == "row ['a', 'b']"


def test_project_dir_is_required(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigurationError):
        actions.project_dir("  ")
    with pytest.raises(exceptions.FileSystemError):
        actions.project_dir(str(tmp_path / "missing"))


def test_resolve_config_defaults_to_project(tmp_path: Path) -> None:
    # resolve() expands Windows short names and macOS /private links
    tmp_path = tmp_path.resolve()
    assert actions.resolve_config(tmp_path, "", "intents.cfg") == tmp_path / "intents.cfg"
    assert actions.resolve_config(tmp_path, "sub/a.cfg", "x") == tmp_path / "sub" / "a.cfg"
    other = tmp_path / "other.cfg"
    assert actions.resolve_config(tmp_path / "p", str(other), "x") == other


def test_build_nl_requires_vertical(tmp_path: Path) -> None:
    make_nl_project(tmp_path)
    reporter = GuiReporter(queue.Queue())
    with pytest.raises(exceptions.ConfigurationError):
        actions.build_nl(str(tmp_path), "", " ", "", False, False, reporter)


def test_extract_rejects_missing_file(tmp_path: Path) -> None:
    reporter = GuiReporter(queue.Queue())
    with pytest.raises(exceptions.FileSystemError):
        actions.extract(str(tmp_path), "nope.xlsx", "NL", "en", reporter)


def test_runner_builds_nl_and_reports_progress(tmp_path: Path) -> None:
    make_nl_project(tmp_path)
    runner = JobRunner()
    runner.start(
        lambda r: actions.build_nl(str(tmp_path), "", "RTL", "", False, False, r)
    )
    events = drain(runner.events)

    kinds = [event[0] for event in events]
    assert "progress_start" in kinds
    assert kinds.count("progress") == 2
    result = events[-1][1]
    assert isinstance(result, BuildResult)
    assert result.intents == 2
    assert (tmp_path / "intents_nl.cfg").exists()
    assert (tmp_path / "intents" / "RTL.Billing.json").exists()


def test_runner_reports_failures_as_plain_text(tmp_path: Path) -> None:
    runner = JobRunner()
    runner.start(lambda r: actions.build_dd(str(tmp_path), "", r))
    kind, text = drain(runner.events)[-1]
    assert kind == "failed"
    assert "Config file does not exist" in text
    assert "[red]" not in text


def test_confirm_waits_for_ui_answer() -> None:
    events: queue.Queue = queue.Queue()
    reporter = GuiReporter(events)
    answers = []
    worker = threading.Thread(target=lambda: answers.append(reporter.confirm("Continue")))
    worker.start()

    kind, question, answer, answered = events.get(timeout=5)
    assert (kind, question) == ("confirm", "Continue")
    assert worker.is_alive()
    answer["value"] = False
    answered.set()
    worker.join(timeout=5)
    assert answers == [False]


def test_gui_command_opens_project(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("customtkinter")
    from typer.testing import CliRunner

    from intentional_py.gui import app as gui_app
    from intentional_py.intentional import app

    opened = []
    monkeypatch.setattr(gui_app, "main", lambda project=None: opened.append(project))

    assert CliRunner().invoke(app, ["gui", "--project", str(tmp_path)]).exit_code == 0
    assert CliRunner().invoke(app, ["gui"]).exit_code == 0
    assert opened == [tmp_path.resolve(), None]


def test_gui_command_rejects_missing_project(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    result = CliRunner().invoke(app, ["gui", "-p", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "Project folder does not exist" in result.stdout
