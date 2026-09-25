"""Validate project structure and configuration files.

This module provides validation for the directory structure, phrase files,
and configuration files before processing. Checks for required language directories
and reports on missing components with visual feedback.
"""

import csv
from pathlib import Path

from rich import print
from rich.table import Table

from intentional_py import constants, exceptions, utils


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

    with config.open(mode="r", encoding="utf-8", newline="") as config_file:
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
            phrase_file = phrase_path / f"{action.removesuffix('^')}.txt"
            if mode == "NL":
                phrase_file = phrase_path / "NL" / f"{action.removesuffix('^')}.txt"
            if not phrase_file.exists():
                warnings.append(
                    f"Row {row_number}: phrase file '{phrase_file}' was not found; "
                    "the intent will be generated without those phrases."
                )

        normalized_rows.append(normalized_row)

    return normalized_rows, fatal_errors, warnings


def validate(config: Path, quiet: bool, test: bool) -> None:
    """Validates the directories and files for the project.

    Args:
        config (Path): config file to use for validation
        quiet (bool): minimize output, only alerting for issues if found
    """
    grid = Table.grid(expand=False)
    grid.add_column(ratio=1, no_wrap=True)
    grid.add_column(ratio=1, no_wrap=True, justify="center")

    print("[yellow]Validating directories and files[/yellow]\n") if not quiet else None

    # check for directory structure
    # set phrase file path
    phrase_path: Path

    (phrase_path, _, _) = utils.check_for_path(config)
    # this may have changed, especially for testing, but we want to keep the
    # phrase file in the same directory we're running this from
    if test:
        phrase_path = Path(phrase_path, constants.DEFAULT_TRAINING_PHRASES_DIR)
    else:
        phrase_path = Path(Path.cwd(), constants.DEFAULT_TRAINING_PHRASES_DIR)

    column1: str = f"{constants.DEFAULT_TRAINING_PHRASES_DIR} path"
    test_path: Path
    if not phrase_path.exists():
        grid.add_row(column1, " [red]:x:[/red]")
    else:
        grid.add_row(column1, " [green]:heavy_check_mark:[/green]")
        # English
        test_path = Path(phrase_path, "en")
        column1 = "English path"
        if not test_path.exists():
            grid.add_row(column1, " [red]:x:[/red]")
        else:
            grid.add_row(column1, " [green]:heavy_check_mark:[/green]")
            test_path = Path(test_path, "NL")
            column1 = "English NL path"
            if not test_path.exists():
                grid.add_row(column1, " [red]:x:[/red]")
            else:
                grid.add_row(column1, " [green]:heavy_check_mark:[/green]")
        # Spanish
        test_path = Path(phrase_path, "es")
        column1 = "Spanish path"
        if not test_path.exists():
            grid.add_row(column1, " [red]:x:[/red]")
        else:
            grid.add_row(column1, " [green]:heavy_check_mark:[/green]")
            test_path = Path(test_path, "NL")
            column1 = "Spanish NL path"
            if not test_path.exists():
                grid.add_row(column1, " [red]:x:[/red]")
            else:
                grid.add_row(column1, " [green]:heavy_check_mark:[/green]")
        # French
        test_path = Path(phrase_path, "fr")
        column1 = "French path"
        if not test_path.exists():
            grid.add_row(column1, " [red]:x:[/red]")
        else:
            grid.add_row(column1, " [green]:heavy_check_mark:[/green]")
            test_path = Path(test_path, "NL")
            print("French NL path ... ", end="")
            column1 = "French NL path"
            if not test_path.exists():
                grid.add_row(column1, " [red]:x:[/red]")
            else:
                grid.add_row(column1, " [green]:heavy_check_mark:[/green]")

    if not test and not quiet:
        print(grid)

    grid2 = Table.grid(expand=False)
    grid2.add_column(ratio=1, no_wrap=True)
    grid2.add_column(ratio=1, no_wrap=True, justify="center")

    errors = Table.grid(expand=False)
    errors.add_column(ratio=1, no_wrap=True)
    errors.add_column(ratio=1, no_wrap=True, justify="center")
    error_column1 = "." * 5 + " "

    final_grid = Table.grid(expand=False)
    final_grid.add_column(ratio=1, no_wrap=True)
    final_grid.add_column(ratio=1, no_wrap=True, justify="center")

    config_list: list = []
    if not config.is_file():
        # check both standard config files
        if not test and not quiet:
            print("Using [purple]STANDARD[/purple] config files")
        config_list.extend(
            [Path(Path.cwd(), "intents.cfg"), Path(Path.cwd(), "intents_nl.cfg")]
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
        if file_path.exists():
            grid2.add_row(column1, " [green]:heavy_check_mark:[/green]")

            # read config files if they exist
            issues_found: bool = False
            with Path(file_path, file).open(mode="r", encoding="utf-8") as config_file:
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
                        phrase_file: str = f"{action}.txt"
                        # set phrase file path
                        phrase_file_path: Path = Path(
                            Path.cwd(), constants.DEFAULT_TRAINING_PHRASES_DIR, language
                        )
                        test_path = Path(phrase_file_path, phrase_file)
                        if not test_path.exists():
                            # check for it in NL path
                            phrase_file_path = Path(phrase_file_path, "NL")
                            test_path = Path(phrase_file_path, phrase_file)
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

                if issues_found:
                    final_grid.add_row(
                        column1,
                        " [red]:x:[/red]",
                    )
                    if not quiet:
                        for error in error_list:
                            final_grid.add_row(f"{error_column1}{error}", "")
                    error_list = []
                else:
                    final_grid.add_row(
                        column1,
                        " [green]:heavy_check_mark:[/green]",
                    )

        else:
            grid2.add_row(column1, " [red]:x:[/red]")

    if test:
        print("validation complete")
    else:
        print(grid2) if not quiet else None
        print(errors) if not quiet else None
        print(final_grid)
