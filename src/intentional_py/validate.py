"""Validate project structure and configuration files.

This module provides validation for the directory structure, phrase files,
and configuration files before processing. Checks for required language directories
and reports on missing components with visual feedback.
"""

import csv
from pathlib import Path

from intentional_py import constants, exceptions, utils
from intentional_py.reporting import Check, Reporter, ValidateResult


def preflight_config(
    config: Path, base_path: Path, mode: str
) -> tuple[list[list[str]], list[str], list[str]]:
    """Validate and normalize config rows before a build starts.

    Missing required values and malformed rows are fatal. Values that the
    builder can safely default are normalized and returned as warnings.
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
            if mode == "NL":
                phrase_path = phrase_path / "NL"
            phrase_file = utils.find_phrase_file(phrase_path, action)
            if not phrase_file.exists():
                warnings.append(
                    f"Row {row_number}: phrase file '{phrase_file}' was not found; "
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
    error_list: list = []
    for file in config_list:
        file_path: Path
        (file_path, file, _) = utils.check_for_path(file)

        column1 = f"Checking for {file.name}"
        if Path(file_path, file).is_file():
            result.config_files.append(Check(column1, True))

            # read config files if they exist
            issues_found: bool = False
            config_path = Path(file_path, file)
            with utils.file_errors(config_path), config_path.open(
                mode="r", encoding="utf-8"
            ) as config_file:
                reader = csv.reader(config_file)
                rows = [row for row in reader if any(row)]  # Filter out empty rows
                if len(rows) == 0:
                    error_list.append("[red]No data![/red]")
                    issues_found = True
                for row_number, row in enumerate(rows, start=1):
                    if len(row) != 7:
                        raise exceptions.ValidationError(
                            f"{file.name}, row {row_number}: expected 7 values, "
                            f"found {len(row)}."
                        )
                    # annotations for variables
                    df_intent: str
                    df_context: str
                    language: str
                    action: str
                    dtmf_value: str
                    machine_learning: str
                    (
                        df_intent,
                        df_context,
                        language,
                        action,
                        _,  # df_entity not validated
                        dtmf_value,
                        machine_learning,
                    ) = row

                    # validate values of config file
                    if not df_intent:
                        error_list.append(f"[red]No intent provided![/red]: {row}")
                        issues_found = True
                    if "-" in df_intent:
                        error_list.append(
                            f"[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]"
                        )
                        issues_found = True

                    if not df_context:
                        error_list.append(f"[red]No context provided![/red]: {row}")
                        issues_found = True
                    if "." in df_context:
                        error_list.append(
                            f"[red]Incorrect context name:[/red] [blue]{df_context}[/blue]"
                        )
                        issues_found = True

                    if language not in (constants.VALID_LANGUAGES | {"dtmf"}):
                        error_list.append(
                            f"[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue]"
                        )
                        issues_found = True

                    if not action:
                        error_list.append(f"[red]No action provided![/red]: {row}")
                        issues_found = True

                    if language != "dtmf" and action != "nomatch":
                        # check that action exists in language
                        phrase_file_path: Path = Path(
                            base_dir, constants.DEFAULT_TRAINING_PHRASES_DIR, language
                        )
                        test_path = utils.find_phrase_file(phrase_file_path, action)
                        if not test_path.exists():
                            # check for it in NL path
                            phrase_file_path = Path(phrase_file_path, "NL")
                            test_path = utils.find_phrase_file(phrase_file_path, action)
                            if not test_path.exists():
                                # still not found
                                error_list.append(
                                    f"[red]Phrase file not found:[/red] [yellow]{language} {action}[/yellow]"
                                )
                                issues_found = True

                    if dtmf_value:
                        dtmf_list = dtmf_value.split("|")
                        if not (set(dtmf_list).issubset(constants.VALID_DTMF_VALUES)):
                            error_list.append(
                                f"[red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]"
                            )
                            issues_found = True

                    if machine_learning and machine_learning.lower() not in {
                        "true",
                        "false",
                    }:
                        error_list.append(
                            f"Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}"
                        )
                        issues_found = True
                column1 = f"Validating {file.name}"
                result.configs.append(Check(column1, not issues_found, error_list))
                error_list = []

        else:
            result.config_files.append(Check(column1, False))

    return result
