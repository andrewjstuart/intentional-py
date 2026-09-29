from pathlib import Path

from typer.testing import CliRunner

from intentional_py import intentional

runner = CliRunner()

app = intentional.app


def build_nl(config: Path, *options: str):
    return runner.invoke(
        app, ["natural-language", "--config", str(config), *options, "--test"]
    )


# tests the NL functionality of intentional
def test_NL_exceptions(data_dir: Path):
    result = build_nl(
        Path(data_dir, "empty_intents_nl.cfg"), "-v", "RTL", "-c", "GetIntent"
    )
    assert result.exit_code == 0


def test_NL(data_dir: Path):
    config = Path(data_dir, "intents_nl.cfg")
    result = build_nl(config, "-v", "RTL", "-c", "GetIntent")
    assert result.exit_code == 0
    assert "RTL.Nomatch,GetIntent,en,NOMATCH-NM" in config.read_text(encoding="utf-8")


def test_NL_reuse(data_dir: Path):
    result = build_nl(Path(data_dir, "intents_nl.cfg"), "--reuse")
    assert result.exit_code == 0
    assert Path(data_dir, "intents", "RTL.Nomatch.json").exists()
