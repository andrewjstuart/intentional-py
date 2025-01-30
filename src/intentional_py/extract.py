import os
import shutil
import pyxlsb
import openpyxl
import datetime
from rich import print
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from time import perf_counter
from intentional_py import utils as utils


def excel_data(xl_file: str, mode: str, language: str, quiet: bool) -> None:
    t1_start = perf_counter()
    # xl_file = os.path.join(os.getcwd(), xl_file)
    # print(f"Adjusting file name: [green]{xl_file}[/green]") if not quiet else None
    xl_file_path: str = xl_file
    if os.path.dirname(xl_file):
        xl_file_path = os.path.dirname(xl_file)  # pull filepath from file
        file = os.path.basename(xl_file)  # pull filename from filepath
        (file, file_extension) = os.path.splitext(file)  # remove extension
        xl_file = f"{file}.{file_extension}"

    else:
        (file, file_extension) = os.path.splitext(xl_file)  # remove extension
        xl_file_path = os.getcwd()  # assume CWD for path
        xl_file = f"{file}{file_extension}"

    if file_extension not in [".xlsb", ".xlsm", ".xlsx"]:
        print(f"Extension {file_extension} is not a valid EXCEL extension supported.")
        exit()

    # setup progress bars
    # Define custom progress bar
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
    phrase_file_path: str = os.path.join(os.getcwd(), "Training Phrases", language)
    phrase_file_path = (
        os.path.join(phrase_file_path, "NL") if mode == "NL" else phrase_file_path
    )
    # zip existing file if it already exists, so nothing is overwritten
    if os.path.exists(phrase_file_path):
        zip_file_name: str = os.path.basename(phrase_file_path)
        now = datetime.datetime.now()
        formatted_datetime = now.strftime("%Y-%m-%d_%H%M%S")
        zip_file_name = f"{zip_file_name}_{formatted_datetime}"
        (zip_save_location, last_dir) = os.path.split(phrase_file_path)
        zip_file_path: str = os.path.join(zip_save_location, f"{zip_file_name}.zip")
        print(f"[green]Zip existing directory[/green]") if not quiet else None
        utils.zip_directory(phrase_file_path, zip_file_path)
        shutil.rmtree(phrase_file_path)
    # create the directory, which may have just been removed, or doesn't exist
    os.mkdir(phrase_file_path)

    print(f"Exporting data to: [blue]{phrase_file_path}[/blue]") if not quiet else None

    # read XL file, check if xlsb or xlsm
    with progress_bar as p:
        phrase_dict: dict = {}
        if file_extension == ".xlsb":
            # uses pyxlsb
            with pyxlsb.open_workbook(xl_file) as wb:
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
                        phrase_file: str = os.path.join(
                            phrase_file_path, sheet + ".txt"
                        )
                        # add to dictionary
                        phrase_dict[phrase_file] = phrase_list
        elif file_extension in [".xlsm", ".xlsx"]:
            # uses openpyxl
            wb = openpyxl.load_workbook(xl_file)
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
                phrase_file: str = os.path.join(phrase_file_path, sheet_name + ".txt")
                phrase_dict[phrase_file] = phrase_list
        else:
            print(f"[red]File not supported[/red]: {xl_file}")
            exit()

        # print the rows from the dictionary
        file_cnt: int = 0
        phrases_cnt: int = 0
        for phrase_file, phrases in phrase_dict.items():
            file_cnt += 1
            with open(phrase_file, mode="w", encoding="utf-8") as file:
                for line in phrases:
                    phrases_cnt += 1
                    file.write(f"{"".join(line)}\n")

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

    console = Console()
    console.print(table) if not quiet else None
