"""Create a config file from the Excel design document.

The design document has one sheet with a header row (Intent, Context, Language,
Action, Entities, DTMF and a machine learning column) and one intent per row.
Its machine learning column uses the same values as the config file: TRUE keeps
machine learning on and FALSE turns it off.
"""

import csv
import shutil
import zipfile
from pathlib import Path

import openpyxl
import pyxlsb
from openpyxl.utils.exceptions import InvalidFileException

from intentional_py import constants, exceptions, models, utils
from intentional_py import validate as validating
from intentional_py.reporting import DesignResult, Reporter

HEADERS = {
    "intent": {"intent", "intent name"},
    "context": {"context", "contexts"},
    "language": {"language", "lang"},
    "action": {"action"},
    "entities": {"entities", "entity"},
    "dtmf": {"dtmf"},
    "machine_learning": {"ml", "machine learning"},
}
REQUIRED = ("intent", "context", "language", "action")
HEADER_SEARCH_ROWS = 25


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _sheets(xl_file: Path) -> dict[str, list[list[str]]]:
    """Every sheet's cell values as text, keyed by sheet name."""
    try:
        with utils.file_errors(xl_file):
            if xl_file.suffix.lower() == ".xlsb":
                with pyxlsb.open_workbook(xl_file) as workbook:
                    return {
                        name: [
                            [_text(cell.v) for cell in row]
                            for row in workbook.get_sheet(name).rows()
                        ]
                        for name in workbook.sheets
                    }
            workbook = openpyxl.load_workbook(xl_file, read_only=True, data_only=True)
            try:
                return {
                    sheet.title: [
                        [_text(value) for value in row]
                        for row in sheet.iter_rows(values_only=True)
                    ]
                    for sheet in workbook.worksheets
                }
            finally:
                workbook.close()
    except (zipfile.BadZipFile, InvalidFileException, KeyError, ValueError) as error:
        raise exceptions.ExtractionError(
            f"{xl_file} could not be read as an Excel file ({error})."
        ) from error


def _find_header(rows: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        columns = {}
        for position, cell in enumerate(row):
            name = " ".join(cell.casefold().split())
            for key, names in HEADERS.items():
                if name in names and key not in columns:
                    columns[key] = position
        if all(key in columns for key in REQUIRED):
            return index, columns
    return None


def read_design(xl_file: Path, sheet: str = "") -> tuple[str, list[list[str]]]:
    """The sheet used and its intent rows, converted to config rows."""
    if xl_file.suffix.lower() not in constants.SUPPORTED_EXCEL_EXTENSIONS:
        raise exceptions.ExtractionError(
            f"Unsupported file extension: {xl_file.suffix}. Supported: {sorted(constants.SUPPORTED_EXCEL_EXTENSIONS)}"
        )
    sheets = _sheets(xl_file)
    if sheet and sheet not in sheets:
        raise exceptions.ConfigurationError(
            f"Sheet '{sheet}' was not found in {xl_file.name}. Sheets: {', '.join(sheets)}"
        )
    for name in [sheet] if sheet else list(sheets):
        found = _find_header(sheets[name])
        if found:
            header_index, columns = found
            break
    else:
        where = f"sheet '{sheet}'" if sheet else xl_file.name
        raise exceptions.ConfigurationError(
            f"No header row with Intent, Context, Language and Action columns was found in {where}."
        )

    def cell(row: list[str], key: str) -> str:
        position = columns.get(key)
        return row[position] if position is not None and position < len(row) else ""

    config_rows = []
    for row in sheets[name][header_index + 1 :]:
        values = [
            cell(row, key)
            for key in ("intent", "context", "language", "action", "entities", "dtmf")
        ]
        if not any(values):
            continue
        machine_learning = cell(row, "machine_learning").upper()
        config_rows.append(values + [machine_learning])
    return name, config_rows


def config_from_design(
    xl_file: Path,
    config: Path,
    reporter: Reporter,
    sheet: str = "",
    rules: models.NamingRules | None = None,
) -> DesignResult:
    """Write the config file from the design document, backing up any existing config first."""
    sheet_used, rows = read_design(xl_file, sheet)
    if not rows:
        raise exceptions.ConfigurationError(
            f"Sheet '{sheet_used}' in {xl_file.name} has no intent rows."
        )
    result = DesignResult(config=config, sheet=sheet_used, rows=len(rows))
    reporter.message("info", f"Reading sheet '{sheet_used}' of {xl_file.name}")
    if config.exists():
        stamp = utils.timestamp()
        result.backup = config.with_name(f"{config.stem}_{stamp}{config.suffix}")
        with utils.file_errors(result.backup):
            shutil.copy2(config, result.backup)
    config.parent.mkdir(parents=True, exist_ok=True)
    with (
        utils.file_errors(config),
        config.open("w", encoding="utf-8", newline="") as file,
    ):
        csv.writer(file).writerows(rows)
    _, result.errors, result.warnings, _removals = validating.check_rows(
        rows, config.parent, "DD", rules
    )
    return result
