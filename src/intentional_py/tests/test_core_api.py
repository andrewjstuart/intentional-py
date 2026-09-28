import json
import zipfile
from pathlib import Path

import openpyxl
import pytest

from intentional_py import build_intents, exceptions, extract


class FakeReporter:
    def __init__(self, answer: bool = True) -> None:
        self.answer = answer
        self.messages: list[tuple[str, str]] = []
        self.tables: list[list[str]] = []
        self.questions: list[str] = []

    def message(self, level, text):
        self.messages.append((level, text))

    def table(self, columns, rows, level="info", title=""):
        self.tables.append(columns)

    def track(self, items, label):
        yield from items

    def confirm(self, question):
        self.questions.append(question)
        return self.answer


def make_nl_phrases(base: Path) -> Path:
    nl_dir = base / "Training Phrases" / "en" / "NL"
    nl_dir.mkdir(parents=True)
    (nl_dir / "BILLING.txt").write_text("pay my bill\nhello\n", encoding="utf-8")
    (nl_dir / "GREETING.txt").write_text("hello\n", encoding="utf-8")
    return base / "intents_nl.cfg"


def test_nl_config_aborts_when_duplicates_declined(tmp_path: Path) -> None:
    config = make_nl_phrases(tmp_path)
    reporter = FakeReporter(answer=False)

    with pytest.raises(exceptions.IntentionalException):
        build_intents.nl_config(config, "RTL", "GetIntent", False, reporter)

    assert reporter.questions == ["Continue processing files"]


def test_nl_build_returns_result(tmp_path: Path) -> None:
    config = make_nl_phrases(tmp_path)
    reporter = FakeReporter(answer=True)

    build_intents.nl_config(config, "RTL", "GetIntent", False, reporter)
    result = build_intents.intents("NL", config, tmp_path, reporter)

    assert result.intents == 2
    assert result.phrases == 3
    assert result.files == 4
    assert result.languages == ["en"]
    assert (tmp_path / "intents" / "RTL.Billing.json").exists()


def test_nl_config_requires_training_phrases(tmp_path: Path) -> None:
    with pytest.raises(exceptions.FileSystemError):
        build_intents.nl_config(
            tmp_path / "intents_nl.cfg", "RTL", "GetIntent", False, FakeReporter()
        )


def test_nl_cli_uses_config_directory(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    project = tmp_path / "project"
    config = make_nl_phrases(project)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = CliRunner().invoke(
        app, ["nl", "--config", str(config), "-v", "RTL"], input="y\n"
    )

    assert result.exit_code == 0, result.stdout
    assert config.exists()
    assert (project / "intents" / "RTL.Billing.json").exists()
    assert not (elsewhere / "intents").exists()


def test_dd_build_machine_learning_column(tmp_path: Path) -> None:
    phrase_dir = tmp_path / "Training Phrases" / "en"
    phrase_dir.mkdir(parents=True)
    (phrase_dir / "on.txt").write_text("turn it on\n", encoding="utf-8")
    (phrase_dir / "off.txt").write_text("turn it off\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"
    config.write_text("A.On,Ctx,en,on,,\nA.Off,Ctx,en,off,,,FALSE\n", encoding="utf-8")

    result = build_intents.intents("DD", config, tmp_path, FakeReporter())

    intents_dir = tmp_path / "intents"
    assert json.loads((intents_dir / "A.On.json").read_text(encoding="utf-8"))["auto"] is True
    assert json.loads((intents_dir / "A.Off.json").read_text(encoding="utf-8"))["auto"] is False
    assert result.ml_disabled == ["A.Off"]


def test_dd_cli_uses_config_directory(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from intentional_py.intentional import app

    project = tmp_path / "project"
    phrase_dir = project / "Training Phrases" / "en"
    phrase_dir.mkdir(parents=True)
    (phrase_dir / "billing.txt").write_text("pay my bill\n", encoding="utf-8")
    config = project / "intents.cfg"
    config.write_text("MYAC.Billing,MYAC-Billing,en,billing,,,TRUE\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = CliRunner().invoke(app, ["--config", str(config)])

    assert result.exit_code == 0, result.stdout
    assert (project / "intents" / "MYAC.Billing_usersays_en.json").exists()
    assert not (elsewhere / "intents").exists()


def test_extract_reports_empty_sheets(tmp_path: Path) -> None:
    workbook = openpyxl.Workbook()
    workbook.active.title = "HELLO"
    workbook.active["A1"] = "hi there"
    workbook.create_sheet("EMPTY_ONE")
    xl_file = tmp_path / "phrases.xlsx"
    workbook.save(xl_file)

    result = extract.excel_data(xl_file, "NL", "en", tmp_path, FakeReporter())

    assert result.files == 2
    assert result.phrases == 1
    assert result.empty_sheets == ["EMPTY_ONE"]
    assert result.output_dir == tmp_path / "Training Phrases" / "en" / "NL"


def make_workbook(path: Path, sheet: str, phrase: str) -> Path:
    workbook = openpyxl.Workbook()
    workbook.active.title = sheet
    workbook.active["A1"] = phrase
    workbook.save(path)
    return path


def test_dd_extract_keeps_nl_phrases(tmp_path: Path) -> None:
    lang_dir = tmp_path / "Training Phrases" / "en"
    (lang_dir / "NL").mkdir(parents=True)
    (lang_dir / "NL" / "HELLO.txt").write_text("hello\n", encoding="utf-8")
    (lang_dir / "old.txt").write_text("old phrase\n", encoding="utf-8")
    xl_file = make_workbook(tmp_path / "dd.xlsx", "home", "at home")

    result = extract.excel_data(xl_file, "DD", "en", tmp_path, FakeReporter())

    assert (lang_dir / "NL" / "HELLO.txt").read_text(encoding="utf-8") == "hello\n"
    assert (lang_dir / "home.txt").read_text(encoding="utf-8") == "at home\n"
    assert not (lang_dir / "old.txt").exists()
    assert result.backup is not None and result.backup.parent == tmp_path / "Training Phrases"
    with zipfile.ZipFile(result.backup) as backup:
        assert backup.namelist() == ["old.txt"]


def test_corrupt_workbook_leaves_existing_phrases(tmp_path: Path) -> None:
    nl_dir = tmp_path / "Training Phrases" / "en" / "NL"
    nl_dir.mkdir(parents=True)
    (nl_dir / "HELLO.txt").write_text("hello\n", encoding="utf-8")
    xl_file = tmp_path / "broken.xlsx"
    xl_file.write_bytes(b"not an excel file")

    with pytest.raises(exceptions.ExtractionError, match="could not be read as an Excel file"):
        extract.excel_data(xl_file, "NL", "en", tmp_path, FakeReporter())

    assert (nl_dir / "HELLO.txt").exists()
    assert not list(nl_dir.parent.glob("*.zip"))


def test_non_utf8_phrase_file_names_the_file(tmp_path: Path) -> None:
    config = make_nl_phrases(tmp_path)
    bad_file = tmp_path / "Training Phrases" / "en" / "NL" / "SPANISH.txt"
    bad_file.write_bytes("año\n".encode("cp1252"))

    with pytest.raises(exceptions.FileSystemError, match="SPANISH.txt is not saved as UTF-8"):
        build_intents.nl_config(config, "RTL", "GetIntent", False, FakeReporter())
