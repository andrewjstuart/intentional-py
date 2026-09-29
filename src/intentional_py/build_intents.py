"""Build Dialogflow ES intents from configuration files.

This module handles the core logic for creating intent JSON files from CSV configuration.
Supports both DD (Directed Dialog) and NL (Natural Language) modes with phrase extraction,
entity handling, priority mapping, and progress tracking.
"""

import csv
import datetime
import json
import uuid
from pathlib import Path
from time import perf_counter

from intentional_py import compare as comparing
from intentional_py import constants, exceptions, models, utils
from intentional_py import validate as validating
from intentional_py.reporting import BuildResult, CompareResult, Reporter


def intents(
    mode: str,
    config: Path,
    base_dir: Path,
    reporter: Reporter,
    clean: bool = False,
) -> BuildResult:
    """Build the intents described in the config file, after the preflight checks in validate.py.

    Args:
        mode (str): Directed dialog (DD) or Natural Language (NL), which selects the phrase folder.
        config (Path): The name of the config file to use to build intents.
        base_dir (Path): Project directory containing the training phrases and receiving the intents.
        reporter (Reporter): Receives messages and progress.
        clean (bool): Zip and remove everything in the intents folder before writing.

    Returns:
        BuildResult: counts, changes since the previous build, and output folder.
    """
    files_to_write, result, t1_start = _generate(mode, config, base_dir, reporter)
    output_dir = Path(base_dir, constants.DEFAULT_INTENTS_DIR)

    previous = [path for path in output_dir.glob("*") if path.is_file()] if output_dir.is_dir() else []
    if any(path.suffix == ".json" for path in previous):
        try:
            result.changes = comparing.compare(
                _summarize(files_to_write), comparing.load(output_dir), "the previous build"
            )
        except exceptions.IntentionalException as error:
            reporter.message("warning", f"Could not compare with the previous build: {error}")
    if clean and previous:
        stamp = datetime.datetime.now(datetime.UTC).astimezone().strftime("%Y-%m-%d_%H%M%S")
        result.backup = Path(base_dir, f"{constants.DEFAULT_INTENTS_DIR}_{stamp}.zip")
        with utils.file_errors(result.backup):
            utils.zip_directory(output_dir, result.backup, previous)
            for path in previous:
                path.unlink()

    output_dir.mkdir(parents=True, exist_ok=True)
    for file, data in files_to_write.items():
        with utils.file_errors(file), open(file, mode="w", encoding="utf-8") as output:
            json.dump(data, output, indent=4)

    result.output_dir = output_dir
    result.elapsed = perf_counter() - t1_start
    return result


def compare_build(
    mode: str, config: Path, base_dir: Path, source: Path, reporter: Reporter
) -> CompareResult:
    """Compare what the config would build with an agent export or intents folder; writes nothing."""
    files_to_write, _result, t1_start = _generate(mode, config, base_dir, reporter)
    result = comparing.compare(_summarize(files_to_write), comparing.load(source), str(source))
    result.elapsed = perf_counter() - t1_start
    return result


def _summarize(files_to_write: dict) -> dict:
    return comparing.summarize({Path(file).name: data for file, data in files_to_write.items()})


