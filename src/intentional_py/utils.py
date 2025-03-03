import re
import zipfile
from pathlib import Path

from rich import box, print
from rich.console import Console
from rich.table import Table


def check_for_duplicate_phrases(directory: Path, lang: str, quiet: bool) -> set:
    """Checks text files in the directory for duplicate phrases across all files

    Args:
        directory (Path): directory to search
        lang (str): the language being searched

    Returns:
        set: a set containing all duplicated phrases
    """
    all_lines: set = set()
    duplicates: set = set()
    phrases_to_review: list = []
    filenames: list = [item.name for item in directory.iterdir() if item.is_file()]
    for filename in filenames:
        if filename.endswith(".txt"):
            filepath: Path = Path(directory, filename)
            with open(filepath, "r") as file:
                for line in file:
                    line = line.strip()
                    # check of line beginning with 'uh' or 'um'
                    if line.startswith(("uh", "um")):
                        phrases_to_review.append(line)

                    if line in all_lines:
                        duplicates.add(line)
                    else:
                        all_lines.add(line)

    if phrases_to_review:
        uhum_table = Table(
            f"[red][bright_black]'uh'[/bright_black] and [bright_black]'um'[/bright_black] phrases found in [yellow]{lang}[/yellow][/red]",
            box=box.ROUNDED,
            header_style="",
        )
        for phrase in phrases_to_review:
            uhum_table.add_row(phrase)
        console = Console()
        if not quiet:
            console.print(uhum_table)
            print("")  # empty line
    return duplicates


def check_priority(df_intent: str) -> tuple[str, str]:
    """Parses the optional priority from the intent name
        priority is appended to df_intent value inside curly brackets {}
        "highest" or "1"
        "high" or "2"
        "normal" or "3" (default)
        "low" or "4"
        "ignore" or "5"
    Args:
        df_intent (str): The name of the intent, with or without an optional priority

    Returns:
        tuple[str, str]: The final intent name and the priority value
    """
    priority: str = "500000"  # default to "normal" priority
    matches: list = re.findall(r"\{(.*?)\}", df_intent)  # search for {}
    if matches:
        priority_dict: dict = {
            "1": 1000000,
            "2": 750000,
            "3": 500000,
            "4": 250000,
            "5": -1,
            "highest": 1000000,
            "high": 750000,
            "normal": 500000,
            "low": 250000,
            "ignore": -1,
        }
        priority = priority_dict[matches[0]]
    intent_split: list = df_intent.split("{", 1)
    intent: str = intent_split[0]

    return (intent, priority)


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


def check_alias(entity_to_check: str) -> tuple[str, str, str, bool]:
    """determines if the entity passed in has and alias and if it is required

    Args:
        entity_to_check (str): the entity value to parse from the config

    Returns:
        tuple[str, str, str, bool]: The entity type, name, value, and if it required
    """
    # default vars
    entity_type: str = ""
    entity_name: str = ""
    entity_value: str = ""
    entity_required: bool = False
    # search for []
    matches: list = re.findall(r"\[(.*?)\]", entity_to_check)
    # remove brackets
    entity_split: list = entity_to_check.split("[", 1)
    entity: str = entity_split[0]

    if matches:
        alias: str = matches[0]
        (entity, entity_required) = check_required(entity)
        entity_type = f"@{entity}"  # append @
        entity_name = alias
        entity_value = f"${alias}"  # append $
    else:
        # no alias
        (entity, entity_required) = check_required(entity)
        entity_type = f"@{entity}"
        entity = entity.removeprefix("sys.")
        entity = entity.lower()
        entity_name = entity
        entity_value = f"${entity}"  # append $
    return (entity_type, entity_name, entity_value, entity_required)


