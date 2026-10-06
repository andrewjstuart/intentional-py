"""Tests for build_intents.package_export(): merging a build into a copy of an agent
export zip, in either of Dialogflow ES's own styles: "restore" (a complete zip, since
Restore replaces the whole agent) or "import" (a partial zip of just the new/changed
intents, since Import only adds or overwrites and never deletes). The confirmed export
layout is a top-level intents/ folder alongside agent.json and package.json.
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
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    result = build_intents.package_export(tmp_path, export, FakeReporter())

    assert result.added == ["A.Pay"]
    assert result.removed == []
    assert result.unmarked == ["Old"]
    assert result.output is not None
    assert result.output.parent == export.parent
    assert result.output.name.startswith("agent_restore_")
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


def test_package_export_never_deletes_an_intent_only_the_config_removed(
    tmp_path: Path,
) -> None:
    # packaging doesn't rebuild or know about '-'/'--' rows, or any config at all -
    # an intent removed from the intents folder by a past build still stays in the
    # export when packaging on its own, surfaced as "unmarked" rather than deleted,
    # the same as any other intent only in the export (e.g. another module's).
    # Deleting it from the export too needs either the combined build-and-merge
    # flow (intents()'s own `export` parameter, with the removal row still present)
    # or removing it from the export by hand.
    export = tmp_path / "agent.zip"
    _make_export(
        export,
        {
            "agent.json": "{}",
            "intents/A.Pay.json": json.dumps({"name": "A.Pay"}),
            "intents/A.Pay_usersays_en.json": "[]",
        },
    )
    config = dd_project(
        tmp_path,
        ["A.Pay,Ctx,en,pay,,1,FALSE", "A.Help,Ctx,en,help,,1,FALSE"],
        {"pay": "pay my bill\n", "help": "help me\n"},
    )
    build_intents.intents("DD", config, tmp_path, FakeReporter())
    assert (tmp_path / "intents" / "A.Pay.json").exists()

    config.write_text(
        "--A.Pay,Ctx,en,pay,,1,FALSE\nA.Help,Ctx,en,help,,1,FALSE\n", encoding="utf-8"
    )
    build_intents.intents("DD", config, tmp_path, FakeReporter())
    assert not (tmp_path / "intents" / "A.Pay.json").exists()

    result = build_intents.package_export(tmp_path, export, FakeReporter())

    assert result.unmarked == ["A.Pay"]
    contents = _read_zip(result.output)
    assert "intents/A.Pay.json" in contents
    assert "intents/A.Help.json" in contents
    assert contents["agent.json"] == "{}"


def test_package_export_requires_an_existing_intents_folder(tmp_path: Path) -> None:
    export = tmp_path / "agent.zip"
    _make_export(export, {"agent.json": "{}"})

    with pytest.raises(exceptions.IntentionalException):
        build_intents.package_export(tmp_path, export, FakeReporter())


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
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    result = build_intents.package_export(tmp_path, export, FakeReporter())

    contents = _read_zip(result.output)
    assert "MyAgent/intents/A.Pay.json" in contents
    assert "MyAgent/intents/A.Pay_usersays_en.json" in contents
    assert "MyAgent/agent.json" in contents


def test_package_export_import_style_is_partial_and_never_deletes(
    tmp_path: Path,
) -> None:
    export = tmp_path / "agent.zip"
    _make_export(
        export,
        {
            "agent.json": "{}",
            "package.json": "{}",
            "entities/Color.json": "[]",
            "intents/Old.json": json.dumps({"name": "Old"}),
            "intents/Old_usersays_en.json": "[]",
        },
    )
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    result = build_intents.package_export(
        tmp_path, export, FakeReporter(), style="import"
    )

    assert result.style == "import"
    assert result.added == ["A.Pay"]
    assert result.removed == []
    assert result.output.name.startswith("agent_import_")

    contents = _read_zip(result.output)
    assert set(contents) == {
        "intents/A.Pay.json",
        "intents/A.Pay_usersays_en.json",
    }
    # neither the export's own agent.json/package.json, nor unmentioned entries
    # (other intents, entities), are carried over - this tool doesn't write
    # agent.json/package.json, and Import leaves everything else alone anyway
    assert "intents/Old.json" not in contents
    assert "entities/Color.json" not in contents


def test_merge_cli_runs_a_complete_zip(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    export = tmp_path / "agent.zip"
    _make_export(export, {"agent.json": "{}", "intents/Old.json": "{}"})
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    result = CliRunner().invoke(
        app, ["merge", "--export", str(export), "--project", str(tmp_path)]
    )

    assert result.exit_code == 0, result.stdout
    assert "restore" in result.stdout.lower()
    assert list(tmp_path.glob("agent_restore_*.zip"))


def test_package_cli_runs_a_partial_zip(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    export = tmp_path / "agent.zip"
    _make_export(export, {"agent.json": "{}", "intents/Old.json": "{}"})
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )
    build_intents.intents("DD", config, tmp_path, FakeReporter())

    result = CliRunner().invoke(
        app, ["package", "--export", str(export), "--project", str(tmp_path)]
    )

    assert result.exit_code == 0, result.stdout
    assert "import" in result.stdout.lower()
    assert list(tmp_path.glob("agent_import_*.zip"))


def test_package_cli_requires_an_existing_intents_folder(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    export = tmp_path / "agent.zip"
    _make_export(export, {"agent.json": "{}"})

    result = CliRunner().invoke(
        app, ["package", "--export", str(export), "--project", str(tmp_path)]
    )

    assert result.exit_code != 0


def test_build_with_export_writes_both_the_intents_folder_and_a_package(
    tmp_path: Path,
) -> None:
    export = tmp_path / "agent.zip"
    _make_export(
        export, {"agent.json": "{}", "intents/Old.json": json.dumps({"name": "Old"})}
    )
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )

    result = build_intents.intents(
        "DD", config, tmp_path, FakeReporter(), export=export
    )

    # the intents folder is still written the same way as without `export`
    assert (tmp_path / "intents" / "A.Pay.json").exists()
    assert (tmp_path / "intents" / "A.Pay_usersays_en.json").exists()
    # ...and a package was merged in the same call, with no separate step
    assert result.package is not None
    assert result.package.style == "restore"
    assert result.package.added == ["A.Pay"]
    assert result.package.output is not None
    contents = _read_zip(result.package.output)
    assert "intents/A.Pay.json" in contents
    assert "intents/Old.json" in contents


def test_build_without_export_does_not_touch_any_zip(tmp_path: Path) -> None:
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )

    result = build_intents.intents("DD", config, tmp_path, FakeReporter())

    assert result.package is None
    assert list(tmp_path.glob("*.zip")) == []


def test_build_with_export_supports_the_import_style(tmp_path: Path) -> None:
    export = tmp_path / "agent.zip"
    _make_export(export, {"intents/Old.json": json.dumps({"name": "Old"})})
    config = dd_project(
        tmp_path, ["A.Pay,Ctx,en,pay,,1,FALSE"], {"pay": "pay my bill\n"}
    )

    result = build_intents.intents(
        "DD", config, tmp_path, FakeReporter(), export=export, package_style="import"
    )

    assert result.package.style == "import"
    contents = _read_zip(result.package.output)
    assert set(contents) == {"intents/A.Pay.json", "intents/A.Pay_usersays_en.json"}
    assert "intents/Old.json" not in contents
