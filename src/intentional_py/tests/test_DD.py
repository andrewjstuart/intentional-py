import shutil
from pathlib import Path

from typer.testing import CliRunner

from intentional_py import intentional

runner = CliRunner()

app = intentional.app
data_src: str = "./src/intentional_py/tests/data"


# tests the DD functionality of intentional
def test_DD_exceptions():
    # empty config
    result = runner.invoke(app, ["--config", f"{data_src}/empty_intents.cfg"])
    assert result.exit_code == 1
    assert "Config file does not contain data" in result.stdout

    # incorrect config, does not exist
    result = runner.invoke(app, ["--config", f"{data_src}/incorrect_config.cfg"])
    assert result.exit_code == 1
    assert "Config file does not exist" in result.stdout


def test_DD():
    # correct config
    result = runner.invoke(app, ["--config", f"{data_src}/intents.cfg", "--test"])
    assert result.exit_code == 0
    assert f"Creating DD intents using {Path(data_src, 'intents.cfg').resolve()}\nbuild complete" in result.stdout

    # clean up intents directory
    intent_path: Path = Path(data_src, "intents")
    if intent_path.exists():
        shutil.rmtree(intent_path)