def check_required(entity: str) -> tuple[str, bool]:
    """Checks for a * at the end of the entity name to determine if the entity is required

    Args:
        entity (str): entity value from config

    Returns:
        tuple[str, bool]: returns the entity with * removed, if present, and a boolean value if it's required
    """
    entity_required = False
    if entity.endswith("*"):  # check for required
        entity = entity.removesuffix("*")
        entity_required = True
    return (entity, entity_required)


def check_phrase_for_entity(phrase: str) -> tuple[list, list]:
    """Searches a phrase for possible entities in the format <entityname|phrase>

    Args:
        phrase (str): the phrase from the file to search for entities in correct format

    Returns:
        tuple[list, list]: the first list returned is the entities used, and is formatted for the config file creation,
        the second list returned is the phrase split on the entity
    """
    entity_list: list = []
    phrases_list: list = []
    # search for <>
    matches: list = re.findall(r"\<(.*?)\>", phrase)
    # remove brackets
    if matches:
        # fill entities for config file
        for match in matches:
            entity_split: list = match.split("|", 1)
            entity_list.append(entity_split[0])  # pulls out just the entity name

        # fill phrase list for usersays file
        phrases_list = split_phrase_by_entity(phrase, matches)
    else:
        # no entities, add to usersays file
        phrases_list.append(phrase)

    return (entity_list, phrases_list)


def split_phrase_by_entity(phrase: str, delimiters: list) -> list:
    """splits the phrase based on the available entities, uses recursion

    Args:
        phrase (str): the phrase for the file
        delimiters (list): the matched entities used to split the phrase

    Returns:
        list: returns a list of the phrase split on the entities
    """
    phrases: list = []

    # break out of recursion when the end of the phrase is reached
    if len(phrase) == 0:
        return phrases

    try:
        delimiter: str = delimiters.pop(0)
    except IndexError:  # break out of recursion when the entities are exhausted
        phrases.append(phrase)
        return phrases
    else:
        if delimiter not in phrase:
            phrases.append(phrase)
            return phrases

    # Find the first occurrence of the delimiter
    index: int = phrase.find(delimiter)
    # Split the string into two parts
    first_part = phrase[:index]
    first_part = clean_phrase(first_part)
    phrases.append(first_part)
    phrases.append(delimiter)  # the entity
    remaining_part = phrase[index + len(delimiter) :]
    remaining_part = clean_phrase(remaining_part)

    # Recursively split the remaining part
    return phrases + split_phrase_by_entity(remaining_part, delimiters)


def clean_phrase(string: str) -> str:
    """removes remnants of entities in the phrase

    Args:
        string (str): the phrase to be cleaned of < and >

    Returns:
        str: the cleaned phrase
    """
    string = string.removeprefix("<")
    string = string.removesuffix(">")
    string = string.strip()  # also remove whitespace
    return string


def zip_directory(directory_path: Path, zip_path: Path) -> None:
    """Zip a directory provided

    Args:
        directory_path (Path): directory to zip
        zip_path (Path): path to save the zip file
    """
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zippy:
        for file_path in directory_path.rglob("*"):
            zippy.write(file_path, arcname=file_path.relative_to(directory_path))


def check_for_path(file_to_check: Path) -> tuple[Path, Path, str]:
    """check the file to determine if there is a path value prefixed

    Args:
        file_to_check (Path): file to check if it contains a path or uses implied CWD

    Returns:
        tuple[Path, Path, str]: returns the path, the file name with the extension, and the file extension
    """
    if file_to_check.parent:
        file_to_check_path = file_to_check.parent  # pull filepath from file
        # file_with_extension: str = file_to_check.name  # pull filename from filepath
        file: str = file_to_check.stem
        file_extension: str = file_to_check.suffix  # store extension
        file_to_check = Path(f"{file}{file_extension}")

    else:
        file: str = file_to_check.stem
        file_extension: str = file_to_check.suffix  # store extension
        file_to_check_path = Path.cwd()  # assume CWD for path
        file_to_check = Path(f"{file}{file_extension}")

    return (file_to_check_path, file_to_check, file_extension)
