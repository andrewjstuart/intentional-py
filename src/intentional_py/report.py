"""Write completed job results as Markdown or CSV reports."""

import csv
import datetime
from pathlib import Path

from intentional_py import exceptions, utils
from intentional_py.reporting import (
    BuildResult,
    CompareResult,
    DesignResult,
    ExtractResult,
    Level,
    ValidateResult,
)

Result = BuildResult | ExtractResult | ValidateResult | CompareResult | DesignResult
Issue = tuple[Level, str, str]
Table = tuple[str, list[str], list[list[str]]]


def _summary(result: Result) -> list[tuple[str, str]]:
    if isinstance(result, BuildResult):
        rows = [
            ("Intents", str(result.intents)),
            ("Phrases", str(result.phrases)),
            ("Entities", str(result.entities)),
            ("Languages", ", ".join(result.languages) or "-"),
            ("Files", str(result.files)),
        ]
        if result.nomatch:
            rows.append(("NoMatch", str(result.nomatch)))
        return rows
    if isinstance(result, ExtractResult):
        return [
            ("Files", str(result.files)),
            ("Phrases", str(result.phrases)),
            ("Empty sheets", str(len(result.empty_sheets))),
        ]
    if isinstance(result, CompareResult):
        return [
            ("Added", str(len(result.added))),
            ("Changed", str(len(result.changed))),
            ("Unchanged", str(result.unchanged)),
            ("Only in export", str(len(result.removed))),
        ]
    if isinstance(result, DesignResult):
        return [
            ("Rows", str(result.rows)),
            ("Errors", str(len(result.errors))),
            ("Warnings", str(len(result.warnings))),
        ]
    checks = result.directories + result.config_files + result.configs
    passed = sum(check.ok for check in checks)
    return [
        ("Checks", str(len(checks))),
        ("Passed", str(passed)),
        ("Failed", str(len(checks) - passed)),
    ]


def _changes(result: CompareResult, title: str) -> Table | None:
    """Added and changed intents, matching the table shown by both front ends."""
    rows = [["Added", name, ""] for name in result.added]
    rows.extend(
        ["Changed", change.name, "; ".join(change.details)] for change in result.changed
    )
    return (title, ["Change", "Intent", "Details"], rows) if rows else None


def _removed_table(names: list[str], title: str) -> Table | None:
    """Intents no longer produced, kept separate since they need a different action (delete by hand)."""
    return (title, ["Intent"], [[name] for name in names]) if names else None


def _tables(result: Result) -> list[Table]:
    if isinstance(result, BuildResult):
        tables: list[Table] = []
        if result.intent_names:
            tables.append(
                ("Built intents", ["Intent"], [[name] for name in result.intent_names])
            )
        if result.changes:
            changes = _changes(result.changes, "Changes since the previous build")
            if changes:
                tables.append(changes)
            removed = _removed_table(
                result.changes.removed,
                "No longer built, but still in the intents folder",
            )
            if removed:
                tables.append(removed)
        if result.machine_learning_off:
            tables.append(
                (
                    "Intents with machine learning off",
                    ["Intent"],
                    [[name] for name in result.machine_learning_off],
                )
            )
        output = []
        if result.output_dir:
            output.append(["Intents written to", str(result.output_dir)])
        if result.backup:
            output.append(["Previous intents saved to", str(result.backup)])
        if output:
            tables.append(("Output", ["Item", "Location"], output))
        return tables
    if isinstance(result, CompareResult):
        tables = []
        changes = _changes(result, f"Differences from {result.source}")
        if changes:
            tables.append(changes)
        removed = _removed_table(
            result.removed, f"Only in {result.source} (not built by this config)"
        )
        if removed:
            tables.append(removed)
        return tables
    if isinstance(result, ValidateResult):
        checks = result.directories + result.config_files + result.configs
        return [
            (
                "Checks",
                ["Result", "Check"],
                [["Pass" if check.ok else "Fail", check.label] for check in checks],
            )
        ]
    if isinstance(result, DesignResult):
        rows = [["Config written", str(result.config)], ["Sheet read", result.sheet]]
        if result.backup:
            rows.append(["Previous config saved to", str(result.backup)])
        return [("Output", ["Item", "Location"], rows)]
    rows = [["Phrases saved to", str(result.output_dir)]]
    if result.backup:
        rows.append(["Previous phrases saved to", str(result.backup)])
    tables = [("Output", ["Item", "Location"], rows)]
    if result.empty_sheets:
        tables.append(
            ("Empty sheets", ["Sheet"], [[name] for name in result.empty_sheets])
        )
    return tables


