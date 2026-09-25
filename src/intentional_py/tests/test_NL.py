import shutil
from pathlib import Path

from typer.testing import CliRunner

from intentional_py import intentional

runner = CliRunner()

app = intentional.app
data_src: str = "./src/intentional_py/tests/data"


# tests the NL functionality of intentional
def test_NL_exceptions():
    result = runner.invoke(
        app,
        [
            "natural-language",
            "--config",
            f"{data_src}/empty_intents_nl.cfg",
            "-v",
            "RTL",
            "-c",
            "GetIntent",
            "--test",
        ],
    )
    assert result.exit_code == 0


def test_NL():
    result = runner.invoke(
        app,
        [
            "natural-language",
            "--config",
            f"{data_src}/intents_nl.cfg",
            "-v",
            "RTL",
            "-c",
            "GetIntent",
            "--test",
        ],
    )
    assert result.exit_code == 0


def test_NL_reuse():
    result = runner.invoke(
        app,
        [
            "natural-language",
            "--config",
            f"{data_src}/intents_nl.cfg",
            "--reuse",
            "--test",
        ],
    )
    assert result.exit_code == 0

    # clean up Training Phrase directory
    training_phrase_path: Path = Path(data_src, "Training Phrases")
    if training_phrase_path.exists():
        shutil.rmtree(training_phrase_path)

    # clean up intents directory
    intent_path: Path = Path(data_src, "intents")
    if intent_path.exists():
        shutil.rmtree(intent_path)
