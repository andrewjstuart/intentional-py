import queue
import threading
import zipfile
from pathlib import Path

import pytest

from intentional_py import exceptions
from intentional_py.gui import actions
from intentional_py.gui.worker import GuiReporter, JobRunner
from intentional_py.models import LanguageSettings
from intentional_py.reporting import (
    BuildResult,
    Check,
    ExtractResult,
    IntentChange,
    PackageResult,
    ValidateResult,
)
from intentional_py.tests.conftest import dd_project


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


def test_help_has_a_section_for_each_tab() -> None:
    from intentional_py.gui import help_text

    assert list(help_text.SECTIONS) == [
        "Getting started",
        "Build DD",
        "Build NL",
        "Validate",
        "Extract",
        "Create Config",
        "Compare",
        "Merge",
        "Package",
        "Settings",
    ]


def test_issue_splits_level_prefix_and_row() -> None:
    assert actions.issue(
        "warning", "[yellow]Warning:[/yellow] Row 3: context 'a.b' contains '.'."
    ) == (
        "warning",
        "3",
        "context 'a.b' contains '.'.",
    )
    assert actions.issue("error", "Error: The config file does not contain data.") == (
        "error",
        "",
        "The config file does not contain data.",
    )


def test_synthesized_english_and_duplicate_row_warnings_link_to_a_row() -> None:
    # config editor and results panels colour/highlight a row by parsing 'Row N: ...' from the warning
    assert (
        actions.issue(
            "warning",
            "Row 1: intent 'A.Pay' has no English ('en') row; an English row will be synthesized from this row ('es').",
        )[1]
        == "1"
    )
    assert (
        actions.issue(
            "warning",
            "Row 2: intent 'A.Pay' also has language 'en' in row(s) 1; its phrases will be used, "
            "but row 1's context, action, priority, entities and machine learning are kept.",
        )[1]
        == "2"
    )


def test_build_display(tmp_path: Path) -> None:
    result = BuildResult(
        intents=2,
        phrases=5,
        files=4,
        languages=["en"],
        elapsed=0.5,
        output_dir=tmp_path,
    )
    assert actions.tiles(result)[:2] == [("Intents", "2"), ("Phrases", "5")]
    assert actions.headline("Build DD intents", result, 1) == (
        True,
        "Build DD intents finished in 0.50 s with 1 warning",
    )
    assert actions.detail_tables(result) == []
    assert actions.output_folder(result) == tmp_path


def test_build_display_with_a_package(tmp_path: Path) -> None:
    # intents(export=...) builds and packages in one step; the package nests under
    # the same BuildResult rather than needing a separate Package run
    package_output = tmp_path / "agent_restore_2026.zip"
    result = BuildResult(
        intents=1,
        phrases=1,
        files=2,
        languages=["en"],
        elapsed=0.5,
        output_dir=tmp_path,
        package=PackageResult(
            source=tmp_path / "agent.zip",
            style="restore",
            output=package_output,
            added=["A.New"],
            unmarked=["A.Unrelated"],
        ),
    )
    assert ("Package style", "restore") in actions.tiles(result)
    titles = [title for title, _, _ in actions.detail_tables(result)]
    assert "Differences from the export" in titles
    assert "Only in the export (not built by this config)" in titles
    assert titles[-1] == "Output"
    issues = actions.result_issues(result)
    assert any("not built by this config" in message for _, _, message in issues)
    # the main build's own output folder, not the package's, is what gets an Open button
    assert actions.output_folder(result) == tmp_path


def test_extract_display(tmp_path: Path) -> None:
    backup = tmp_path / "NL_2026.zip"
    result = ExtractResult(
        output_dir=tmp_path, files=2, phrases=1, empty_sheets=["EMPTY"], backup=backup
    )
    assert actions.result_issues(result) == [
        ("warning", "", "Sheet EMPTY has no phrases; an empty text file was created.")
    ]
    (_, _, locations), (_, _, sheets) = actions.detail_tables(result)
    assert locations[1] == ["Previous phrases saved to", str(backup)]
    assert sheets == [["EMPTY"]]


def test_package_display(tmp_path: Path) -> None:
    output = tmp_path / "agent_restore_2026.zip"
    result = PackageResult(
        source=tmp_path / "agent.zip",
        style="import",
        output=output,
        added=["A.New"],
        changed=[IntentChange("A.Changed", ["action: old -> new"])],
        removed=["A.Old.json"],
        needs_manual_removal=["A.Stuck"],
        unmarked=["A.Unrelated"],
    )
    assert actions.tiles(result)[0] == ("Style", "import")
    tables = actions.detail_tables(result)
    titles = [title for title, _, _ in tables]
    assert titles == [
        "Differences from the export",
        "Removed from the package zip (marked with '-'/'--')",
        "Marked for removal, but 'import' can't delete - remove by hand",
        "Only in the export (not built by this config)",
        "Output",
    ]
    assert actions.output_folder(result) == tmp_path


def test_package_rejects_an_export_folder(tmp_path: Path) -> None:
    folder = tmp_path / "unzipped_export"
    folder.mkdir()
    with pytest.raises(exceptions.ConfigurationError):
        actions.package(
            str(tmp_path), str(folder), "restore", GuiReporter(queue.Queue())
        )