def _result_issues(result: Result) -> list[Issue]:
    if isinstance(result, ValidateResult):
        return [
            (
                "error" if detail.startswith("Error") else "warning",
                "",
                detail.removeprefix("Error: ").removeprefix("Warning: "),
            )
            for check in result.configs
            for detail in check.details
        ]
    if isinstance(result, DesignResult):
        return [("error", "", text) for text in result.errors] + [
            ("warning", "", text) for text in result.warnings
        ]
    if isinstance(result, ExtractResult):
        return [
            ("warning", "", f"Sheet {name} has no phrases; an empty file was created.")
            for name in result.empty_sheets
        ]
    if (
        isinstance(result, BuildResult)
        and result.changes
        and result.changes.removed
        and not result.backup
    ):
        return [
            (
                "warning",
                "",
                "No longer built, but still in the intents folder: "
                + ", ".join(result.changes.removed),
            )
        ]
    return []


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


# leading characters Excel/Sheets can interpret as the start of a formula
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _csv_cell(value: object) -> str:
    """A cell safe from CSV/formula injection when the report is opened in a spreadsheet."""
    text = str(value)
    return f"'{text}" if text.startswith(_FORMULA_TRIGGERS) else text


def _csv_row(row: list) -> list[str]:
    return [_csv_cell(cell) for cell in row]


def _markdown(
    title: str,
    generated: str,
    summary: list[tuple[str, str]],
    issues: list[Issue],
    tables: list[Table],
) -> str:
    lines = [
        "# Intentional Report",
        "",
        f"**Job:** {_escape(title)}  ",
        f"**Generated:** {generated}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        *(f"| {_escape(label)} | {_escape(value)} |" for label, value in summary),
    ]
    if issues:
        lines.extend(
            ["", "## Issues", "", "| Level | Row | Message |", "|---|---|---|"]
        )
        lines.extend(
            f"| {level.title()} | {_escape(row)} | {_escape(message)} |"
            for level, row, message in issues
        )
    else:
        lines.extend(["", "## Issues", "", "No errors or warnings."])
    for table_title, columns, rows in tables:
        lines.extend(
            [
                "",
                f"## {_escape(table_title)}",
                "",
                "| " + " | ".join(_escape(column) for column in columns) + " |",
                "|" + "|".join("---" for _ in columns) + "|",
            ]
        )
        lines.extend(
            "| " + " | ".join(_escape(cell) for cell in row) + " |" for row in rows
        )
    return "\n".join(lines) + "\n"


def _write_csv(
    path: Path,
    title: str,
    generated: str,
    summary: list[tuple[str, str]],
    issues: list[Issue],
    tables: list[Table],
) -> None:
    with utils.file_errors(path), path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Intentional Report"])
        writer.writerow(_csv_row(["Job", title]))
        writer.writerow(["Generated", generated])
        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerows(_csv_row(row) for row in summary)
        writer.writerow([])
        writer.writerow(["Issues"])
        writer.writerow(["Level", "Row", "Message"])
        writer.writerows(_csv_row(row) for row in issues)
        for table_title, columns, rows in tables:
            writer.writerow([])
            writer.writerow(_csv_row([table_title]))
            writer.writerow(_csv_row(columns))
            writer.writerows(_csv_row(row) for row in rows)


def write(
    path: Path,
    title: str,
    result: Result,
    issues: list[Issue] | None = None,
    tables: list[Table] | None = None,
) -> Path:
    """Write a completed job report; the .md or .csv suffix selects its format."""
    path = Path(path)
    suffix = path.suffix.casefold()
    if suffix not in {".md", ".markdown", ".csv"}:
        raise exceptions.ConfigurationError(
            "Report file must use a Markdown (.md) or CSV (.csv) extension."
        )
    all_issues = list(issues or [])
    for item in _result_issues(result):
        if item not in all_issues:
            all_issues.append(item)
    report_tables = list(tables) if tables is not None else _tables(result)
    generated = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if suffix == ".csv":
        _write_csv(path, title, generated, _summary(result), all_issues, report_tables)
    else:
        content = _markdown(
            title, generated, _summary(result), all_issues, report_tables
        )
        with utils.file_errors(path):
            path.write_text(content, encoding="utf-8")
    return path
