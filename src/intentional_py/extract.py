import shutil
import pyxlsb
import openpyxl
import datetime
import sys
from pathlib import Path
from rich import print
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
from time import perf_counter
from intentional_py import utils as utils


def excel_data(
    xl_file: Path, mode: str, language: str, quiet: bool, test: bool
) -> None:
    t1_start = perf_counter()

    xl_file_path: Path
    file_extension: str

    (xl_file_path, xl_file, file_extension) = utils.check_for_path(xl_file)
    # this may have changed, especially for testing, but we want to keep the
    # phrase file in the same directory we're running this from
    default_path: Path = Path.cwd() if not test else xl_file_path

    if file_extension not in [".xlsb", ".xlsm", ".xlsx"]:
        print(f"Extension {file_extension} is not a valid EXCEL extension supported.")
        sys.exit(1)

    # setup progress bars
    # Define custom progress bar
    if test:
        progress_bar = Progress(TextColumn(f"Processing [green]{xl_file}[/green]"))
    else:
        progress_bar = Progress(
            TextColumn(
                f"Processing [green]{xl_file}[/green]:"
                + " [progress.percentage]{task.percentage:>3.0f}%\n"
            ),
            BarColumn(bar_width=15),
            MofNCompleteColumn(),
            # TextColumn("•"),
            TextColumn("|"),
            # TimeElapsedColumn(),
            TimeRemainingColumn(elapsed_when_finished=True),
            # TextColumn("|"),
            # TimeRemainingColumn(),
        )

    # set up path to save files
    # set phrase file path
    phrase_file_path: Path = Path(default_path, "Training Phrases", language)
    phrase_file_path = (
        Path(phrase_file_path, "NL") if mode == "NL" else phrase_file_path
    )

    # zip existing file if it already exists, so nothing is overwritten
    if phrase_file_path.exists():
        zip_file_name: str = phrase_file_path.name
        now = datetime.datetime.now()
        formatted_datetime = now.strftime("%Y-%m-%d_%H%M%S")
        zip_file_name = f"{zip_file_name}_{formatted_datetime}"
        zip_save_location: Path = phrase_file_path.parent
        zip_file_path: Path = Path(zip_save_location, f"{zip_file_name}.zip")
        print("[green]Zip existing directory[/green]") if not quiet else None
        utils.zip_directory(phrase_file_path, zip_file_path)
        shutil.rmtree(str(phrase_file_path))
    # create the directory, which may have just been removed, or doesn't exist
    phrase_file_path.mkdir(parents=True, exist_ok=True)

    print(f"Exporting data to: [blue]{phrase_file_path}[/blue]") if not quiet else None

    # read XL file, check if xlsb or xlsm
    with progress_bar as p:
        phrase_dict: dict = {}
        phrase_file: Path
        xl = Path(xl_file_path, xl_file)
        if file_extension == ".xlsb":
            # uses pyxlsb
            with pyxlsb.open_workbook(xl) as wb:
                for sheet in p.track(wb.sheets):
                    phrases: set = set()
                    for row in wb.get_sheet(sheet).rows():
                        for cell in row:
                            # add the phrases to a set to remove duplicates
                            phrases.add(cell.v)

                        # convert to a list to sort them
                        phrase_list: list = list(phrases)
                        phrase_list = sorted(phrase_list)
                        # print the list
                        phrase_file = Path(phrase_file_path, f"{sheet}.txt")
                        # add to dictionary
                        phrase_dict[phrase_file] = phrase_list
        elif file_extension in [".xlsm", ".xlsx"]:
            # uses openpyxl
            wb = openpyxl.load_workbook(xl)
            sheets: list = wb.sheetnames
            for sheet_name in p.track(sheets):
                phrases: set = set()
                sheet = wb[sheet_name]
                for row in sheet.iter_rows(values_only=True):
                    # add the phrases to a set to remove duplicates
                    phrases.add(row)
                # convert to a list to sort them
                phrase_list: list = list(phrases)
                phrase_list = sorted(phrase_list)
                # print the list
                phrase_file = Path(phrase_file_path, f"{sheet_name}.txt")
                phrase_dict[phrase_file] = phrase_list
        else:
            print(f"[red]File not supported[/red]: {xl_file}")
            sys.exit(1)

        # print the rows from the dictionary
        file_cnt: int = 0
        phrases_cnt: int = 0
        for phrase_file, phrases in phrase_dict.items():
            file_cnt += 1
            # with open(phrase_file, mode="w", encoding="utf-8") as f:
            with phrase_file.open(mode="w", encoding="utf-8") as f:
                for line in phrases:
                    phrases_cnt += 1
                    f.write(f"{"".join(line)}\n")

    t1_stop = perf_counter()
    time = f"{t1_stop - t1_start:.3f} s"
    table = Table(
        "Time",
        "Files",
        "Phrases",
        title="",
        box=box.ROUNDED,
    )
    table.add_row(
        time,
        str(file_cnt),
        str(phrases_cnt),
    )
    if test:
        print("extract complete")
    else:
        console = Console()
        console.print(table) if not quiet else None
