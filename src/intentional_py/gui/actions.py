"""GUI actions that do not depend on the widget toolkit.

Each action checks the form values, calls the core module, and returns its
result. The helpers at the bottom turn results into display rows and log lines.
"""

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


def summary(result: Result) -> list[tuple[str, str]]:
    """Headline figures shown above the log."""
    if isinstance(result, BuildResult):
        rows = [
            ("Time", f"{result.elapsed:.3f} s"),
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
            ("Time", f"{result.elapsed:.3f} s"),
            ("Files", str(result.files)),
            ("Phrases", str(result.phrases)),
        ]
    checks = result.directories + result.config_files + result.configs
    failed = sum(not check.ok for check in checks)
    return [
        ("Checks", str(len(checks))),
        ("Passed", str(len(checks) - failed)),
        ("Failed", str(failed)),
    ]


def details(result: Result) -> list[tuple[Level, str]]:
    """Log lines describing a finished job."""
    lines: list[tuple[Level, str]] = []
    if isinstance(result, BuildResult):
        if result.ml_disabled:
            lines.append(("info", "Intents with ML disabled:"))
            lines.extend(("info", f"    {name}") for name in result.ml_disabled)
    elif isinstance(result, ExtractResult):
        lines.append(("info", f"Phrases saved to {result.output_dir}"))
        if result.backup:
            lines.append(("info", f"Previous phrases saved to {result.backup}"))
        lines.extend(
            ("warning", f"Sheet {name} has no phrases; an empty text file was created.")
            for name in result.empty_sheets
        )
    else:
        if result.used_standard_configs:
            lines.append(("info", "Using standard config files"))
        for check in result.directories + result.config_files + result.configs:
            lines.append(
                ("info" if check.ok else "error", f"{'✔' if check.ok else '✖'} {check.label}")
            )
            level = "error" if not check.ok else "warning"
            lines.extend((level, f"    {plain_text(d)}") for d in check.details)
    return lines
