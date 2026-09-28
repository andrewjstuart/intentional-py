"""GUI actions that do not depend on the widget toolkit.

Each action checks the form values, calls the core module, and returns its
result. The helpers at the bottom turn results into tiles, issues and tables.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from rich.errors import MarkupError
from rich.text import Text

from intentional_py import build_intents, constants, exceptions
from intentional_py import extract as extracting
from intentional_py import validate as validating
from intentional_py.reporting import (
    BuildResult,
    ExtractResult,
    Level,
    Reporter,
    ValidateResult,
)

Result = BuildResult | ExtractResult | ValidateResult
Issue = tuple[Level, str, str]  # level, config row (or ""), message
Table = tuple[str, list[str], list[list[str]]]  # title, columns, rows


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


def build_dd(project_text: str, config_text: str, reporter: Reporter) -> BuildResult:
    config = resolve_config(
        project_dir(project_text), config_text, constants.DEFAULT_DD_CONFIG
    )
    return build_intents.intents("DD", config, config.parent, reporter)


def build_nl(
    project_text: str,
    config_text: str,
    vertical: str,
    context: str,
    lowercase: bool,
    reuse: bool,
    reporter: Reporter,
) -> BuildResult:
    config = resolve_config(
        project_dir(project_text), config_text, constants.DEFAULT_NL_CONFIG
    )
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
            context.strip() or constants.DEFAULT_NL_CONTEXT,
            lowercase,
            reporter,
        )
    return build_intents.intents("NL", config, config.parent, reporter)


def extract(
    project_text: str, xl_text: str, mode: str, language: str, reporter: Reporter
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
    return extracting.excel_data(xl_file, mode, language, project, reporter)


def validate(project_text: str, config_text: str, reporter: Reporter) -> ValidateResult:
    project = project_dir(project_text)
    if not config_text.strip():
        return validating.validate(Path(), project, reporter)
    config = resolve_config(project, config_text, "")
    if not config.is_file():
        raise exceptions.FileSystemError(f"Config file does not exist: {config}")
    return validating.validate(config, config.parent, reporter)


def issue(level: Level, text: str) -> Issue:
    """Split a message such as 'Warning: Row 3: ...' into its level, row and text."""
    text = re.sub(r"^(Error|Warning):\s*", "", plain_text(text).strip())
    match = re.match(r"Row (\d+):\s*(.*)", text, re.DOTALL)
    return (level, match[1], match[2]) if match else (level, "", text)


def _checks(result: ValidateResult) -> list:
    return result.directories + result.config_files + result.configs


def tiles(result: Result) -> list[tuple[str, str]]:
    """Headline figures as (label, value)."""
    if isinstance(result, BuildResult):
        figures = [
            ("Intents", str(result.intents)),
            ("Phrases", str(result.phrases)),
            ("Entities", str(result.entities)),
            ("Files", str(result.files)),
            ("Languages", ", ".join(result.languages) or "-"),
        ]
        if result.nomatch:
            figures.append(("NoMatch", str(result.nomatch)))
        return figures
    if isinstance(result, ExtractResult):
        return [
            ("Files", str(result.files)),
            ("Phrases", str(result.phrases)),
            ("Empty sheets", str(len(result.empty_sheets))),
        ]
    checks = _checks(result)
    failed = sum(not check.ok for check in checks)
    return [
        ("Checks", str(len(checks))),
        ("Passed", str(len(checks) - failed)),
        ("Failed", str(failed)),
    ]


def headline(title: str, result: Result, warnings: int) -> tuple[bool, str]:
    """Whether the job fully succeeded, and a one-line description of it."""
    if isinstance(result, ValidateResult):
        checks = _checks(result)
        passed = sum(check.ok for check in checks)
        return passed == len(checks), f"{title}: {passed} of {len(checks)} checks passed"
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
    if isinstance(result, ExtractResult):
        return [
            ("warning", "", f"Sheet {name} has no phrases; an empty text file was created.")
            for name in result.empty_sheets
        ]
    return []


def detail_tables(result: Result) -> list[Table]:
    if isinstance(result, BuildResult):
        if not result.ml_disabled:
            return []
        return [("Intents with ML disabled", ["Intent"], [[n] for n in result.ml_disabled])]
    if isinstance(result, ExtractResult):
        locations = [["Phrases saved to", str(result.output_dir)]]
        if result.backup:
            locations.append(["Previous phrases saved to", str(result.backup)])
        tables = [("Output", ["Item", "Location"], locations)]
        if result.empty_sheets:
            tables.append(("Empty sheets", ["Sheet"], [[n] for n in result.empty_sheets]))
        return tables
    rows = [["✔" if check.ok else "✖", check.label] for check in _checks(result)]
    title = "Checks (standard config files)" if result.used_standard_configs else "Checks"
    return [(title, ["Result", "Check"], rows)]


def output_folder(result: Result) -> Path | None:
    if isinstance(result, ValidateResult):
        return None
    return result.output_dir


def open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", str(path)])