def test_validate_display() -> None:
    result = ValidateResult(
        directories=[Check("Training Phrases path", True)],
        configs=[
            Check(
                "Validating intents.cfg",
                False,
                [
                    "Error: Row 2: intent name 'A-B' cannot contain '-'.",
                    "Warning: Row 4: context 'a.b' contains '.'.",
                ],
            )
        ],
    )
    assert actions.headline("Validate", result, 1) == (
        False,
        "Validate: 1 of 2 checks passed",
    )
    assert actions.result_issues(result) == [
        ("error", "2", "intent name 'A-B' cannot contain '-'."),
        ("warning", "4", "context 'a.b' contains '.'."),
    ]
    assert actions.detail_tables(result)[0][2] == [
        ["✔", "Training Phrases path"],
        ["✖", "Validating intents.cfg"],
    ]
    assert actions.output_folder(result) is None


def test_project_dir_is_required(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigurationError):
        actions.project_dir("  ")
    with pytest.raises(exceptions.FileSystemError):
        actions.project_dir(str(tmp_path / "missing"))


def test_resolve_config_defaults_to_project(tmp_path: Path) -> None:
    # resolve() expands Windows short names and macOS /private links
    tmp_path = tmp_path.resolve()
    assert (
        actions.resolve_config(tmp_path, "", "intents.cfg") == tmp_path / "intents.cfg"
    )
    assert (
        actions.resolve_config(tmp_path, "sub/a.cfg", "x") == tmp_path / "sub" / "a.cfg"
    )
    other = tmp_path / "other.cfg"
    assert actions.resolve_config(tmp_path / "p", str(other), "x") == other


def test_build_nl_requires_vertical(tmp_path: Path) -> None:
    make_nl_project(tmp_path)
    reporter = GuiReporter(queue.Queue())
    with pytest.raises(exceptions.ConfigurationError):
        actions.build_nl(str(tmp_path), "", " ", "", False, False, reporter)


def test_build_dd_merges_into_an_export_when_given(tmp_path: Path) -> None:
    dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    export = tmp_path / "agent.zip"
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr("agent.json", "{}")
        archive.writestr("intents/Old.json", '{"name": "Old"}')
    reporter = GuiReporter(queue.Queue())

    result = actions.build_dd(str(tmp_path), "", reporter, export_text=str(export))

    # the intents folder is still written the same way as without an export
    assert (tmp_path / "intents" / "A.Pay.json").exists()
    assert result.package is not None
    assert result.package.style == "restore"
    assert result.package.added == ["A.Pay"]


def test_build_dd_without_an_export_leaves_package_none(tmp_path: Path) -> None:
    dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    reporter = GuiReporter(queue.Queue())

    result = actions.build_dd(str(tmp_path), "", reporter)

    assert result.package is None


def test_build_dd_rejects_an_export_folder(tmp_path: Path) -> None:
    dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    folder = tmp_path / "unzipped_export"
    folder.mkdir()
    reporter = GuiReporter(queue.Queue())

    with pytest.raises(exceptions.ConfigurationError):
        actions.build_dd(str(tmp_path), "", reporter, export_text=str(folder))


def test_build_dd_rejects_an_invalid_style(tmp_path: Path) -> None:
    dd_project(tmp_path, ["A.Pay,Ctx,en,pay,,,"], {"pay": "pay my bill"})
    export = tmp_path / "agent.zip"
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr("agent.json", "{}")
    reporter = GuiReporter(queue.Queue())

    with pytest.raises(exceptions.ConfigurationError):
        actions.build_dd(
            str(tmp_path), "", reporter, export_text=str(export), style="bogus"
        )


def test_extract_rejects_missing_file(tmp_path: Path) -> None:
    reporter = GuiReporter(queue.Queue())
    with pytest.raises(exceptions.FileSystemError):
        actions.extract(str(tmp_path), "nope.xlsx", "NL", "en", reporter)


def test_extract_rejects_a_language_outside_the_custom_set(tmp_path: Path) -> None:
    (tmp_path / "phrases.xlsx").touch()
    languages = LanguageSettings(languages={"en": "English", "de": "German"})
    reporter = GuiReporter(queue.Queue())
    with pytest.raises(exceptions.ConfigurationError):
        actions.extract(
            str(tmp_path), "phrases.xlsx", "NL", "fr", reporter, languages=languages
        )


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
    worker = threading.Thread(
        target=lambda: answers.append(
            reporter.confirm("Continue", ["hello", "pay my bill"])
        )
    )
    worker.start()

    kind, question, details, answer, answered = events.get(timeout=5)
    assert (kind, question, details) == (
        "confirm",
        "Continue",
        ["hello", "pay my bill"],
    )
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
    monkeypatch.chdir(tmp_path)

    assert CliRunner().invoke(app, ["gui", "--project", str(tmp_path)]).exit_code == 0
    assert CliRunner().invoke(app, ["gui"]).exit_code == 0
    # with no --project, it's the current directory, not whatever the GUI last
    # had open - the user can still change it from inside the GUI
    assert opened == [tmp_path.resolve(), tmp_path.resolve()]


def test_gui_command_rejects_missing_project(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    result = CliRunner().invoke(app, ["gui", "-p", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "Project folder does not exist" in result.stdout


def test_gui_command_reports_no_display_cleanly(monkeypatch) -> None:
    """A TclError (e.g. no $DISPLAY on a headless machine) shouldn't be a raw traceback."""
    pytest.importorskip("customtkinter")
    import tkinter

    from typer.testing import CliRunner

    from intentional_py.gui import app as gui_app
    from intentional_py.intentional import app

    def fail(project=None) -> None:
        raise tkinter.TclError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(gui_app, "main", fail)

    result = CliRunner().invoke(app, ["gui"])

    assert result.exit_code == 1
    assert not isinstance(result.exception, tkinter.TclError)  # caught, not raw
    assert "Could not open the GUI" in result.stdout
    assert "no display" in result.stdout.lower()
