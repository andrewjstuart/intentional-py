from pathlib import Path

from typer.testing import CliRunner

from intentional_py import extract as extract_module
from intentional_py import intentional

runner = CliRunner()

app = intentional.app


# tests the extraction functionality of intentional
def test_extract_exceptions(data_dir: Path):
    xl_file = Path(data_dir, "sample_file.xlsx")

    result = runner.invoke(app, ["extract", "--file", str(xl_file)])
    assert result.exit_code == 1
    assert (
        f"{xl_file} does NOT exist as a file." + "\nAbort processing...\n"
        in result.stdout
    )


def extract(data_dir: Path, file: str, language: str) -> None:
    xl_output_path = Path(data_dir, "Training Phrases", language, "NL")
    result = runner.invoke(
        app,
        [
            "extract",
            "--file",
            str(Path(data_dir, file)),
            "--language",
            language,
            "--test",
        ],
    )
    assert result.exit_code == 0
    assert (
        f"Exporting data to: {xl_output_path}"
        + f"\nProcessing {file}"
        + "\nextract complete\n"
        in result.stdout
    )


def test_extract_XLSM(data_dir: Path):
    extract(data_dir, "NL_English_Data.xlsm", "en")
    extract(data_dir, "NL_Spanish_Data.xlsm", "es")


def test_extract_XLSB(data_dir: Path):
    # the phrases extracted here are used by the NL tests
    extract(data_dir, "NL_English_Data.xlsb", "en")
    extract(data_dir, "NL_Spanish_Data.xlsb", "es")


def test_read_workbook_xlsx_uses_safe_openpyxl_mode_and_closes(monkeypatch):
    class FakeSheet:
        def iter_rows(self, values_only=True):
            assert values_only is True
            return [("hello", None), ("",), ("hello", None)]

    class FakeWorkbook:
        def __init__(self):
            self.sheetnames = ["Sample"]
            self.closed = False

        def __getitem__(self, name: str):
            assert name == "Sample"
            return FakeSheet()

        def close(self):
            self.closed = True

    workbook = FakeWorkbook()

    def fake_load_workbook(path: Path, read_only: bool, data_only: bool):
        assert read_only is True
        assert data_only is True
        assert path == Path("dummy.xlsx")
        return workbook

    monkeypatch.setattr(extract_module.openpyxl, "load_workbook", fake_load_workbook)

    phrase_dict = extract_module._read_workbook(
        Path("dummy.xlsx"),
        ".xlsx",
        Path("phrases"),
        "Processing",
        reporter=type(
            "Reporter", (), {"track": staticmethod(lambda items, _label: items)}
        )(),
    )

    assert workbook.closed is True
    assert phrase_dict[Path("phrases", "Sample.txt")] == ["hello"]
