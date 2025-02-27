from typer.testing import CliRunner
from intentional_py import intentional
import shutil
from pathlib import Path

runner = CliRunner()

app = intentional.app
data_src: str = "./src/intentional_py/tests/data"
temp_output_path: str = "src\\intentional_py\\tests\\data\\"
output_path = f"{temp_output_path}Training Phrases"


# tests the extraction functionality of intentional
def test_extract_exceptions():
    file: str = "sample_file.xlsx"

    result = runner.invoke(app, ["extract", "--file", f"{data_src}/{file}"])
    assert result.exit_code == 0
    assert (
        f"{temp_output_path}{file} does NOT exist as a file."
        + "\nAbort processing...\n"
        in result.stdout
    )


def test_extract_XLSM():
    # Extract Data XLSM
    file: str = "NL_English_Data.xlsm"
    xl_output_path: str = f"{output_path}\\en\\NL"
    result = runner.invoke(app, ["extract", "--file", f"{data_src}/{file}", "--test"])
    assert result.exit_code == 0
    assert (
        f"Exporting data to: {xl_output_path}"
        + f"\nProcessing {file}"
        + "\nextract complete\n"
        in result.stdout
    )

    file: str = "NL_Spanish_Data.xlsm"
    xl_output_path: str = f"{output_path}\\es\\NL"
    result = runner.invoke(
        app,
        [
            "extract",
            "--file",
            f"{data_src}/{file}",
            "--language",
            "es",
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
    # clean up Training Phrase directory
    training_phrase_path: Path = Path(data_src, "Training Phrases")
    if training_phrase_path.exists():
        shutil.rmtree(training_phrase_path)


def test_extract_XLSB():

    # Extract Data XLSB
    file: str = "NL_English_Data.xlsb"
    xl_output_path: str = f"{output_path}\\en\\NL"
    result = runner.invoke(app, ["extract", "--file", f"{data_src}/{file}", "--test"])
    assert result.exit_code == 0
    assert (
        f"Exporting data to: {xl_output_path}"
        + f"\nProcessing {file}"
        + "\nextract complete\n"
        in result.stdout
    )

    file: str = "NL_Spanish_Data.xlsb"
    xl_output_path: str = f"{output_path}\\es\\NL"
    result = runner.invoke(
        app,
        [
            "extract",
            "--file",
            f"{data_src}/NL_Spanish_Data.xlsb",
            "--language",
            "es",
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

    # does not clean up, because they're used by the NL test
