"""GUI actions that do not depend on the widget toolkit.

Each action checks the form values, calls the core module, and returns its
result. The helpers at the bottom turn results into tiles, issues and tables,
sharing the result-interpretation logic in result_views.py with report.py so
the GUI and the CLI report can't drift apart.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from rich.errors import MarkupError
from rich.text import Text

from intentional_py import (
    build_intents,
    constants,
    design_doc,
    exceptions,
    result_views,
)
from intentional_py import extract as extracting
from intentional_py import validate as validating
from intentional_py.models import NamingRules, NlDefaults, ProjectLayout
from intentional_py.reporting import (
    BuildResult,
    CompareResult,
    DesignResult,
    ExtractResult,
    Level,
    Reporter,
    ValidateResult,
)
from intentional_py.result_views import Issue, Result, Table


def plain_text(text: str) -> str:
    """Strip Rich markup and convert emoji codes for display outside a terminal."""
    try:
        return Text.from_markup(text).plain
    except MarkupError:
        return text


def project_dir(text: str) -> Path:
    if not text.strip():
        raise exceptions.ConfigurationError("Choose a project folder.")
    path = Path(text.strip()).expanduser().resolve()
    if not path.is_dir():
        raise exceptions.FileSystemError(f"Project folder does not exist: {path}")
    return path


def resolve_config(project: Path, text: str, default: str) -> Path:
    """Blank uses the default file in the project folder; relative paths are relative to it."""
    path = Path(text.strip() or default).expanduser()
    return (path if path.is_absolute() else project / path).resolve()


def build_dd(
    project_text: str,
    config_text: str,
    reporter: Reporter,
    clean: bool = False,
    rules: NamingRules | None = None,
    layout: ProjectLayout | None = None,
) -> BuildResult:
    layout = layout or ProjectLayout()
    config = resolve_config(project_dir(project_text), config_text, layout.dd_config)
    return build_intents.intents(
        "DD", config, config.parent, reporter, clean, rules, layout
    )


def build_nl(
    project_text: str,
    config_text: str,
    vertical: str,
    context: str,
    lowercase: bool,
    reuse: bool,
    reporter: Reporter,
    clean: bool = False,
    rules: NamingRules | None = None,
    layout: ProjectLayout | None = None,
    nl_defaults: NlDefaults | None = None,
) -> BuildResult:
    layout = layout or ProjectLayout()
    nl_defaults = nl_defaults or NlDefaults()
    config = resolve_config(project_dir(project_text), config_text, layout.nl_config)
    if not reuse or not config.exists():
        if not vertical.strip():
            raise exceptions.ConfigurationError(
                "Enter a vertical prefix to build the NL config."
            )
        if not config.exists():
            reporter.message(
                "info", f"Existing config {config} not found, creating new config"
            )
        build_intents.nl_config(
            config,
            vertical.strip(),
            context.strip() or nl_defaults.context,
            lowercase,
            reporter,
            layout,
        )
    return build_intents.intents(
        "NL", config, config.parent, reporter, clean, rules, layout
    )


def compare(
    project_text: str,
    mode: str,
    config_text: str,
    export_text: str,
    reporter: Reporter,
    rules: NamingRules | None = None,
    layout: ProjectLayout | None = None,
) -> CompareResult:
    layout = layout or ProjectLayout()
    project = project_dir(project_text)
    mode = mode.upper()
    default = layout.nl_config if mode == "NL" else layout.dd_config
    config = resolve_config(project, config_text, default)
    if not export_text.strip():
        raise exceptions.ConfigurationError(
            "Choose an agent export (zip or folder) to compare with."
        )
    export = Path(export_text.strip()).expanduser()
    export = (export if export.is_absolute() else project / export).resolve()
    return build_intents.compare_build(
        mode, config, config.parent, export, reporter, rules, layout
    )


def design(
    project_text: str,
    xl_text: str,
    sheet: str,
    config_text: str,
    reporter: Reporter,
    rules: NamingRules | None = None,
    layout: ProjectLayout | None = None,
) -> DesignResult:
    layout = layout or ProjectLayout()
    project = project_dir(project_text)
    if not xl_text.strip():
        raise exceptions.ConfigurationError("Choose the Excel design document.")
    xl_file = Path(xl_text.strip()).expanduser()
    xl_file = (xl_file if xl_file.is_absolute() else project / xl_file).resolve()
    if not xl_file.is_file():
        raise exceptions.FileSystemError(f"Excel file does not exist: {xl_file}")
    config = resolve_config(project, config_text, layout.dd_config)
    return design_doc.config_from_design(
        xl_file, config, reporter, sheet.strip(), rules
    )


def extract(
    project_text: str,
    xl_text: str,
    mode: str,
    language: str,
    reporter: Reporter,
    layout: ProjectLayout | None = None,
) -> ExtractResult:
    project = project_dir(project_text)
    if not xl_text.strip():
        raise exceptions.ConfigurationError("Choose an Excel file to extract.")
    xl_file = Path(xl_text.strip()).expanduser()
    if not xl_file.is_absolute():
        xl_file = project / xl_file
    if not xl_file.is_file():
        raise exceptions.FileSystemError(f"Excel file does not exist: {xl_file}")
    mode = mode.upper()
    if mode not in constants.VALID_MODES:
        raise exceptions.ConfigurationError(f"Invalid mode: {mode}")
    language = language.lower()
    if language not in constants.VALID_LANGUAGES:
        raise exceptions.ConfigurationError(f"Invalid language: {language}")
    return extracting.excel_data(xl_file, mode, language, project, reporter, layout)


def validate(
    project_text: str,
    config_text: str,
    reporter: Reporter,
    rules: NamingRules | None = None,
    layout: ProjectLayout | None = None,
) -> ValidateResult:
    project = project_dir(project_text)
    if not config_text.strip():
        return validating.validate(Path(), project, reporter, rules, layout)
    config = resolve_config(project, config_text, "")
    if not config.is_file():
        raise exceptions.FileSystemError(f"Config file does not exist: {config}")
    return validating.validate(config, config.parent, reporter, rules, layout)


def issue(level: Level, text: str) -> Issue:
    """Split a message such as 'Warning: Row 3: ...' into its level, row and text."""
    text = re.sub(r"^(Error|Warning):\s*", "", plain_text(text).strip())
    match = re.match(r"Row (\d+):\s*(.*)", text, re.DOTALL)
    return (level, match[1], match[2]) if match else (level, "", text)


def tiles(result: Result) -> list[tuple[str, str]]:
    """Headline figures as (label, value)."""
    return result_views.summary_tiles(result)


def headline(title: str, result: Result, warnings: int) -> tuple[bool, str]:
    """Whether the job fully succeeded, and a one-line description of it."""
    if isinstance(result, ValidateResult):
        checks = result_views.checks(result)
        passed = sum(check.ok for check in checks)
        return passed == len(
            checks
        ), f"{title}: {passed} of {len(checks)} checks passed"
    if isinstance(result, DesignResult):
        if result.errors:
            return (
                False,
                f"{title}: {result.rows} rows written; fix the errors before building",
            )
        return True, f"{title}: {result.rows} rows written to {result.config.name}"
    text = f"{title} finished in {result.elapsed:.2f} s"
    if warnings:
        text += f" with {warnings} warning{'s' if warnings != 1 else ''}"
    return True, text


def result_issues(result: Result) -> list[Issue]:
    """Issues carried by the result itself (build issues arrive as messages instead)."""
    if isinstance(result, ValidateResult):
        return [
            issue("error" if detail.startswith("Error") else "warning", detail)
            for check in result.configs
            for detail in check.details
        ]
    if isinstance(result, DesignResult):
        return [issue("error", e) for e in result.errors] + [
            issue("warning", w) for w in result.warnings
        ]
    return result_views.result_issues(
        result,
        build_removed_message=(
            "No longer built, but still in the intents folder: {names}. "
            "Tick 'Clear the intents folder first' to remove them."
        ),
        extract_empty_sheet_message=(
            "Sheet {name} has no phrases; an empty text file was created."
        ),
    )


def detail_tables(result: Result) -> list[Table]:
    if isinstance(result, BuildResult):
        tables: list[Table] = []
        if result.changes and (result.changes.added or result.changes.changed):
            tables.append(
                (
                    "Changes since the previous build",
                    ["Change", "Intent", "Details"],
                    result_views.change_rows(result.changes),
                )
            )
        if result.backup:
            tables.append(
                (
                    "Output",
                    ["Item", "Location"],
                    [["Previous intents saved to", str(result.backup)]],
                )
            )
        if result.machine_learning_off:
            tables.append(
                (
                    "Intents with machine learning off",
                    ["Intent"],
                    [[name] for name in result.machine_learning_off],
                )
            )
        return tables
    if isinstance(result, CompareResult):
        tables = []
        if result.added or result.changed:
            tables.append(
                (
                    "Differences from the export",
                    ["Change", "Intent", "Details"],
                    result_views.change_rows(result),
                )
            )
        if result.removed:
            tables.append(
                (
                    "Only in the export (not built by this config)",
                    ["Intent"],
                    [[n] for n in result.removed],
                )
            )
        return tables
    if isinstance(result, DesignResult):
        rows = [["Config written", str(result.config)], ["Sheet read", result.sheet]]
        if result.backup:
            rows.append(["Previous config saved to", str(result.backup)])
        return [("Output", ["Item", "Location"], rows)]
    if isinstance(result, ExtractResult):
        locations = [["Phrases saved to", str(result.output_dir)]]
        if result.backup:
            locations.append(["Previous phrases saved to", str(result.backup)])
        tables = [("Output", ["Item", "Location"], locations)]
        if result.empty_sheets:
            tables.append(
                ("Empty sheets", ["Sheet"], [[n] for n in result.empty_sheets])
            )
        return tables
    rows = [
        ["✔" if check.ok else "✖", check.label] for check in result_views.checks(result)
    ]
    title = (
        "Checks (standard config files)" if result.used_standard_configs else "Checks"
    )
    return [(title, ["Result", "Check"], rows)]


def output_folder(result: Result) -> Path | None:
    return result_views.output_folder(result)


def open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", str(path)])
