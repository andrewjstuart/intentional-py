import csv
from pathlib import Path

import pytest

from intentional_py import validate


def write_config(path: Path, row: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as config_file:
        csv.writer(config_file).writerow(row)


def test_preflight_normalizes_defaultable_values(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    write_config(config, ["welcome", "GetIntent", "", "welcome", "", "", "maybe"])

    rows, fatal_errors, warnings = validate.preflight_config(config, tmp_path, "DD")

    assert fatal_errors == []
    assert rows == [["welcome", "GetIntent", "en", "welcome", "", "", "TRUE"]]
    assert any("language" in warning for warning in warnings)
    assert any("machine learning" in warning for warning in warnings)
    assert any("phrase file" in warning for warning in warnings)


def test_preflight_rejects_malformed_rows_before_build(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    write_config(config, ["welcome", "GetIntent", "en"])

    rows, fatal_errors, warnings = validate.preflight_config(config, tmp_path, "DD")

    assert rows == []
    assert warnings == []
    assert fatal_errors == ["Row 1: expected 7 values, found 3."]


def test_preflight_requires_dtmf_value(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    write_config(config, ["menu", "GetIntent", "dtmf", "menu", "", "", "TRUE"])

    _, fatal_errors, _ = validate.preflight_config(config, tmp_path, "DD")

    assert fatal_errors == ["Row 1: DTMF rows require a DTMF value."]
