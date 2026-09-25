import csv
from pathlib import Path

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


class NullReporter:
    def message(self, level, text):
        pass


def test_validate_matches_build_rules(tmp_path: Path) -> None:
    nl_dir = tmp_path / "Training Phrases" / "en" / "NL"
    nl_dir.mkdir(parents=True)
    (nl_dir / "HELLO.txt").write_text("hello\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"
    with config.open("w", newline="", encoding="utf-8") as config_file:
        writer = csv.writer(config_file)
        writer.writerow(["RTL.Hello", "GetIntent", "EN", "HELLO", "", "", "TRUE"])
        writer.writerow(["RTL.Bad-Name", "Get.Intent", "en", "missing", "", "", "TRUE"])

    check = validate.validate(config, tmp_path, NullReporter()).configs[0]

    assert not check.ok
    assert check.details == [
        "Error: Row 2: intent name 'RTL.Bad-Name' cannot contain '-'.",
        "Warning: Row 2: context 'Get.Intent' contains '.'.",
        "Warning: Row 2: phrase file "
        f"'{tmp_path / 'Training Phrases' / 'en' / 'missing.txt'}' was not found; "
        "the intent will be generated without those phrases.",
    ]


def test_validate_reports_empty_and_missing_configs(tmp_path: Path) -> None:
    (tmp_path / "intents.cfg").write_text("", encoding="utf-8")

    result = validate.validate(Path(), tmp_path, NullReporter())

    assert result.used_standard_configs
    assert [(c.label, c.ok) for c in result.config_files] == [
        ("Checking for intents.cfg", True),
        ("Checking for intents_nl.cfg", False),
    ]
    assert result.configs[0].details == ["Error: The config file does not contain data."]
