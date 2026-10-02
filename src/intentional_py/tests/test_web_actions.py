import io
import json
import zipfile
from pathlib import Path

from intentional_py.tests.conftest import dd_project
from intentional_py.web.actions import validate_project


def _zip_dir(directory: Path) -> bytes:
    """Zip a directory's contents at the archive root, like a user's project zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in directory.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(directory))
    return buffer.getvalue()


def test_validate_project_passes_for_a_valid_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    dd_project(
        project,
        ["A.Pay,Ctx,en,pay,,,"],
        {"pay": "pay my bill"},
    )

    result = json.loads(validate_project(_zip_dir(project)))

    assert result["used_standard_configs"] is True
    # only English phrases exist in this project; other languages are expected to fail
    assert ("English path", True) in [tuple(d) for d in result["directories"]]
    # only intents.cfg exists; intents_nl.cfg is one of the two standard files checked
    assert ("Checking for intents.cfg", True) in [
        tuple(c) for c in result["config_files"]
    ]
    assert all(config["ok"] for config in result["configs"])


def test_validate_project_reports_row_errors(tmp_path: Path) -> None:
    project = tmp_path / "project"
    dd_project(
        project,
        ["A-B,Ctx,en,pay,,,"],
        {"pay": "pay my bill"},
    )

    result = json.loads(validate_project(_zip_dir(project)))

    config = next(c for c in result["configs"] if not c["ok"])
    assert any("A-B" in detail for detail in config["details"])


def test_validate_project_uses_the_given_config_name(tmp_path: Path) -> None:
    project = tmp_path / "project"
    dd_project(
        project,
        ["A.Pay,Ctx,en,pay,,,"],
        {"pay": "pay my bill"},
        layout=None,
    )
    (project / "custom.cfg").write_text(
        (project / "intents.cfg").read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = json.loads(validate_project(_zip_dir(project), "custom.cfg"))

    assert result["used_standard_configs"] is False
    assert all(config["ok"] for config in result["configs"])
