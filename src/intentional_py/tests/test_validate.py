from typer.testing import CliRunner
from intentional_py import intentional

runner = CliRunner()

app = intentional.app


# tests the validation functionality of intentional
def test_validate():

    # validate
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