def _generate(
    mode: str, config: Path, base_dir: Path, reporter: Reporter
) -> tuple[dict, BuildResult, float]:
    """Check the config and create every intent's JSON in memory, keyed by output file."""
    # check if config file exists
    if not Path(config).exists():
        raise exceptions.FileSystemError(
            f"[red]Config file does not exist: [blue]{config}[/blue][/red]\n"
        )

    files_to_write: dict = {}
    result = BuildResult()
    langs_set: set = set()
    machine_learning_off: set = set()

    # Perform preflight validation on the config file to catch errors and warnings early
    rows, fatal_errors, warnings = validating.preflight_config(config, base_dir, mode)
    for warning in warnings:
        reporter.message("warning", f"[yellow]Warning:[/yellow] {warning}")
    if fatal_errors:
        raise exceptions.ValidationError(
            "Configuration validation failed:\n"
            + "\n".join(f"- {error}" for error in fatal_errors)
        )

    t1_start = perf_counter()
    if len(rows) == 0:
        raise exceptions.ValidationError(
            f"[red]Config file does not contain data[/red]: [cyan]{config}[/cyan]"
        )

    intents_with_english = {
        row[0] for row in rows if row[2] == constants.DEFAULT_LANGUAGE
    }
    first_row_for_intent: dict[str, int] = {}
    for row_number, row in enumerate(rows):
        first_row_for_intent.setdefault(row[0], row_number)

    label = f"Creating [green]{mode}[/green] intents using [cyan]{config}[/cyan]"
    for row_number, row in enumerate(reporter.track(rows, label)):
        write_intent = (
            row[2] == constants.DEFAULT_LANGUAGE
            or (
                row[0] not in intents_with_english
                and first_row_for_intent[row[0]] == row_number
            )
        )
        (
            data,
            temp_intents,
            temp_phrases,
            temp_entities,
            temp_lang,
            temp_nomatch,
            temp_ml,
        ) = create_json(models.ConfigRow.from_csv_row(row, row_number + 1), mode, base_dir, reporter, write_intent)

        # a duplicate (intent, language) row overwrites rather than merges, so its
        # phrases are not doubled; preflight warns when this happens (see validate.py)
        files_to_write.update(data)
        result.intents += temp_intents
        result.phrases += temp_phrases
        result.entities += temp_entities
        if temp_lang:
            langs_set.add(temp_lang)
        result.nomatch += temp_nomatch
        if temp_ml:
            machine_learning_off.add(temp_ml)

    result.files = len(files_to_write)
    result.intent_names = sorted({utils.check_priority(row[0])[0] for row in rows})
    result.languages = sorted(langs_set)
    result.machine_learning_off = sorted(machine_learning_off)
    return files_to_write, result, t1_start


