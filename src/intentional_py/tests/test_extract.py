from typer.testing import CliRunner
from intentional_py import intentional
import shutil
from pathlib import Path

runner = CliRunner()

app = intentional.app


# tests the extraction functionality of intentional
def test_extract_XLSM():
    # Extract Data XLSM
    data_src: str = "./src/intentional_py/tests/data"
    result = runner.invoke(
        app, ["extract", "--file", f"{data_src}/NL_English_Data.xlsm"]
    )
    assert result.exit_code == 0
    data_src: str = "./src/intentional_py/tests/data"
    result = runner.invoke(
        app,
        ["extract", "--file", f"{data_src}/NL_Spanish_Data.xlsm", "--language", "es"],
    )
    assert result.exit_code == 0

    # clean up Training Phrase directory
    training_phrase_path: Path = Path(data_src, "Training PHrases")
    if training_phrase_path.exists():
        shutil.rmtree(training_phrase_path)


def test_extract_XLSB():

    # Extract Data XLSB
    data_src: str = "./src/intentional_py/tests/data"
    result = runner.invoke(
        app, ["extract", "--file", f"{data_src}/NL_English_Data.xlsb"]
    )
    assert result.exit_code == 0
    data_src: str = "./src/intentional_py/tests/data"
    result = runner.invoke(
        app,
        ["extract", "--file", f"{data_src}/NL_Spanish_Data.xlsb", "--language", "es"],
    )
    assert result.exit_code == 0

    # does not clean up, because they're used by the NL test
