import csv
from pathlib import Path

from intentional_py import validate
from intentional_py.models import ProjectLayout
from intentional_py.tests.conftest import write_config


def test_preflight_normalizes_defaultable_values(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    write_config(config, ["welcome", "GetIntent", "", "welcome", "", "", "maybe"])

    rows, fatal_errors, warnings, _removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert fatal_errors == []
    assert rows == [["welcome", "GetIntent", "en", "welcome", "", "", "TRUE"]]
    assert any("language" in warning for warning in warnings)
    assert any("machine learning" in warning for warning in warnings)
    assert any("phrase file" in warning for warning in warnings)


def test_preflight_rejects_malformed_rows_before_build(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    write_config(config, ["welcome", "GetIntent", "en"])

    rows, fatal_errors, warnings, _removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert rows == []
    assert warnings == []
    assert fatal_errors == ["Row 1: expected 6 or 7 values, found 3."]


def test_preflight_rejects_a_path_traversal_intent_name(tmp_path: Path) -> None:
    # the intent name becomes a file name; this is a safety rule, not a relaxable
    # naming convention, so it's caught here before a build ever writes a file
    config = tmp_path / "intents.cfg"
    write_config(config, ["../../evil", "GetIntent", "en", "welcome", "", "", ""])

    _, fatal_errors, _, _removals = validate.preflight_config(config, tmp_path, "DD")

    assert fatal_errors == [
        "Row 1: intent name '../../evil' cannot contain '/' or '\\'."
    ]


def test_machine_learning_column_is_optional(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    # no ML column, a blank one, and an explicit FALSE
    config.write_text(
        "A.One,Ctx,en,one,,1\nA.Two,Ctx,en,two,,2,\nA.Three,Ctx,en,three,,3,FALSE\n",
        encoding="utf-8",
    )

    rows, fatal_errors, warnings, _removals = validate.preflight_config(
        config, tmp_path, "DD"
    )

    assert fatal_errors == []
    assert [row[6] for row in rows] == ["TRUE", "TRUE", "false"]
    assert not any("machine learning" in warning for warning in warnings)


def test_preflight_requires_dtmf_value(tmp_path: Path) -> None:
    config = tmp_path / "intents.cfg"
    write_config(config, ["menu", "GetIntent", "dtmf", "menu", "", "", "TRUE"])

    _, fatal_errors, _, _removals = validate.preflight_config(config, tmp_path, "DD")

    assert fatal_errors == ["Row 1: DTMF rows require a DTMF value."]


def test_preflight_finds_phrase_files_in_a_custom_layout(tmp_path: Path) -> None:
    layout = ProjectLayout(training_phrases_dir="Phrases")
    phrase_dir = tmp_path / "Phrases" / "en"
    phrase_dir.mkdir(parents=True)
    (phrase_dir / "welcome.txt").write_text("hello\n", encoding="utf-8")
    config = tmp_path / "intents.cfg"
    write_config(config, ["welcome", "GetIntent", "en", "welcome", "", "", "TRUE"])

    _, fatal_errors, warnings, _removals = validate.preflight_config(
        config, tmp_path, "DD", layout=layout
    )

    assert fatal_errors == []
    assert not any("phrase file" in warning for warning in warnings)


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
        (
            "Warning: Row 2: phrase file "
            f"'{tmp_path / 'Training Phrases' / 'en' / 'missing.txt'}' was not found; "
            "the intent will be generated without those phrases."
        ),
    ]


def test_validate_reports_empty_and_missing_configs(tmp_path: Path) -> None:
    (tmp_path / "intents.cfg").write_text("", encoding="utf-8")

    result = validate.validate(Path(), tmp_path, NullReporter())

    assert result.used_standard_configs
    assert [(c.label, c.ok) for c in result.config_files] == [
        ("Checking for intents.cfg", True),
        ("Checking for intents_nl.cfg", False),
    ]
    assert result.configs[0].details == [
        "Error: The config file does not contain data."
    ]


def test_validate_only_checks_languages_used_in_the_config(tmp_path: Path) -> None:
    # Spanish and French are supported (the default set), but this config only uses
    # English, so there's nothing to check for the other two yet
    (tmp_path / "Training Phrases" / "en").mkdir(parents=True)
    config = tmp_path / "intents.cfg"
    write_config(config, ["A.Pay", "Ctx", "en", "pay", "", "", "TRUE"])

    result = validate.validate(config, tmp_path, NullReporter())

    labels = [c.label for c in result.directories]
    assert "English path" in labels
    assert "Spanish path" not in labels
    assert "French path" not in labels
