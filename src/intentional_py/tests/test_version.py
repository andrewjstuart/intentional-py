from typer.testing import CliRunner

from intentional_py import intentional

runner = CliRunner()

app = intentional.app


# generic test to make sure it runs
def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
