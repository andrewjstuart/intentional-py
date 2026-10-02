"""Browser-facing actions, operating on one project workspace that persists
for the whole page session (Pyodide keeps its virtual filesystem alive for as
long as the page is open). Extract, Build and Design write their output
straight into that workspace, so a later task sees it immediately, and the
project can be downloaded at any point — no zip round trip between tasks.

Mirrors gui/actions.py's role for the desktop GUI: the session workspace here
plays the part of the picked project folder. The functions here don't touch
Pyodide-specific APIs, so they can (and do) run under plain CPython in the
test suite too. JSON summaries reuse result_views.py, the same shaping
report.py and gui/actions.py already use, so all three front ends describe a
result the same way.
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from intentional_py import build_intents, design_doc, exceptions, result_views, utils
from intentional_py import extract as extracting
from intentional_py import validate as validating
from intentional_py.models import NamingRules, NlDefaults, ProjectLayout
from intentional_py.web.reporter import WebReporter

_workspace: Path | None = None


def _require_workspace() -> Path:
    if _workspace is None:
        raise exceptions.ConfigurationError(
            "Start or open a project before running a task."
        )
    return _workspace


def _zip_dir(directory: Path) -> bytes:
    """Zip a directory's contents at the archive root, for the browser to download."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in directory.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(directory))
    return buffer.getvalue()


def _project_status() -> str:
    workspace = _require_workspace()
    files = sorted(
        str(path.relative_to(workspace))
        for path in workspace.rglob("*")
        if path.is_file()
    )
    return json.dumps({"files": files})


def new_project() -> str:
    """Start a fresh, empty project for this session; returns its (empty) file listing."""
    global _workspace
    if _workspace is not None:
        shutil.rmtree(_workspace, ignore_errors=True)
    _workspace = Path(tempfile.mkdtemp(prefix="intentional_web_"))
    return _project_status()


def open_project(zip_bytes: bytes) -> str:
    """Start this session's project from an uploaded zip; returns its file listing."""
    new_project()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        # reject a member path (e.g. '../../etc/passwd') that would land outside the
        # workspace, before extracting anything - zipfile.extractall() does not check this
        for name in archive.namelist():
            utils.safe_join(_workspace, name)
        archive.extractall(_workspace)
    return _project_status()


def project_files() -> str:
    """The current project's file listing, e.g. to refresh a status display."""
    return _project_status()


def download_project() -> bytes:
    """Zip the whole current project, to save it or take it to the GUI/CLI."""
    return _zip_dir(_require_workspace())


def validate_project(config_name: str = "") -> str:
    """Validate the current project.

    config_name (str): name of the config file to validate; blank checks the
        standard config files, same as the CLI/GUI default.
    """
    workspace = _require_workspace()
    reporter = WebReporter()
    config = Path(workspace, config_name) if config_name else Path()
    result = validating.validate(
        config, workspace, reporter, NamingRules(), ProjectLayout()
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


def build_dd_project(config_name: str = "", clean: bool = False) -> str:
    """Build DD intents into the current project."""
    workspace = _require_workspace()
    layout = ProjectLayout()
    reporter = WebReporter()
    config = Path(workspace, config_name or layout.dd_config)
    result = build_intents.intents(
        "DD", config, workspace, reporter, clean, NamingRules(), layout
    )
    return json.dumps(
        {
            "messages": reporter.messages,
            "summary": result_views.summary_rows(result),
            "issues": result_views.result_issues(result),
        }
    )


def build_nl_project(
    config_name: str = "",
    vertical: str = "",
    context: str = "",
    lowercase: bool = False,
    reuse: bool = False,
    clean: bool = False,
) -> str:
    """Build NL intents into the current project."""
    workspace = _require_workspace()
    layout = ProjectLayout()
    reporter = WebReporter()
    config = Path(workspace, config_name or layout.nl_config)
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
        "NL", config, workspace, reporter, clean, NamingRules(), layout
    )
    return json.dumps(
        {
            "messages": reporter.messages,
            "summary": result_views.summary_rows(result),
            "issues": result_views.result_issues(result),
        }
    )


def extract_project(
    excel_bytes: bytes, filename: str, mode: str = "NL", language: str = "en"
) -> str:
    """Extract phrases from an uploaded Excel file into the current project."""
    workspace = _require_workspace()
    upload_dir = Path(tempfile.mkdtemp(prefix="intentional_web_upload_"))
    try:
        xl_file = upload_dir / filename
        xl_file.write_bytes(excel_bytes)
        reporter = WebReporter()
        result = extracting.excel_data(
            xl_file, mode, language, workspace, reporter, ProjectLayout()
        )
        return json.dumps(
            {
                "messages": reporter.messages,
                "files": result.files,
                "phrases": result.phrases,
                "empty_sheets": result.empty_sheets,
            }
        )
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)


def design_project(
    excel_bytes: bytes, filename: str, sheet: str = "", config_name: str = ""
) -> str:
    """Create a config file from an uploaded Excel design document, in the current project."""
    workspace = _require_workspace()
    layout = ProjectLayout()
    upload_dir = Path(tempfile.mkdtemp(prefix="intentional_web_upload_"))
    try:
        xl_file = upload_dir / filename
        xl_file.write_bytes(excel_bytes)
        config = Path(workspace, config_name or layout.dd_config)
        reporter = WebReporter()
        result = design_doc.config_from_design(
            xl_file, config, reporter, sheet, NamingRules()
        )
        return json.dumps(
            {
                "messages": reporter.messages,
                "rows": result.rows,
                "errors": result.errors,
                "warnings": result.warnings,
            }
        )
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)


def compare_project(
    export_bytes: bytes,
    export_filename: str,
    mode: str = "DD",
    config_name: str = "",
) -> str:
    """Compare what the current project would build with an uploaded agent export."""
    workspace = _require_workspace()
    layout = ProjectLayout()
    upload_dir = Path(tempfile.mkdtemp(prefix="intentional_web_upload_"))
    try:
        default = layout.nl_config if mode == "NL" else layout.dd_config
        config = Path(workspace, config_name or default)
        export_path = upload_dir / f"export{Path(export_filename).suffix or '.zip'}"
        export_path.write_bytes(export_bytes)
        reporter = WebReporter()
        result = build_intents.compare_build(
            mode, config, workspace, export_path, reporter, NamingRules(), layout
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
        shutil.rmtree(upload_dir, ignore_errors=True)
