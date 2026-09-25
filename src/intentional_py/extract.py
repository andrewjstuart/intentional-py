"""Extract training phrases from Excel files.

This module handles reading Excel files (.xlsb, .xlsm, .xlsx) and extracting
training phrases into organized text files by language and mode (DD or NL).
Includes backup functionality for existing phrase directories.
"""

import datetime
import shutil
from pathlib import Path
from time import perf_counter

import openpyxl
import pyxlsb

from intentional_py import constants, exceptions, utils
from intentional_py.reporting import ExtractResult, Reporter


def excel_data(
    xl_file: Path, mode: str, language: str, base_dir: Path, reporter: Reporter
) -> ExtractResult:
    t1_start = perf_counter()

    xl_file_path: Path
    file_extension: str

    (xl_file_path, xl_file, file_extension) = utils.check_for_path(xl_file)

    if file_extension not in constants.SUPPORTED_EXCEL_EXTENSIONS:
        raise exceptions.ExtractionError(
            f"Unsupported file extension: {file_extension}. Supported: {constants.SUPPORTED_EXCEL_EXTENSIONS}"
        )

    # set up path to save files
    # set phrase file path
    phrase_file_path: Path = Path(
        base_dir, constants.DEFAULT_TRAINING_PHRASES_DIR, language
    )
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
        reporter.message("info", "[green]Zip existing directory[/green]")
        utils.zip_directory(phrase_file_path, zip_file_path)
        shutil.rmtree(str(phrase_file_path))
    # create the directory, which may have just been removed, or doesn't exist
    phrase_file_path.mkdir(parents=True, exist_ok=True)

    reporter.message("info", f"Exporting data to: [blue]{phrase_file_path}[/blue]")

    # read XL file, check if xlsb or xlsm
    label = f"Processing [green]{xl_file}[/green]"
    phrase_dict: dict = {}
    phrase_file: Path
    xl = Path(xl_file_path, xl_file)
    if file_extension == ".xlsb":
        # uses pyxlsb
        with pyxlsb.open_workbook(xl) as wb:
            for sheet in reporter.track(wb.sheets, label):
                phrases: set = set()
                for row in wb.get_sheet(sheet).rows():
                    for cell in row:
                        # add the phrases to a set to remove duplicates
                        if cell.v is not None and str(cell.v).strip():
                            phrases.add(str(cell.v))

                phrase_file = Path(phrase_file_path, f"{sheet}.txt")
                phrase_dict[phrase_file] = sorted(phrases)
    elif file_extension in [".xlsm", ".xlsx"]:
        # uses openpyxl
        wb = openpyxl.load_workbook(xl)
        for sheet_name in reporter.track(wb.sheetnames, label):
            phrases: set = set()
            sheet = wb[sheet_name]
            for row in sheet.iter_rows(values_only=True):
                phrase = "".join(str(cell) for cell in row if cell is not None)
                # add the phrases to a set to remove duplicates
                if phrase.strip():
                    phrases.add(phrase)
            phrase_file = Path(phrase_file_path, f"{sheet_name}.txt")
            phrase_dict[phrase_file] = sorted(phrases)
    else:
        raise exceptions.ExtractionError(
            f"[red]Unsupported file format[/red]: {xl_file}"
        )

    result = ExtractResult(output_dir=phrase_file_path)
    for phrase_file, phrases in phrase_dict.items():
        result.files += 1
        if not phrases:
            result.empty_sheets.append(phrase_file.stem)
        with phrase_file.open(mode="w", encoding="utf-8") as f:
            for line in phrases:
                result.phrases += 1
                f.write(f"{line}\n")

    result.elapsed = perf_counter() - t1_start
    return result
