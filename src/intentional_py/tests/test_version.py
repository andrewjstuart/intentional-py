from typer.testing import CliRunner

from intentional_py import __version__, intentional

runner = CliRunner()

app = intentional.app


# generic test to make sure it runs
def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"intentional-cli version {__version__}" in result.stdout
