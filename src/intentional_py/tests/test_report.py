import csv
from pathlib import Path

import pytest

from intentional_py import exceptions, report
from intentional_py.reporting import BuildResult, CompareResult, IntentChange


def sample_result(tmp_path: Path) -> BuildResult:
    return BuildResult(
        intents=2,
        phrases=5,
        entities=1,
        languages=["en", "es"],
        files=5,
        machine_learning_off=["A.Off"],
        output_dir=tmp_path / "intents",
        changes=CompareResult(
            source="the previous build",
            added=["A.New"],
            changed=[IntentChange("A.Changed", ["action: old -> new"])],
            removed=["A.Old"],
            unchanged=3,
        ),
    )


def test_markdown_report_contains_summary_issues_and_changes(tmp_path: Path) -> None:
    output = tmp_path / "build-report.md"

    report.write(
        output,
        "Build DD intents",
        sample_result(tmp_path),
        [("warning", "4", "Phrase file is empty")],
    )

    text = output.read_text(encoding="utf-8")
    assert "# Intentional Report" in text
    assert "**Job:** Build DD intents" in text
    assert "| Intents | 2 |" in text
    assert "| Warning | 4 | Phrase file is empty |" in text
    assert "A.New" in text
    assert "A.Changed" in text
    assert "A.Old" in text


def test_csv_report_contains_named_sections(tmp_path: Path) -> None:
    output = tmp_path / "build-report.csv"

    report.write(output, "Build DD intents", sample_result(tmp_path))

    with output.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert ["Intentional Report"] in rows
    assert ["Job", "Build DD intents"] in rows
    assert ["Summary"] in rows
    assert ["Intents", "2"] in rows
    assert ["Changes since the previous build"] in rows


def test_report_rejects_unknown_extension(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigurationError, match="Markdown.*CSV"):
        report.write(tmp_path / "report.txt", "Build", sample_result(tmp_path))


def test_cli_build_writes_optional_markdown_report(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    config = tmp_path / "intents.cfg"
    config.write_text("A.Pay,Ctx,en,pay,,,\n", encoding="utf-8")
    output = tmp_path / "completed-work.md"

    result = CliRunner().invoke(
        app, ["--config", str(config), "--report", str(output)]
    )

    assert result.exit_code == 0, result.stdout
    text = output.read_text(encoding="utf-8")
    assert "**Job:** Build DD intents" in text
    assert "phrase file" in text
    assert "A.Pay" in text


def test_cli_rejects_report_extension_before_building(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    config = tmp_path / "intents.cfg"
    config.write_text("A.Pay,Ctx,en,pay,,,\n", encoding="utf-8")

    result = CliRunner().invoke(
        app, ["--config", str(config), "--report", str(tmp_path / "report.txt")]
    )

    assert result.exit_code == 2
    assert "Markdown (.md) or CSV (.csv)" in result.stderr
    assert not (tmp_path / "intents").exists()
