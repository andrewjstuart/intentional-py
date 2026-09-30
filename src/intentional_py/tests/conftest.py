import csv
import os
import shutil
from pathlib import Path

import pytest

from intentional_py import validate

# Rich wraps at 80 columns when not attached to a terminal, which splits asserted messages.
os.environ["COLUMNS"] = "200"


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    """A copy of tests/data, shared because the NL tests use the phrases extracted earlier."""
    target = tmp_path_factory.mktemp("data")
    shutil.copytree(Path(__file__).parent / "data", target, dirs_exist_ok=True)
    return target


class FakeReporter:
    """A Reporter that records what it's given instead of printing or showing anything;
    shared by every test file instead of each defining its own (previously duplicated as
    FakeReporter in test_core_api.py and QuietReporter in test_features.py).
    """

    def __init__(self, answer: bool = True) -> None:
        self.answer = answer
        self.messages: list[tuple[str, str]] = []
        self.tables: list[list[str]] = []
        self.questions: list[str] = []
        self.question_details: list[list[str]] = []

    def message(self, level, text):
        self.messages.append((level, text))

    def table(self, columns, rows, level="info", title=""):
        self.tables.append(columns)

    def track(self, items, label):
        yield from items

    def confirm(self, question, details=None):
        self.questions.append(question)
        self.question_details.append(list(details or []))
        return self.answer


def write_config(path: Path, row: list[str]) -> None:
    """Write a single config row, quoted correctly by the csv module."""
    with path.open("w", newline="", encoding="utf-8") as config_file:
        csv.writer(config_file).writerow(row)


def dd_project(base: Path, rows: list[str], phrases: dict[str, str]) -> Path:
    """A DD project: intents.cfg with the given raw rows, and one phrase file per entry."""
    phrase_dir = base / "Training Phrases" / "en"
    phrase_dir.mkdir(parents=True, exist_ok=True)
    for name, text in phrases.items():
        (phrase_dir / f"{name}.txt").write_text(text, encoding="utf-8")
    config = base / "intents.cfg"
    config.write_text("".join(f"{row}\n" for row in rows), encoding="utf-8")
    return config


def make_nl_phrases(base: Path) -> Path:
    """An NL project's phrase files, for building intents_nl.cfg from them."""
    nl_dir = base / "Training Phrases" / "en" / "NL"
    nl_dir.mkdir(parents=True)
    (nl_dir / "BILLING.txt").write_text("pay my bill\nhello\n", encoding="utf-8")
    (nl_dir / "GREETING.txt").write_text("hello\n", encoding="utf-8")
    return base / "intents_nl.cfg"


def warnings_for(config: Path) -> list[str]:
    return validate.preflight_config(config, config.parent, "DD")[2]


def pytest_collection_modifyitems(session, config, items):
    """Modifies test items in place to ensure test functions run in a given order"""
    function_order = [
        "test_version",
        "test_validate_exceptions",
        "test_validate",
        "test_extract_exceptions",
        "test_extract_XLSM",
        "test_extract_XLSB",
        "test_DD_exceptions",
        "test_DD",
        "test_NL_exceptions",
        "test_NL",
        "test_NL_reuse",
    ]
    # OR
    # function_order = ["test_one[1]", "test_two[2]"]
    function_mapping = {
        item: item.name.split("[")[0] if "]" not in function_order[0] else item.name
        for item in items
    }

    sorted_items = items.copy()
    for func_ in function_order:
        sorted_items = [it for it in sorted_items if function_mapping[it] != func_] + [
            it for it in sorted_items if function_mapping[it] == func_
        ]
    items[:] = sorted_items
