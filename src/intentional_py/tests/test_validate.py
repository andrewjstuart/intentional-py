from pathlib import Path

from typer.testing import CliRunner

from intentional_py import intentional

runner = CliRunner()

app = intentional.app
data_src: str = "./src/intentional_py/tests/data"


# tests the validation functionality of intentional
def test_validate_exceptions():
    config: Path = Path(f"{data_src}/test_intents.cfg")
    result = runner.invoke(app, ["validate", "--config", f"{config}", "--test"])
    assert result.exit_code == 0
    assert "Validating directories and files" + "\n\nvalidation complete\n" in result.stdout


def test_validate():
    # validate
    result = runner.invoke(app, ["validate", "--test"])
    assert result.exit_code == 0
    assert "Validating directories and files" + "\n\nvalidation complete\n" in result.stdout
