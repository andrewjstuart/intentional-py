import os
import csv
from rich import print
from rich.table import Table
from rich import box
from intentional_py import utils as utils


def validate(config: str, quiet: bool) -> None:
    grid = Table.grid(expand=False)
    grid.add_column(ratio=1, no_wrap=True)
    grid.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    grid.add_column(ratio=1, no_wrap=True, justify="center")

    print(f"[yellow]Validating directories and files[/yellow]\n") if not quiet else None

    # check for directory structure
    # set phrase file path
    phrase_path = os.path.join(os.getcwd(), "Training Phrases")
    column1: str = "Training Phrases path"
    column2: str = " " + "." * 10 + " "
    if not os.path.exists(phrase_path):
        grid.add_row(column1, column2, "[red]:x:[/red]")
    else:
        grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
        # English
        test_path = os.path.join(phrase_path, "en")
        column1 = "English path"
        if not os.path.exists(test_path):
            grid.add_row(column1, column2, "[red]:x:[/red]")
        else:
            grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
            test_path = os.path.join(test_path, "NL")
            column1 = "English NL path"
            if not os.path.exists(test_path):
                grid.add_row(column1, column2, "[red]:x:[/red]")
            else:
                grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
        # Spanish
        test_path = os.path.join(phrase_path, "es")
        column1 = "Spanish path"
        if not os.path.exists(test_path):
            grid.add_row(column1, column2, "[red]:x:[/red]")
        else:
            grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
            test_path = os.path.join(test_path, "NL")
            column1 = "Spanish NL path"
            if not os.path.exists(test_path):
                grid.add_row(column1, column2, "[red]:x:[/red]")
            else:
                grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
        # French
        test_path = os.path.join(phrase_path, "fr")
        column1 = "French path"
        if not os.path.exists(test_path):
            grid.add_row(column1, column2, "[red]:x:[/red]")
        else:
            grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
            test_path = os.path.join(test_path, "NL")
            print(f"French NL path ... ", end="")
            column1 = "French NL path"
            if not os.path.exists(test_path):
                grid.add_row(column1, column2, "[red]:x:[/red]")
            else:
                grid.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
    print(grid) if not quiet else None

    grid2 = Table.grid(expand=False)
    grid2.add_column(ratio=1, no_wrap=True)
    grid2.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    grid2.add_column(ratio=1, no_wrap=True, justify="center")

    errors = Table.grid(expand=False)
    errors.add_column(ratio=1, no_wrap=True)
    errors.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    errors.add_column(ratio=1, no_wrap=True, justify="center")
    error_column1 = "." * 5 + " "

    final_grid = Table.grid(expand=False)
    final_grid.add_column(ratio=1, no_wrap=True)
    final_grid.add_column(ratio=1, no_wrap=True)  # for ellipsis separation
    final_grid.add_column(ratio=1, no_wrap=True, justify="center")

    config_list: list = []
    if not config:
        # check both standard config files
        print(f"Using [purple]STANDARD[/purple] config files") if not quiet else None
        config_list.extend(["intents.cfg", "intents_nl.cfg"])
    else:
        # check for this config file
        config_list.append(config)

    found_list: list = []
    # check if config files exist
    for file in config_list:
        file_path = os.path.join(os.getcwd(), file)
        column1 = f"Checking {file}"
        if os.path.exists(file_path):
            grid2.add_row(column1, column2, "[green]:heavy_check_mark:[/green]")
            found_list.append(file)
        else:
            grid2.add_row(column1, column2, "[red]:x:[/red]")

    if not found_list:
        print(grid2)
        exit()

    # read config files if they exist
    for files in found_list:
        issues_found: bool = False
        with open(files, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = [row for row in reader if any(row)]  # Filter out empty rows
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
                    # print(f"\t[red]No intent provided![/red]: {row}")
                    errors.add_row(
                        error_column1, f"[red]No intent provided![/red]: {row}", ""
                    )
                    issues_found = True
                if "-" in df_intent:
                    # print(f"\t[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]")
                    errors.add_row(
                        error_column1,
                        f"[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]",
                        "",
                    )
                    issues_found = True

                if not df_context:
                    # print(f"\t[red]No context provided![/red]: {row}")
                    errors.add_row(
                        error_column1, f"[red]No context provided![/red]: {row}", ""
                    )
                    issues_found = True
                if "." in df_context:
                    # print(f"\t[red]Incorrect context name:[/red] [blue]{df_context}[/blue]")
                    errors.add_row(
                        error_column1,
                        f"[red]Incorrect context name:[/red] [blue]{df_context}[/blue]",
                        "",
                    )
                    issues_found = True

                if language not in {"en", "es", "fr", "dtmf"}:
                    # print(f"\t[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue]")
                    errors.add_row(
                        error_column1,
                        f"[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue]",
                        "",
                    )
                    issues_found = True

                if not action:
                    # print(f"\t[red]No action provided![/red]: {row}")
                    errors.add_row(
                        error_column1, f"[red]No action provided![/red]: {row}", ""
                    )
                    issues_found = True

                if language != "dtmf" and action != "nomatch":
                    # check that action exists in language
                    phrase_file: str = f"{action}.txt"
                    # set phrase file path
                    phrase_file_path = os.path.join(
                        os.getcwd(), "Training Phrases", language
                    )
                    # phrase_file_path = (os.path.join(phrase_file_path, "NL") if mode == "NL" else phrase_file_path    )
                    test_path = os.path.join(phrase_file_path, phrase_file)
                    if not os.path.exists(test_path):
                        # check for it in NL path
                        phrase_file_path = os.path.join(phrase_file_path, "NL")
                        test_path = os.path.join(phrase_file_path, phrase_file)
                        if not os.path.exists(test_path):
                            # still not found
                            # print(f"\t[red]Phrase file not found:[/red] [purple]{action}[/purple]")
                            errors.add_row(
                                error_column1,
                                f"[red]Phrase file not found:[/red] [purple]{action}[/purple]",
                                "",
                            )
                            issues_found = True

                if dtmf_value:
                    dtmf_list = dtmf_value.split("|")
                    if not (
                        set(dtmf_list).issubset(
                            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "#", "*"]
                        )
                    ):
                        # print(f"\t[red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]")
                        errors.add_row(
                            error_column1,
                            f"[red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]",
                            "",
                        )
                        issues_found = True

                if machine_learning and machine_learning.lower() not in {
                    "true",
                    "false",
                }:
                    # print(f"\tMachine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}")
                    errors.add_row(
                        error_column1,
                        f"Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}",
                        "",
                    )
                    issues_found = True
            # print(f"Validating {files} ... ", end="")
            column1 = f"Validating {files}"

            if issues_found:
                # print(f"[red][bold]FAIL[/bold][/red]")
                final_grid.add_row(
                    column1,
                    column2,
                    f"[red]:x:[/red]",
                )
            else:
                # print(f"[green]SUCCESS[/green]")
                final_grid.add_row(
                    column1,
                    column2,
                    f"[green]:heavy_check_mark:[/green]",
                )

    print(grid2) if not quiet else None
    print(errors) if not quiet else None
    print(final_grid)
