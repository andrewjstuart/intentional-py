import csv
import json
import zipfile
from pathlib import Path

import openpyxl
import pytest

from intentional_py import build_intents, compare, design_doc, exceptions, validate


class QuietReporter:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def message(self, level, text):
        self.messages.append((level, text))

    def table(self, columns, rows, level="info"):
        pass

    def track(self, items, label):
        yield from items

    def confirm(self, question, details=None):
        return True


def dd_project(base: Path, rows: list[str], phrases: dict[str, str]) -> Path:
    phrase_dir = base / "Training Phrases" / "en"
    phrase_dir.mkdir(parents=True, exist_ok=True)
    for name, text in phrases.items():
        (phrase_dir / f"{name}.txt").write_text(text, encoding="utf-8")
    config = base / "intents.cfg"
    config.write_text("".join(f"{row}\n" for row in rows), encoding="utf-8")
    return config


def warnings_for(config: Path) -> list[str]:
    return validate.preflight_config(config, config.parent, "DD")[2]


# ----- phrase checks -----


def test_entity_tag_problems_are_grouped_per_file(tmp_path: Path) -> None:
    config = dd_project(
        tmp_path,
        ["A.Pay,Ctx,en,pay,sys.unit-currency*,,"],
        {"pay": "pay <sys.unit-currency|$5>\npay <sys.unit-currency|$6\npay <sys.date|today>\npay <nope>\n"},
    )
    warnings = warnings_for(config)
    assert "Row 1: 'pay.txt' has an unmatched '<' or '>' on line 2." in warnings
    assert "Row 1: 'pay.txt' has an entity tag without the <entity|text> form on line 4." in warnings
    assert (
        "Row 1: 'pay.txt' uses the entity 'sys.date' on line 3, but it is not in the row's Entities column."
        in warnings
    )
    assert len(warnings) == 3


def test_entity_aliases_and_required_markers_match(tmp_path: Path) -> None:
    config = dd_project(
        tmp_path,
        ["A.Phone,Ctx,en,phone,sys.phone-number[phone]*|digits4,,"],
        {"phone": "<sys.phone-number[phone]|4025551234>\nlast four <digits4*|1234>\n"},
    )
    assert warnings_for(config) == []


