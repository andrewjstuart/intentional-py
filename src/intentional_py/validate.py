import csv
from pathlib import Path
from rich import print
from rich.table import Table
from intentional_py import utils as utils


def validate(config: Path, quiet: bool) -> None:
    """Validates the directories and files for the project.

    Args:
        config (Path): config file to use for validation
        quiet (bool): minimize output, only alerting for issues if found
    """
    grid = Table.grid(expand=False)
    grid.add_column(ratio=1, no_wrap=True)
    # grid.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    grid.add_column(ratio=1, no_wrap=True, justify="center")

    print("[yellow]Validating directories and files[/yellow]\n") if not quiet else None

    # check for directory structure
    # set phrase file path
    phrase_path: Path = Path(Path.cwd(), "Training Phrases")
    column1: str = "Training Phrases path"
    # column2: str = " " + "." * 10 + " "
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
    print(grid) if not quiet else None

    grid2 = Table.grid(expand=False)
    grid2.add_column(ratio=1, no_wrap=True)
    # grid2.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    grid2.add_column(ratio=1, no_wrap=True, justify="center")

    errors = Table.grid(expand=False)
    errors.add_column(ratio=1, no_wrap=True)
    # errors.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    errors.add_column(ratio=1, no_wrap=True, justify="center")
    error_column1 = "." * 5 + " "

    final_grid = Table.grid(expand=False)
    final_grid.add_column(ratio=1, no_wrap=True)
    # final_grid.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    final_grid.add_column(ratio=1, no_wrap=True, justify="center")

    config_list: list = []
    if not config.is_file():
        # check both standard config files
        print("Using [purple]STANDARD[/purple] config files") if not quiet else None
        config_list.extend(
            [Path(Path.cwd(), "intents.cfg"), Path(Path.cwd(), "intents_nl.cfg")]
        )
    else:
        # check for this config file
        config_list.append(config)

    # check if config files exist
    error_list: list = []
    for file in config_list:
        file_path = Path(Path.cwd(), file)
        column1 = f"Checking for {file.name}"
        if file_path.exists():
            grid2.add_row(column1, " [green]:heavy_check_mark:[/green]")

            # read config files if they exist
            issues_found: bool = False
            with file_path.open(mode="r", encoding="utf-8") as config_file:
                reader = csv.reader(config_file)
                rows = [row for row in reader if any(row)]  # Filter out empty rows
                if len(rows) == 0:
                    # grid2.add_row(f"{error_column1}[red]No data![/red]", "", "")
                    error_list.append("[red]No data![/red]")
                    issues_found = True
                for row in rows:
                    # annotations for variables
                    df_intent: str
                    df_context: str
                    language: str
                    action: str
                    df_entity: str
                    dtmf_value: str
                    machine_learning: str
                    (
                        df_intent,
                        df_context,
                        language,
                        action,
                        df_entity,
                        dtmf_value,
                        machine_learning,
                    ) = row

                    # validate values of config file
                    if not df_intent:
                        # print(f" [red]No intent provided![/red]: {row}")
                        # grid2.add_row(error_column1, f"[red]No intent provided![/red]: {row}", "")
                        error_list.append(f"[red]No intent provided![/red]: {row}")
                        issues_found = True
                    if "-" in df_intent:
                        # print(f" [red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]")
                        # grid2.add_row(error_column1,f"[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]","",)
                        error_list.append(
                            f"[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]"
                        )
                        issues_found = True

                    if not df_context:
                        # print(f" [red]No context provided![/red]: {row}")
                        # grid2.add_row(error_column1, f"[red]No context provided![/red]: {row}", "")
                        error_list.append(f"[red]No context provided![/red]: {row}")
                        issues_found = True
                    if "." in df_context:
                        # print(f" [red]Incorrect context name:[/red] [blue]{df_context}[/blue]")
                        # grid2.add_row(error_column1,f"[red]Incorrect context name:[/red] [blue]{df_context}[/blue]","",)
                        error_list.append(
                            f"[red]Incorrect context name:[/red] [blue]{df_context}[/blue]"
                        )
                        issues_found = True

                    if language not in {"en", "es", "fr", "dtmf"}:
                        # print(f" [red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue]")
                        # grid2.add_row(error_column1,f"[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue]","",)
                        error_list.append(
                            f"[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue]"
                        )
                        issues_found = True

                    if not action:
                        # print(f" [red]No action provided![/red]: {row}")
                        # grid2.add_row(error_column1, f"[red]No action provided![/red]: {row}", "")
                        error_list.append(f"[red]No action provided![/red]: {row}")
                        issues_found = True

                    if language != "dtmf" and action != "nomatch":
                        # check that action exists in language
                        phrase_file: str = f"{action}.txt"
                        # set phrase file path
                        phrase_file_path: Path = Path(
                            Path.cwd(), "Training Phrases", language
                        )
                        # phrase_file_path = Path(phrase_file_path,"NL") if mode == "NL" else phrase_file_path    )
                        test_path = Path(phrase_file_path, phrase_file)
                        if not test_path.exists():
                            # check for it in NL path
                            phrase_file_path = Path(phrase_file_path, "NL")
                            test_path = Path(phrase_file_path, phrase_file)
                            if not test_path.exists():
                                # still not found
                                # grid2.add_row(error_column1,f"[red]Phrase file not found:[/red] [yellow]{language} {action}[/yellow]","",)
                                error_list.append(
                                    f"[red]Phrase file not found:[/red] [yellow]{language} {action}[/yellow]"
                                )
                                issues_found = True

                    if dtmf_value:
                        dtmf_list = dtmf_value.split("|")
                        if not (
                            set(dtmf_list).issubset(
                                [
                                    "1",
                                    "2",
                                    "3",
                                    "4",
                                    "5",
                                    "6",
                                    "7",
                                    "8",
                                    "9",
                                    "0",
                                    "#",
                                    "*",
                                ]
                            )
                        ):
                            # print(f" [red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]")
                            # grid2.add_row(error_column1,f"[red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]","",)
                            error_list.append(
                                f"[red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]"
                            )
                            issues_found = True

                    if machine_learning and machine_learning.lower() not in {
                        "true",
                        "false",
                    }:
                        # print(f"\t Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}")
                        # grid2.add_row(error_column1,f"Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}","",)
                        error_list.append(
                            f"Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}"
                        )
                        issues_found = True
                # print(f"Validating {files} ... ", end="")
                column1 = f"Validating {file.name}"

                if issues_found:
                    # print(f"[red][bold]FAIL[/bold][/red]")
                    final_grid.add_row(
                        column1,
                        " [red]:x:[/red]",
                    )
                    if not quiet:
                        for error in error_list:
                            final_grid.add_row(f"{error_column1}{error}", "")
                    error_list = []
                else:
                    # print(f"[green]SUCCESS[/green]")
                    final_grid.add_row(
                        column1,
                        " [green]:heavy_check_mark:[/green]",
                    )

        else:
            grid2.add_row(column1, " [red]:x:[/red]")

    print(grid2) if not quiet else None
    print(errors) if not quiet else None
    print(final_grid)
