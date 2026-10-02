"""Browser-facing actions: unpack an uploaded project zip, run a task against
it with the unmodified core, and hand back a JSON-serializable result.

Mirrors gui/actions.py's role for the desktop GUI, but zip-in/JSON-out instead
of a picked folder, since a browser tab has no direct access to the user's
filesystem. The functions here don't touch Pyodide-specific APIs, so they can
(and do) run under plain CPython in the test suite too.
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from intentional_py import validate as validating
from intentional_py.models import NamingRules, ProjectLayout
from intentional_py.web.reporter import WebReporter


def _extract_zip(zip_bytes: bytes) -> Path:
    work_dir = Path(tempfile.mkdtemp(prefix="intentional_web_"))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        archive.extractall(work_dir)
    return work_dir


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