def test_empty_phrase_file(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.Empty,Ctx,en,empty,,,"], {"empty": "\n  \n"})
    assert warnings_for(config) == ["Row 1: phrase file 'empty.txt' is empty; the intent will have no phrases."]


def test_duplicate_phrases_only_matter_within_a_context(tmp_path: Path) -> None:
    config = dd_project(
        tmp_path,
        ["A.Yes,Menu,en,yes,,,", "A.Sure,Menu,en,sure,,,", "B.Yes,Other,en,yes,,,"],
        {"yes": "Yes\nyeah\n", "sure": "yes\nsure\n"},
    )
    assert warnings_for(config) == [
        (
            "Row 2: 'A.Sure' shares a phrase (e.g. 'yes') with 'A.Yes' (row 1), "
            "which has the same context 'Menu' and language 'en'."
        )
    ]


def test_intent_without_english_row_is_complete(tmp_path: Path) -> None:
    for language, phrase in (("en", "pay my bill"), ("es", "pagar mi factura")):
        phrase_dir = tmp_path / "Training Phrases" / language
        phrase_dir.mkdir(parents=True)
        (phrase_dir / "pagar.txt").write_text(f"{phrase}\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"
    config.write_text("A.Pay,Ctx,es,pagar,,,\n", encoding="utf-8")

    rows, errors, warnings = validate.preflight_config(config, tmp_path, "DD")
    result = build_intents.intents("DD", config, tmp_path, QuietReporter())

    assert errors == []
    assert len(rows) == 2
    assert warnings == [
        "Row 1: intent 'A.Pay' has no English ('en') row; an English row will be synthesized from this row ('es')."
    ]
    assert result.files == 3
    assert (tmp_path / "intents" / "A.Pay.json").exists()
    english = json.loads(
        (tmp_path / "intents" / "A.Pay_usersays_en.json").read_text(encoding="utf-8")
    )
    assert english[0]["data"][0]["text"] == "pay my bill"
    assert (tmp_path / "intents" / "A.Pay_usersays_es.json").exists()


def test_synthesized_english_row_warns_when_phrases_are_missing(tmp_path: Path) -> None:
    phrase_dir = tmp_path / "Training Phrases" / "es"
    phrase_dir.mkdir(parents=True)
    (phrase_dir / "pagar.txt").write_text("pagar mi factura\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"
    config.write_text("A.Pay,Ctx,es,pagar,,,\n", encoding="utf-8")

    warnings = warnings_for(config)

    assert warnings == [
        "Row 1: intent 'A.Pay' has no English ('en') row; an English row will be synthesized from this row ('es').",
        (
            "Row 1: synthesized English row for 'A.Pay': phrase file "
            f"'{tmp_path / 'Training Phrases' / 'en' / 'pagar.txt'}' was not found; "
            "the English intent will be generated without those phrases."
        ),
    ]


def test_english_row_owns_multilingual_intent_definition(tmp_path: Path) -> None:
    for language, action in (("es", "pagar"), ("en", "pay")):
        phrase_dir = tmp_path / "Training Phrases" / language
        phrase_dir.mkdir(parents=True)
        (phrase_dir / f"{action}.txt").write_text(f"{action}\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"
    config.write_text(
        "A.Pay,Context-es,es,pagar,,,\nA.Pay,Context-en,en,pay,,,\n", encoding="utf-8"
    )

    build_intents.intents("DD", config, tmp_path, QuietReporter())

    intent = json.loads((tmp_path / "intents" / "A.Pay.json").read_text(encoding="utf-8"))
    assert intent["contexts"] == ["Context-en"]
    assert intent["responses"][0]["action"] == "pay"
    assert (tmp_path / "intents" / "A.Pay_usersays_es.json").exists()


def test_duplicate_row_for_same_intent_and_language_does_not_duplicate_phrases(tmp_path: Path) -> None:
    config = dd_project(
        tmp_path,
        # an accidental copy-paste: the same intent, context, language and action twice
        ["A.Pay,Ctx,en,pay,,,", "A.Pay,Ctx,en,pay,,,"],
        {"pay": "pay my bill\nmake a payment\n"},
    )

    warnings = warnings_for(config)

    assert warnings == [
        "Row 2: intent 'A.Pay' also has language 'en' in row(s) 1; this row will be used instead."
    ]

    build_intents.intents("DD", config, tmp_path, QuietReporter())
    usersays = json.loads((tmp_path / "intents" / "A.Pay_usersays_en.json").read_text(encoding="utf-8"))
    texts = sorted(entry["data"][0]["text"] for entry in usersays)
    assert texts == ["make a payment", "pay my bill"]


# ----- clean and previous-build comparison -----


def test_clean_backs_up_and_removes_old_intents(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.One,Ctx,en,one,,,", "A.Two,Ctx,en,two,,,"], {"one": "one\n", "two": "two\n"})
    build_intents.intents("DD", config, tmp_path, QuietReporter())
    config.write_text("A.One,Ctx,en,one,,,\n", encoding="utf-8")

    result = build_intents.intents("DD", config, tmp_path, QuietReporter(), clean=True)

    assert result.changes.removed == ["A.Two"]
    assert sorted(p.name for p in (tmp_path / "intents").iterdir()) == ["A.One.json", "A.One_usersays_en.json"]
    with zipfile.ZipFile(result.backup) as backup:
        assert "A.Two.json" in backup.namelist()


def test_rebuild_without_clean_keeps_old_intents(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.One,Ctx,en,one,,,", "A.Two,Ctx,en,two,,,"], {"one": "one\n", "two": "two\n"})
    build_intents.intents("DD", config, tmp_path, QuietReporter())
    (tmp_path / "Training Phrases" / "en" / "one.txt").write_text("one\nuno\n", encoding="utf-8")
    config.write_text("A.One,Ctx,en,one,,,\n", encoding="utf-8")

    result = build_intents.intents("DD", config, tmp_path, QuietReporter())

    assert result.backup is None
    assert result.changes.removed == ["A.Two"]
    assert [(c.name, c.details) for c in result.changes.changed] == [("A.One", ["en phrases: 1 added, 0 removed"])]
    assert (tmp_path / "intents" / "A.Two.json").exists()


# ----- compare with an export -----


def test_compare_with_export_zip_ignores_ids(tmp_path: Path) -> None:
    config = dd_project(tmp_path, ["A.One,Ctx,en,one,,,", "A.Two,Ctx,en,two,,,FALSE"], {"one": "one\n", "two": "two\n"})
    build_intents.intents("DD", config, tmp_path, QuietReporter())
    export = tmp_path / "agent.zip"
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr("agent.json", "{}")
        for path in (tmp_path / "intents").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if path.name == "A.Two.json":
                data["auto"] = True
            archive.writestr(f"intents/{path.name}", json.dumps(data))
        archive.writestr("intents/Other.Intent.json", json.dumps({"name": "Other.Intent", "responses": [{}]}))
    config.write_text("A.One,Ctx,en,one,,,\nA.Two,Ctx,en,two,,,FALSE\nA.Three,Ctx,en,one,,,\n", encoding="utf-8")

    result = build_intents.compare_build("DD", config, tmp_path, export, QuietReporter())

    assert result.added == ["A.Three"]
    assert [(c.name, c.details) for c in result.changed] == [("A.Two", ["machine learning: on \u2192 off"])]
    assert result.removed == ["Other.Intent"]
    assert result.unchanged == 1
    assert not (tmp_path / "intents" / "A.Three.json").exists()


def test_compare_rejects_a_non_export(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(exceptions.FileSystemError):
        compare.load(tmp_path / "notes.txt")


# ----- design document -----


def make_design(path: Path, header_row: int = 2) -> Path:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Design"
    sheet.cell(1, 1, "Billing module design")
    headers = ["Intent", "Context", "Language", "Action", "Entities", "DTMF", "Machine Learning"]
    for column, header in enumerate(headers, start=1):
        sheet.cell(header_row, column, header)
    rows = [
        ["MYAC.Billing.Pay", "MYAC-Billing", "en", "pay", "sys.unit-currency", 1, "FALSE"],
        ["MYAC.Billing.Help", "MYAC-Billing", "en", "help", None, None, "TRUE"],
        [None, None, None, None, None, None, None],
        ["MYAC.Billing.Menu", "MYAC-Billing", "en", "menu", None, "2|3", None],
    ]
    for offset, row in enumerate(rows, start=1):
        for column, value in enumerate(row, start=1):
            sheet.cell(header_row + offset, column, value)
    workbook.save(path)
    return path


def test_design_document_becomes_config(tmp_path: Path) -> None:
    xl_file = make_design(tmp_path / "design.xlsx")
    config = tmp_path / "intents.cfg"
    config.write_text("OLD.Row,Ctx,en,old,,,\n", encoding="utf-8")

    result = design_doc.config_from_design(xl_file, config, QuietReporter())

    with config.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert rows == [
        ["MYAC.Billing.Pay", "MYAC-Billing", "en", "pay", "sys.unit-currency", "1", "FALSE"],
        ["MYAC.Billing.Help", "MYAC-Billing", "en", "help", "", "", "TRUE"],
        ["MYAC.Billing.Menu", "MYAC-Billing", "en", "menu", "", "2|3", ""],
    ]
    assert (result.sheet, result.rows, result.errors) == ("Design", 3, [])
    assert result.backup.read_text(encoding="utf-8") == "OLD.Row,Ctx,en,old,,,\n"


def test_design_document_without_headers(tmp_path: Path) -> None:
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = "no headers here"
    workbook.save(tmp_path / "bad.xlsx")
    with pytest.raises(exceptions.ConfigurationError, match="No header row"):
        design_doc.config_from_design(tmp_path / "bad.xlsx", tmp_path / "intents.cfg", QuietReporter())


# ----- CLI commands -----


def test_cli_design_compare_and_clean(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    monkeypatch.setenv("COLUMNS", "200")
    runner = CliRunner()
    xl_file = make_design(tmp_path / "design.xlsx")
    phrases = tmp_path / "Training Phrases" / "en"
    phrases.mkdir(parents=True)
    for action in ("pay", "help", "menu"):
        (phrases / f"{action}.txt").write_text(f"{action}\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"

    result = runner.invoke(app, ["design", "--file", str(xl_file), "--config", str(config)])
    assert result.exit_code == 0, result.stdout
    assert config.exists()

    assert runner.invoke(app, ["--config", str(config)]).exit_code == 0
    result = runner.invoke(app, ["compare", "--export", str(tmp_path / "intents"), "--config", str(config)])
    assert result.exit_code == 0, result.stdout
    assert "Unchanged" in result.stdout

    (tmp_path / "intents" / "Stale.Intent.json").write_text("{}", encoding="utf-8")
    result = runner.invoke(app, ["--config", str(config), "--clean"])
    assert result.exit_code == 0, result.stdout
    assert not (tmp_path / "intents" / "Stale.Intent.json").exists()
    assert list(tmp_path.glob("intents_*.zip"))


# ----- GUI settings and update check -----


def test_settings_round_trip(tmp_path: Path) -> None:
    from intentional_py.gui import settings

    path = tmp_path / "settings.json"
    assert settings.load(path) == settings.DEFAULTS
    values = settings.load(path)
    for project in ["a", "b", "a", *(str(n) for n in range(10))]:
        settings.add_recent(values, project)
    values["clean"] = True
    settings.save(values, path)

    loaded = settings.load(path)
    assert loaded["clean"] is True
    assert loaded["recent_projects"][:2] == ["9", "8"]
    assert len(loaded["recent_projects"]) == settings.MAX_RECENT
    path.write_text("not json", encoding="utf-8")
    assert settings.load(path) == settings.DEFAULTS


def test_update_version_comparison() -> None:
    from intentional_py.gui import updates

    assert updates.is_newer("1.0.6", "1.0.5")
    assert updates.is_newer("v1.1.0", "1.0.10")
    assert not updates.is_newer("1.0.5", "1.0.5")
    assert not updates.is_newer("1.0.4", "1.0.5")
