"""Tests for build_intents.package_export(): merging a build into a copy of an agent
export zip. The export's own layout (entries outside intents/, and whether intents/ is
nested under an agent-name folder) is guessed from a synthetic zip here - the exact
shape will need checking against a real Dialogflow export once one is available.
"""

import json
import zipfile
from pathlib import Path

import pytest

from intentional_py import build_intents, exceptions
from intentional_py.tests.conftest import FakeReporter, dd_project


def _make_export(path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _read_zip(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}


def test_package_export_adds_a_new_intent_and_leaves_others_alone(
    tmp_path: Path,
) -> None:
    export = tmp_path / "agent.zip"
    _make_export(
        export,
        {
            "agent.json": "{}",
            "intents/Old.json": json.dumps({"name": "Old"}),
            "intents/Old_usersays_en.json": "[]",
        },
    )
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )

    result = build_intents.package_export(
        "DD", config, tmp_path, export, FakeReporter()
    )

    assert result.added == ["A.Pay"]
    assert result.removed == []
    assert result.unmarked == ["Old"]
    assert result.output is not None
    assert result.output.parent == export.parent
    assert result.output.name.startswith("agent_")
    assert result.output.name.endswith(".zip")
    assert result.output != export

    contents = _read_zip(result.output)
    assert "intents/A.Pay.json" in contents
    assert "intents/A.Pay_usersays_en.json" in contents
    # untouched entries are carried over unchanged
    assert contents["agent.json"] == "{}"
    assert contents["intents/Old.json"] == json.dumps({"name": "Old"})
    # the original export is never modified
    assert _read_zip(export) == {
        "agent.json": "{}",
        "intents/Old.json": json.dumps({"name": "Old"}),
        "intents/Old_usersays_en.json": "[]",
    }


def test_package_export_force_removes_a_marked_intent(tmp_path: Path) -> None:
    export = tmp_path / "agent.zip"
    _make_export(
        export,
        {
            "agent.json": "{}",
            "intents/A.Pay.json": json.dumps({"name": "A.Pay"}),
            "intents/A.Pay_usersays_en.json": "[]",
        },
    )
    config = dd_project(tmp_path, ["--A.Pay,Ctx,en,pay,,1,FALSE"], {})
    reporter = FakeReporter()

    result = build_intents.package_export("DD", config, tmp_path, export, reporter)

    assert reporter.questions == []
    assert sorted(result.removed) == ["A.Pay.json", "A.Pay_usersays_en.json"]
    contents = _read_zip(result.output)
    assert "intents/A.Pay.json" not in contents
    assert "intents/A.Pay_usersays_en.json" not in contents
    assert contents["agent.json"] == "{}"


def test_package_export_asks_before_removing_with_a_single_dash(tmp_path: Path) -> None:
    export = tmp_path / "agent.zip"
    _make_export(
        export,
        {
            "intents/A.Pay.json": json.dumps({"name": "A.Pay"}),
            "intents/A.Pay_usersays_en.json": "[]",
        },
    )
    config = dd_project(tmp_path, ["-A.Pay,Ctx,en,pay,,1,FALSE"], {})
    reporter = FakeReporter(answer=True)

    result = build_intents.package_export("DD", config, tmp_path, export, reporter)

    assert reporter.questions == ["Remove the intents marked for removal"]
    assert sorted(result.removed) == ["A.Pay.json", "A.Pay_usersays_en.json"]


def test_package_export_aborts_when_removal_is_declined(tmp_path: Path) -> None:
    export = tmp_path / "agent.zip"
    _make_export(export, {"intents/A.Pay.json": json.dumps({"name": "A.Pay"})})
    original = export.read_bytes()
    config = dd_project(tmp_path, ["-A.Pay,Ctx,en,pay,,1,FALSE"], {})
    reporter = FakeReporter(answer=False)

    with pytest.raises(exceptions.IntentionalException):
        build_intents.package_export("DD", config, tmp_path, export, reporter)

    # nothing was written: neither the export nor any new copy next to it
    assert export.read_bytes() == original
    assert list(tmp_path.glob("agent_*.zip")) == []


def test_package_export_detects_a_nested_intents_folder(tmp_path: Path) -> None:
    export = tmp_path / "agent.zip"
    _make_export(
        export,
        {
            "MyAgent/agent.json": "{}",
            "MyAgent/intents/Old.json": json.dumps({"name": "Old"}),
        },
    )
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )

    result = build_intents.package_export(
        "DD", config, tmp_path, export, FakeReporter()
    )

    contents = _read_zip(result.output)
    assert "MyAgent/intents/A.Pay.json" in contents
    assert "MyAgent/intents/A.Pay_usersays_en.json" in contents
    assert "MyAgent/agent.json" in contents