def create_json(
    row: models.ConfigRow,
    mode: str,
    default_path: Path,
    reporter: Reporter,
    write_intent: bool = True,
) -> tuple[dict, int, int, int, str, int, str]:
    """Create the JSON for one config row, which must already have passed preflight_config.

    Args:
        row (models.ConfigRow): one config row, already validated and normalized.
        mode (str): Directed dialog (DD) or Natural Language (NL), which selects the phrase folder
        default_path (Path): project directory containing the training phrases and receiving the intents
        reporter (Reporter): Receives messages.
        write_intent (bool): Whether this row owns the shared intent definition file.

    Returns:
        tuple[dict, int, int, int, str, int, str]
            dict: A dictionary where the keys are file names and the values are the JSON data to be written to those files.
            int: number of intents created
            int: number of phrases read
            int: number of entities used
            str: language code used
            int: number of nomatch intents
            str: name of the intent if machine learning is off, otherwise empty

    """
    df_intent = row.intent
    priority = row.priority

    files_to_write: dict = {}  # variable to store all the files to write
    # counters
    intents_cnt: int = 0
    phrases_cnt: int = 0
    entities_cnt: int = 0
    nomatch_cnt: int = 0
    machine_learning_off: str = ""

    language = row.language
    dtmf_only: bool = language == "dtmf"
    if dtmf_only:
        language = constants.DEFAULT_LANGUAGE
    langs_used: str = language  # store for return

    action = row.action
    clean_action: str = action
    machine_learning = row.machine_learning

    if action.endswith("^"):
        machine_learning = False
        clean_action = action.removesuffix("^")

    # phrases are read from the '-NM' file, but the intent returns 'nomatch'
    if clean_action.endswith("-NM"):
        clean_action = "nomatch"

    dtmf_list: list = row.dtmf

    # set output file paths; the folder is created when the files are written
    output_file_path: Path = Path(default_path, constants.DEFAULT_INTENTS_DIR)

    output_file: Path = Path(f"{df_intent}.json")
    output_file = Path(output_file_path, output_file)
    output_phrase_file: Path = Path(f"{df_intent}_usersays_{language}.json")
    output_phrase_file = Path(output_file_path, output_phrase_file)

    # create intent JSON
    intent_json = """
        {
            "id": "default_id",
            "name": "default_name",
            "auto": true,
            "contexts": [
                "default_context"
            ],
            "responses": [
                {
                "resetContexts": false,
                "action": "default_action",
                "affectedContexts": [],
                "parameters": [],
                "messages": [
                    {
                    "type": "0",
                    "title": "",
                    "textToSpeech": "",
                    "lang": "default_lang",
                    "condition": ""
                    }
                ],
                "speech": []
                }
            ],
            "priority": 500000,
            "webhookUsed": false,
            "webhookForSlotFilling": false,
            "fallbackIntent": false,
            "events": [],
            "conditionalResponses": [],
            "condition": "",
            "conditionalFollowupEvents": []
        }        
        """
    intent_data: dict = json.loads(intent_json)
    # modify with correct values
    intent_data["id"] = str(uuid.uuid4())
    intent_data["name"] = df_intent
    intent_data["auto"] = machine_learning
    intent_data["contexts"][0] = row.context_text
    intent_data["responses"][0]["action"] = clean_action
    intent_data["responses"][0]["messages"][0]["lang"] = language
    intent_data["priority"] = priority

    intents_cnt += 1  # store for return
    if not machine_learning:
        machine_learning_off = df_intent
    if clean_action == "nomatch":
        nomatch_cnt += 1

    if row.entities:
        # create entity JSON
        entity_list: list = []
        entity_json = """
            {
                "id": "entity_id",
                "name": "entity_name",
                "required": false,
                "dataType": "entity_type",
                "value": "entity_value",
                "defaultValue": "",
                "isList": false,
                "prompts": [],
                "promptMessages": [],
                "noMatchPromptMessages": [],
                "noInputPromptMessages": [],
                "outputDialogContexts": []
            }
            """
        for entity in row.entities:
            # add values to the JSON object
            entity_data: dict = json.loads(entity_json)
            entity_data["id"] = str(uuid.uuid4())
            entity_data["name"] = entity.name
            entity_data["required"] = entity.required
            entity_data["dataType"] = entity.type
            entity_data["value"] = entity.value
            entity_list.append(entity_data)
            entities_cnt += 1

        # add proper JSON to the output
        intent_data["responses"][0]["parameters"] = entity_list

    if write_intent:
        files_to_write[output_file] = intent_data

    # set phrase file path
    phrase_file_path: Path = Path(
        default_path, constants.DEFAULT_TRAINING_PHRASES_DIR, language
    )
    phrase_file_path = (
        Path(phrase_file_path, "NL") if mode == "NL" else phrase_file_path
    )

    if not phrase_file_path.exists():
        reporter.message(
            "warning",
            f"\n[red]Phrase file path [blue]{phrase_file_path}[/blue] does not exist![/red]\nCreating Path...\n",
        )
        phrase_file_path.mkdir(parents=True, exist_ok=True)

    # create phrase JSON
    phrase_list: list = []
    phrase_json = """
        {
        "id": "default_id",
        "data": [
            {
            "text": "phrase",
            "userDefined": false
            }
        ],
        "isTemplate": false,
        "count": 0,
        "lang": "language",
        "updated": 0
        }        
        """
    for dtmf in dtmf_list:
        phrase_data: dict = json.loads(phrase_json)
        phrase_data["id"] = str(uuid.uuid4())
        phrase_data["data"][0]["text"] = dtmf
        phrase_data["lang"] = language
        phrase_list.append(phrase_data)

    if not dtmf_only:
        # read the phrase file
        phrase_file_path = utils.find_phrase_file(phrase_file_path, action)
        # a missing phrase file is already reported by preflight_config
        if phrase_file_path.exists():
            with utils.file_errors(phrase_file_path), open(
                phrase_file_path, mode="r", encoding="utf-8"
            ) as file:
                reader = csv.reader(file)
                phrase_rows = [phrase_row for phrase_row in reader if any(phrase_row)]  # Filter out empty rows
                for phrase_row in phrase_rows:
                    row_str: str = "".join(phrase_row)  # convert to string
                    phrase_data: dict = json.loads(phrase_json)
                    phrase_data["id"] = str(uuid.uuid4())
                    (_, temp_phrase_list) = utils.check_phrase_for_entity(
                        row_str
                    )  # temp variable for entity_list
                    if len(temp_phrase_list) > 1:
                        new_phrase_list: list = []
                        for phrase in temp_phrase_list:
                            phrase = "".join(phrase)
                            if "|" in phrase:
                                entity_json = """
                                {
                                "text": "text",
                                "meta": "@temp",
                                "alias": "name",
                                "userDefined": true
                                }
                                """
                                entity_code: list = phrase.split(
                                    "|"
                                )  # splits it between the entity and the phrase
                                (ent_type, ent_name, _, _) = utils.check_alias(
                                    entity_code[0]
                                )  # temp variable for ent_value, ent_required
                                entity_data: dict = json.loads(entity_json)
                                entity_data["text"] = entity_code[1]
                                entity_data["meta"] = ent_type
                                entity_data["alias"] = ent_name
                                new_phrase_list.append(entity_data)
                            else:
                                entity_json = """
                                {
                                "text": "phrase",
                                "userDefined": false
                                }
                                """
                                entity_data: dict = json.loads(entity_json)
                                entity_data["text"] = phrase
                                new_phrase_list.append(entity_data)

                        phrase_data["data"] = new_phrase_list
                    else:
                        temp_phrase_list = "".join(temp_phrase_list)
                        phrase_data["data"][0]["text"] = temp_phrase_list

                    phrase_data["lang"] = language
                    phrase_list.append(phrase_data)
                    phrases_cnt += 1  # store for return

    # written by intents() once every row has been processed
    files_to_write[output_phrase_file] = phrase_list

    return (
        files_to_write,
        intents_cnt,
        phrases_cnt,
        entities_cnt,
        langs_used,
        nomatch_cnt,
        machine_learning_off,
    )


