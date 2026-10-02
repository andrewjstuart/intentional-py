"""Browser-facing actions: unpack an uploaded project zip, run a task against
it with the unmodified core, and hand back a JSON-serializable result (plus,
for tasks that produce files, a base64-encoded zip of just what changed).

Mirrors gui/actions.py's role for the desktop GUI, but zip-in/JSON-out instead
of a picked folder, since a browser tab has no direct access to the user's
filesystem. The functions here don't touch Pyodide-specific APIs, so they can
(and do) run under plain CPython in the test suite too. JSON summaries reuse
result_views.py, the same shaping report.py and gui/actions.py already use, so
all three front ends describe a result the same way.
"""

from __future__ import annotations

import base64
import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from intentional_py import build_intents, design_doc, exceptions, result_views
from intentional_py import extract as extracting
from intentional_py import validate as validating
from intentional_py.models import NamingRules, NlDefaults, ProjectLayout
from intentional_py.web.reporter import WebReporter


def _extract_zip(zip_bytes: bytes) -> Path:
    work_dir = Path(tempfile.mkdtemp(prefix="intentional_web_"))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        archive.extractall(work_dir)
    return work_dir


def _zip_dir(directory: Path) -> bytes:
    """Zip a directory's contents at the archive root, for the browser to download."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in directory.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(directory))
    return buffer.getvalue()


def _zip_file(path: Path) -> bytes:
    """Zip a single file at the archive root (e.g. a config file Design doc wrote)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(path, arcname=path.name)
    return buffer.getvalue()


def _respond(payload: dict, output_zip: bytes | None = None) -> str:
    if output_zip is not None:
        payload["output_zip_base64"] = base64.b64encode(output_zip).decode("ascii")
    return json.dumps(payload)


def validate_project(zip_bytes: bytes, config_name: str = "") -> str:
    """Validate an uploaded project zip; returns the result as a JSON string.

    config_name (str): name of the config file to validate, relative to the zip's
        root; blank checks the standard config files, same as the CLI/GUI default.
    """
    work_dir = _extract_zip(zip_bytes)
    try:
        reporter = WebReporter()
        config = Path(work_dir, config_name) if config_name else Path()
        result = validating.validate(
            config, work_dir, reporter, NamingRules(), ProjectLayout()
        )
        payload = {
            "messages": reporter.messages,
            "directories": [[check.label, check.ok] for check in result.directories],
            "config_files": [[check.label, check.ok] for check in result.config_files],
            "configs": [
                {"label": check.label, "ok": check.ok, "details": check.details}
                for check in result.configs
            ],
            "used_standard_configs": result.used_standard_configs,
        }
        return json.dumps(payload)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def build_dd_project(
    zip_bytes: bytes, config_name: str = "", clean: bool = False
) -> str:
    """Build DD intents from an uploaded project zip; returns the intents/ folder as a zip."""
    layout = ProjectLayout()
    work_dir = _extract_zip(zip_bytes)
    try:
        reporter = WebReporter()
        config = Path(work_dir, config_name or layout.dd_config)
        result = build_intents.intents(
            "DD", config, work_dir, reporter, clean, NamingRules(), layout
        )
        payload = {
            "messages": reporter.messages,
            "summary": result_views.summary_rows(result),
            "issues": result_views.result_issues(result),
        }
        output_zip = _zip_dir(result.output_dir) if result.output_dir else None
        return _respond(payload, output_zip)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def build_nl_project(
    zip_bytes: bytes,
    config_name: str = "",
    vertical: str = "",
    context: str = "",
    lowercase: bool = False,
    reuse: bool = False,
    clean: bool = False,
) -> str:
    """Build NL intents from an uploaded project zip; returns the intents/ folder as a zip."""
    layout = ProjectLayout()
    work_dir = _extract_zip(zip_bytes)
    try:
        reporter = WebReporter()
        config = Path(work_dir, config_name or layout.nl_config)
        if not reuse or not config.exists():
            if not vertical.strip():
                raise exceptions.ConfigurationError(
                    "Enter a vertical prefix to build the NL config."
                )
            build_intents.nl_config(
                config,
                vertical.strip(),
                context.strip() or NlDefaults().context,
                lowercase,
                reporter,
                layout,
            )
        result = build_intents.intents(
            "NL", config, work_dir, reporter, clean, NamingRules(), layout
        )
        payload = {
            "messages": reporter.messages,
            "summary": result_views.summary_rows(result),
            "issues": result_views.result_issues(result),
        }
        output_zip = _zip_dir(result.output_dir) if result.output_dir else None
        return _respond(payload, output_zip)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def extract_project(
    excel_bytes: bytes, filename: str, mode: str = "NL", language: str = "en"
) -> str:
    """Extract phrases from an uploaded Excel file; returns the Training Phrases folder as a zip."""
    work_dir = Path(tempfile.mkdtemp(prefix="intentional_web_"))
    try:
        xl_file = work_dir / filename
        xl_file.write_bytes(excel_bytes)
        reporter = WebReporter()
        result = extracting.excel_data(
            xl_file, mode, language, work_dir, reporter, ProjectLayout()
        )
        payload = {
            "messages": reporter.messages,
            "files": result.files,
            "phrases": result.phrases,
            "empty_sheets": result.empty_sheets,
        }
        return _respond(payload, _zip_dir(result.output_dir))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def design_project(
    excel_bytes: bytes, filename: str, sheet: str = "", config_name: str = ""
) -> str:
    """Create a config file from an uploaded Excel design document; returns it as a zip."""
    layout = ProjectLayout()
    work_dir = Path(tempfile.mkdtemp(prefix="intentional_web_"))
    try:
        xl_file = work_dir / filename
        xl_file.write_bytes(excel_bytes)
        config = Path(work_dir, config_name or layout.dd_config)
        reporter = WebReporter()
        result = design_doc.config_from_design(
            xl_file, config, reporter, sheet, NamingRules()
        )
        payload = {
            "messages": reporter.messages,
            "rows": result.rows,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        return _respond(payload, _zip_file(result.config))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def compare_project(
    zip_bytes: bytes,
    export_bytes: bytes,
    export_filename: str,
    mode: str = "DD",
    config_name: str = "",
) -> str:
    """Compare an uploaded project zip's build with an uploaded agent export; writes nothing."""
    layout = ProjectLayout()
    work_dir = _extract_zip(zip_bytes)
    try:
        default = layout.nl_config if mode == "NL" else layout.dd_config
        config = Path(work_dir, config_name or default)
        export_path = Path(
            work_dir, f"__export__{Path(export_filename).suffix or '.zip'}"
        )
        export_path.write_bytes(export_bytes)
        reporter = WebReporter()
        result = build_intents.compare_build(
            mode, config, work_dir, export_path, reporter, NamingRules(), layout
        )
        payload = {
            "messages": reporter.messages,
            "source": result.source,
            "added": result.added,
            "changed": [
                {"name": change.name, "details": change.details}
                for change in result.changed
            ],
            "removed": result.removed,
            "unchanged": result.unchanged,
        }
        return json.dumps(payload)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
