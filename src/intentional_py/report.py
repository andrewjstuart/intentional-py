"""Write completed job results as Markdown or CSV reports."""

import csv
import datetime
from pathlib import Path

from intentional_py import exceptions, result_views, utils
from intentional_py.reporting import (
    BuildResult,
    CompareResult,
    DesignResult,
    PackageResult,
    ValidateResult,
)
from intentional_py.result_views import Issue, Result, Table


def _summary(result: Result) -> list[tuple[str, str]]:
    return result_views.summary_rows(result)


def _changes(result: CompareResult | PackageResult, title: str) -> Table | None:
    """Added and changed intents, matching the table shown by both front ends."""
    rows = result_views.change_rows(result)
    return (title, ["Change", "Intent", "Details"], rows) if rows else None


def _removed_table(names: list[str], title: str) -> Table | None:
    """Intents no longer produced, kept separate since they need a different action (delete by hand)."""
    return (title, ["Intent"], [[name] for name in names]) if names else None


def _package_tables(package: PackageResult) -> list[Table]:
    """Shared by BuildResult (when it has a `package`, from `intents(export=...)`) and
    a standalone PackageResult - everything except the Output table, since that's
    folded into the build's own Output table in the BuildResult case."""
    tables: list[Table] = []
    changes = _changes(package, f"Differences from {package.source}")
    if changes:
        tables.append(changes)
    removed = _removed_table(
        package.removed, "Removed from the package zip (marked with '-'/'--')"
    )
    if removed:
        tables.append(removed)
    manual = _removed_table(
        package.needs_manual_removal,
        "Marked for removal, but 'import' can't delete - remove by hand",
    )
    if manual:
        tables.append(manual)
    unmarked = _removed_table(
        package.unmarked, f"Only in {package.source} (not built by this config)"
    )
    if unmarked:
        tables.append(unmarked)
    return tables


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
        if result.package:
            tables.extend(_package_tables(result.package))
            output.append(["Package style", result.package.style])
            if result.package.output:
                output.append(["Updated export written to", str(result.package.output)])
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
    if isinstance(result, PackageResult):
        tables = _package_tables(result)
        output = [["Package style", result.style]]
        if result.output:
            output.append(["Updated export written to", str(result.output)])
        tables.append(("Output", ["Item", "Location"], output))
        return tables
    if isinstance(result, ValidateResult):
        checks = result_views.checks(result)
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
    return result_views.result_issues(result)


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