def nl_config(
    config: Path, vertical: str, context: str, lowercase: bool, reporter: Reporter
) -> None:
    """Builds a config file for NL intent creation. It creates the file by reading the existing NL directories
    looking for text file corresponding the to intent names. These files contain training phrases for the
    intent the same as the directed dialog intent creation.

    Args:
        config (Path): name of the config file to create
        vertical (str): vertical abbreviation used in the intent names
        context (str): context used to reference all the intents at the same time
        lowercase (bool): flag to adjust the action to be lowercase and is only used by specific clients
        reporter (Reporter): Receives messages and answers the duplicate phrase prompt.
    """
    # the training phrases are read from the config file's folder
    (config_file_path, config_file_name, _temp_file_extension) = utils.check_for_path(
        config
    )

    table_columns: list = ["Building Config", "Vertical", "Context"]
    table_row: list = [
        f"{config_file_name}",
        f"{vertical}",
        f"{context}",
    ]

    if lowercase:
        table_columns.append("Lowercase")
        table_row.append(f"[cyan]{lowercase}[/cyan]")

    # set phrase file path
    phrase_file_path: Path = Path(
        config_file_path, constants.DEFAULT_TRAINING_PHRASES_DIR
    )
    if not phrase_file_path.exists():
        raise exceptions.FileSystemError(
            f"[red]Phrase file path [blue]{phrase_file_path}[/blue] does not exist![/red]"
        )

    # determine languages available by the files available, and then which are used by the having text files
    languages_used: set = set()
    for lang in phrase_file_path.iterdir():
        lang_path: Path = Path(lang, "NL")
        if lang_path.exists():
            filenames: list = [
                item.name for item in lang_path.iterdir() if item.is_file()
            ]
            for filename in filenames:
                if filename.endswith(".txt"):
                    languages_used.add(lang)

    # remove config file before creating a new one
    if config.exists():
        with utils.file_errors(config):
            config.unlink()

    # build the intent file
    for lang in sorted(languages_used):
        lang_path: Path = Path(lang, "NL")
        lang = Path(lang.stem)
        files_to_add: list = []
        entity_dict: dict = {}
        filenames: list = [item.name for item in lang_path.iterdir() if item.is_file()]
        for filename in filenames:
            filepath = Path(lang_path, filename)
            if filepath.is_file() and filename.endswith(".txt"):
                files_to_add.append(Path(filename))

                # read phrase files looking for entities
                entity_set: set = set()
                with utils.file_errors(filepath), open(
                    filepath, mode="r", encoding="utf-8"
                ) as file:
                    reader = csv.reader(file)
                    rows = [row for row in reader if any(row)]  # Filter out empty rows
                    for row in rows:
                        row = "".join(row)  # convert to string
                        (entity_list, _phrase_list) = utils.check_phrase_for_entity(row)
                        if entity_list:
                            for entity in entity_list:
                                # add to set to only keep unique entities
                                entity_set.add(str(entity))
                            # add them to dictionary to pull out later by filename
                            entity_dict[Path(filename)] = entity_set

        with utils.file_errors(config), open(
            config, mode="a", encoding="utf-8"
        ) as config_file:
            for file in files_to_add:
                action = file.with_suffix("")  # remove extension
                action: str = str(action)
                # remove any underscores and format intent correctly
                temp: list = action.split("_")
                res: str = temp[0].title() + "".join(ele.title() for ele in temp[1:])
                intent: str = f"{vertical}.{res}"

                # check for entities
                entity: str = ""
                if file in entity_dict:
                    entity = "|".join(entity_dict[file])

                dtmf: str = ""  # no DTMF on NL...usually

                ml: bool = True  # default is set to ML on
                if action.endswith("^"):
                    ml = False
                    intent = intent.removesuffix("^")

                # if ACTION ends in "-NM", the builder returns 'nomatch', which is already lowercase
                if action.endswith("-NM"):
                    intent = intent.removesuffix("-Nm")
                elif lowercase:
                    # write it lowercase first, then with uppercase name
                    config_file.write(
                        f"{intent},{context},{lang},{action.lower()},{entity},{dtmf},{str(ml).upper()}\n"
                    )

                config_file.write(
                    f"{intent},{context},{lang},{action},{entity},{dtmf},{str(ml).upper()}\n"
                )

    table_columns.append("Status")
    if not config.exists():
        raise exceptions.ConfigurationError(
            f"Failed to create NL config file: {config}\n[red][bold]Abort processing...[/red][/bold]"
        )
    table_row.append("[green]COMPLETE[/green]")
    reporter.table(table_columns, [table_row])

    # check for duplicate phrases in the training phrases
    for lang in sorted(languages_used):
        lang_path: Path = Path(lang, "NL")
        lang = Path(lang.stem)
        duplicates, phrases_to_review = utils.check_for_duplicate_phrases(lang_path)
        if phrases_to_review:
            reporter.table(
                [
                    f"[red][bright_black]'uh'[/bright_black] and [bright_black]'um'[/bright_black] phrases found in [yellow]{lang}[/yellow][/red]"
                ],
                [[phrase] for phrase in phrases_to_review],
                level="warning",
            )
        if duplicates:
            reporter.table(
                [f"[red]Duplicate phrases found in [yellow]'{lang}'[/yellow][/red]"],
                [[dup] for dup in sorted(duplicates)],
                level="error",
            )
            if not reporter.confirm("Continue processing files", sorted(duplicates)):
                raise exceptions.IntentionalException(
                    "\n[bold][red]Abort processing...[/bold][/red]\n"
                    "User aborted due to duplicate phrases"
                )
