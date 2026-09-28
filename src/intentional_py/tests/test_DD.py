from pathlib import Path

from typer.testing import CliRunner

from intentional_py import intentional

runner = CliRunner()

app = intentional.app


# tests the DD functionality of intentional
def test_DD_exceptions(data_dir: Path):
    # empty config
    result = runner.invoke(app, ["--config", str(Path(data_dir, "empty_intents.cfg"))])
    assert result.exit_code == 1
    assert "Config file does not contain data" in result.stdout

    # incorrect config, does not exist
    result = runner.invoke(app, ["--config", str(Path(data_dir, "incorrect_config.cfg"))])
    assert result.exit_code == 1
    assert "Config file does not exist" in result.stdout


def test_DD(data_dir: Path):
    config = Path(data_dir, "intents.cfg")
    result = runner.invoke(app, ["--config", str(config), "--test"])
    assert result.exit_code == 0
    assert f"Creating DD intents using {config.resolve()}\nbuild complete" in result.stdout
    assert Path(data_dir, "intents", "MYAC.NewServiceHomeOrBus.Home.json").exists()
