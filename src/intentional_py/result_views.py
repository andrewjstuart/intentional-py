"""Shared result-to-view helpers used by GUI actions and report writing.

These functions keep the result interpretation logic in one place so the GUI and
report output stay aligned when behavior changes.
"""

from pathlib import Path

from intentional_py.reporting import (
    BuildResult,
    Check,
    CompareResult,
    DesignResult,
    ExtractResult,
    Level,
    PackageResult,
    ValidateResult,
)

# Canonical result/issue/table shapes; gui/actions.py and report.py import these
# instead of redefining them, so the front ends can't drift out of sync.
Result = (
    BuildResult
    | ExtractResult
    | ValidateResult
    | CompareResult
    | DesignResult
    | PackageResult
)
Issue = tuple[Level, str, str]
Table = tuple[str, list[str], list[list[str]]]


def checks(result: ValidateResult) -> list[Check]:
    return result.directories + result.config_files + result.configs


def summary_rows(result: Result) -> list[tuple[str, str]]:
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
        if result.removed:
            rows.append(("Removed", str(len(result.removed))))
        if result.package:
            rows.append(("Package style", result.package.style))
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
    if isinstance(result, PackageResult):
        rows = [
            ("Style", result.style),
            ("Added", str(len(result.added))),
            ("Changed", str(len(result.changed))),
            ("Unchanged", str(result.unchanged)),
        ]
        if result.removed:
            rows.append(("Removed", str(len(result.removed))))
        if result.needs_manual_removal:
            rows.append(("Needs manual removal", str(len(result.needs_manual_removal))))
        if result.unmarked:
            rows.append(("Only in export", str(len(result.unmarked))))
        return rows
    if isinstance(result, DesignResult):
        return [
            ("Rows", str(result.rows)),
            ("Errors", str(len(result.errors))),
            ("Warnings", str(len(result.warnings))),
        ]
    all_checks = checks(result)
    passed = sum(check.ok for check in all_checks)
    return [
        ("Checks", str(len(all_checks))),
        ("Passed", str(passed)),
        ("Failed", str(len(all_checks) - passed)),
    ]


def summary_tiles(result: Result) -> list[tuple[str, str]]:
    """GUI tile order, preserving current UI layout."""
    rows = summary_rows(result)
    if isinstance(result, BuildResult):
        by_name = dict(rows)
        ordered = [
            "Intents",
            "Phrases",
            "Entities",
            "Files",
            "Languages",
            "NoMatch",
            "Removed",
            "Package style",
        ]
        return [(name, by_name[name]) for name in ordered if name in by_name]
    return rows


def change_rows(result: CompareResult | PackageResult) -> list[list[str]]:
    rows = [["Added", name, ""] for name in result.added]
    rows.extend(
        ["Changed", change.name, "; ".join(change.details)] for change in result.changed
    )
    return rows


def _package_issues(package: PackageResult) -> list[Issue]:
    """Shared by BuildResult (when it has a `package`, from `intents(export=...)`) and
    a standalone PackageResult, so the wording can't drift between the two."""
    issues: list[Issue] = []
    if package.removed:
        issues.append(
            (
                "warning",
                "",
                f"Removed from the package zip (marked with '-'/'--'): {', '.join(package.removed)}.",
            )
        )
    if package.needs_manual_removal:
        issues.append(
            (
                "warning",
                "",
                "Marked for removal, but 'import' can't delete from the agent - "
                "remove by hand: " + ", ".join(package.needs_manual_removal) + ".",
            )
        )
    if package.unmarked:
        issues.append(
            (
                "warning",
                "",
                f"Only in {package.source} (not built by this config, left as-is): "
                + ", ".join(package.unmarked)
                + ".",
            )
        )
    return issues


def result_issues(
    result: Result,
    *,
    build_removed_message: str = "No longer built, but still in the intents folder: {names}.",
    extract_empty_sheet_message: str = "Sheet {name} has no phrases; an empty file was created.",
) -> list[Issue]:
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
            ("warning", "", extract_empty_sheet_message.format(name=name))
            for name in result.empty_sheets
        ]
    if isinstance(result, BuildResult):
        issues: list[Issue] = []
        if result.removed:
            issues.append(
                (
                    "warning",
                    "",
                    f"Removed (marked with '-'/'--'): {', '.join(result.removed)}.",
                )
            )
        if result.changes and result.changes.removed and not result.backup:
            issues.append(
                (
                    "warning",
                    "",
                    build_removed_message.format(
                        names=", ".join(result.changes.removed)
                    ),
                )
            )
        if result.package:
            issues.extend(_package_issues(result.package))
        return issues
    if isinstance(result, PackageResult):
        return _package_issues(result)
    return []


def output_folder(result: Result) -> Path | None:
    if isinstance(result, ValidateResult | CompareResult):
        return None
    if isinstance(result, PackageResult):
        return result.output.parent if result.output else None
    if isinstance(result, DesignResult):
        return result.config.parent
    return result.output_dir
