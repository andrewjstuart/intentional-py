"""Validate project structure and configuration files.

This module provides validation for the directory structure, phrase files,
and configuration files before processing. Checks for required language directories
and reports on missing components with visual feedback.
"""

import csv
from pathlib import Path

from intentional_py import constants, utils
from intentional_py.reporting import Check, Reporter, ValidateResult


def preflight_config(
    config: Path, base_path: Path, mode: str | None
) -> tuple[list[list[str]], list[str], list[str]]:
    """Validate and normalize config rows before a build starts.

    Missing required values and malformed rows are fatal. Values that the
    builder can safely default are normalized and returned as warnings.
    With mode None, phrase files may be in either the DD or the NL folder.
    """
    fatal_errors: list[str] = []
    warnings: list[str] = []
    normalized_rows: list[list[str]] = []

    with utils.file_errors(config), config.open(
        mode="r", encoding="utf-8", newline=""
    ) as config_file:
        rows = [row for row in csv.reader(config_file) if any(cell.strip() for cell in row)]

    for row_number, row in enumerate(rows, start=1):
        if len(row) != 7:
            fatal_errors.append(
                f"Row {row_number}: expected 7 values, found {len(row)}."
            )
            continue

        normalized_row = [cell.strip() for cell in row]
        intent, context, language, action, _, dtmf_value, machine_learning = normalized_row

        if not intent:
            fatal_errors.append(f"Row {row_number}: intent name is required.")
        elif "-" in intent:
            fatal_errors.append(
                f"Row {row_number}: intent name '{intent}' cannot contain '-'."
            )

        if not context:
            fatal_errors.append(f"Row {row_number}: context is required.")
        elif "." in context:
            warnings.append(
                f"Row {row_number}: context '{context}' contains '.'."
            )

        if not action:
            fatal_errors.append(f"Row {row_number}: action is required.")

        language = language.lower()
        if language not in constants.VALID_LANGUAGES | {"dtmf"}:
            warnings.append(
                f"Row {row_number}: language '{language or '<blank>'}' "
                f"will default to '{constants.DEFAULT_LANGUAGE}'."
            )
            language = constants.DEFAULT_LANGUAGE
            normalized_row[2] = constants.DEFAULT_LANGUAGE

        if language == "dtmf" and not dtmf_value:
            fatal_errors.append(f"Row {row_number}: DTMF rows require a DTMF value.")

        if dtmf_value:
            dtmf_values = dtmf_value.split("|")
            invalid_dtmf = set(dtmf_values) - constants.VALID_DTMF_VALUES
            if invalid_dtmf:
                warnings.append(
                    f"Row {row_number}: invalid DTMF values {sorted(invalid_dtmf)} "
                    "will be retained for compatibility."
                )

        if not machine_learning:
            normalized_row[6] = constants.MACHINE_LEARNING_DEFAULT
            warnings.append(
                f"Row {row_number}: machine learning will default to "
                f"'{constants.MACHINE_LEARNING_DEFAULT}'."
            )
        elif machine_learning.lower() not in constants.VALID_ML_VALUES:
            normalized_row[6] = constants.MACHINE_LEARNING_DEFAULT
            warnings.append(
                f"Row {row_number}: machine learning value '{machine_learning}' "
                f"will default to '{constants.MACHINE_LEARNING_DEFAULT}'."
            )
        else:
            normalized_row[6] = machine_learning.lower()

        if action and language != "dtmf" and action != "nomatch":
            phrase_path = base_path / constants.DEFAULT_TRAINING_PHRASES_DIR / language
            phrase_dirs = {"DD": [phrase_path], "NL": [phrase_path / "NL"]}.get(
                mode, [phrase_path, phrase_path / "NL"]
            )
            phrase_files = [utils.find_phrase_file(path, action) for path in phrase_dirs]
            if not any(phrase_file.exists() for phrase_file in phrase_files):
                warnings.append(
                    f"Row {row_number}: phrase file '{phrase_files[0]}' was not found; "
                    "the intent will be generated without those phrases."
                )

        normalized_rows.append(normalized_row)

    return normalized_rows, fatal_errors, warnings


def validate(config: Path, base_dir: Path, reporter: Reporter) -> ValidateResult:
    """Validates the directories and files for the project.

    Args:
        config (Path): config file to use for validation; the standard config files are used if it does not exist
        base_dir (Path): Project directory containing the training phrases and standard config files.
        reporter (Reporter): Receives messages.
    """
    result = ValidateResult()
    reporter.message("info", "[yellow]Validating directories and files[/yellow]\n")

    # check for directory structure
    phrase_path = Path(base_dir, constants.DEFAULT_TRAINING_PHRASES_DIR)
    phrases_exist = phrase_path.exists()
    result.directories.append(
        Check(f"{constants.DEFAULT_TRAINING_PHRASES_DIR} path", phrases_exist)
    )
    if phrases_exist:
        for code, name in constants.LANGUAGE_NAMES.items():
            lang_path = Path(phrase_path, code)
            lang_exists = lang_path.exists()
            result.directories.append(Check(f"{name} path", lang_exists))
            if lang_exists:
                result.directories.append(
                    Check(f"{name} NL path", Path(lang_path, "NL").exists())
                )

    config_list: list = []
    if not config.is_file():
        # check both standard config files
        result.used_standard_configs = True
        config_list.extend(
            [
                Path(base_dir, constants.DEFAULT_DD_CONFIG),
                Path(base_dir, constants.DEFAULT_NL_CONFIG),
            ]
        )
    else:
        # check for this config file
        config_list.append(config)

    # check if config files exist
    for file in config_list:
        if not file.is_file():
            result.config_files.append(Check(f"Checking for {file.name}", False))
            continue
        result.config_files.append(Check(f"Checking for {file.name}", True))

        # the same checks a build runs, so validate reports exactly what a build would
        rows, errors, warnings = preflight_config(file, base_dir, None)
        if not rows and not errors:
            errors = ["The config file does not contain data."]
        details = [f"Error: {error}" for error in errors]
        details += [f"Warning: {warning}" for warning in warnings]
        result.configs.append(Check(f"Validating {file.name}", not errors, details))

    return result
