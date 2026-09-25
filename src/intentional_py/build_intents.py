"""Build Dialogflow ES intents from configuration files.

This module handles the core logic for creating intent JSON files from CSV configuration.
Supports both DD (Directed Dialog) and NL (Natural Language) modes with phrase extraction,
entity handling, priority mapping, and progress tracking.
"""

import csv
import json
import uuid
from pathlib import Path
from time import perf_counter

from intentional_py import constants, exceptions, utils
from intentional_py import validate as validating
from intentional_py.reporting import BuildResult, Reporter


def intents(
    mode: str,
    config: Path,
    base_dir: Path,
    reporter: Reporter,
) -> BuildResult:
    """Build the intents described in the config file. Perform simple sanity checking on input to enforce standards.

    Args:
        mode (str): Determine if it's directed dialog (DD) or Natural Language (NL) which selects the appropriate phrase directories and config files.
        config (Path): The name of the config file to use to build intents.
        base_dir (Path): Project directory containing the training phrases and receiving the intents.
        reporter (Reporter): Receives messages and progress.
    """
    # check if config file exists
    if not Path(config).exists():
        raise exceptions.FileSystemError(
            f"[red]Config file does not exist: [blue]{config}[/blue][/red]\n"
        )

    files_to_write: dict = {}
    result = BuildResult()
    langs_set: set = set()
    ml_disabled_set: set = set()

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

    label = f"Creating [green]{mode}[/green] intents using [cyan]{config}[/cyan]"
    for row in reporter.track(rows, label):
        (
            data,
            temp_intents,
            temp_phrases,
            temp_entities,
            temp_lang,
            temp_nomatch,
            temp_ml,
        ) = create_json(row, mode, base_dir, reporter)

        files_to_write.update(data)
        result.intents += temp_intents
        result.phrases += temp_phrases
        result.entities += temp_entities
        if temp_lang:
            langs_set.add(temp_lang)
        result.nomatch += temp_nomatch
        if temp_ml:
            ml_disabled_set.add(temp_ml)

    for file, data in files_to_write.items():
        with utils.file_errors(file), open(file, mode="w", encoding="utf-8") as output:
            json.dump(data, output, indent=4)

    result.files = len(files_to_write)
    result.languages = sorted(langs_set)
    result.ml_disabled = sorted(ml_disabled_set)
    result.elapsed = perf_counter() - t1_start
    return result


def create_json(
    row: list,
    mode: str,
    default_path: Path,
    reporter: Reporter,
) -> tuple[dict, int, int, int, str, int, str]:
    """Create JSON files described by config rows

    Args:
        row (list): line from config file
        mode (str): Determine if it's directed dialog (DD) or Natural Language (NL) which selects the appropriate phrase directories
        reporter (Reporter): Receives messages.

    Returns:
        tuple[dict,int,int,int,int,int,str]
            dict: A dictionary where the keys are file names and the values are the JSON data to be written to those files.
            int: number of intents created
            int: number of phrases read
            int: number of entities used
            str: number of languages used
            int: number of nomatch intents
            str: name of intents if ML disabled

    """
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

    files_to_write: dict = {}  # variable to store all the files to write
    # counters
    intents_cnt: int = 0
    phrases_cnt: int = 0
    entities_cnt: int = 0
    langs_used: str = ""
    nomatch_cnt: int = 0
    ml_disabled_str: str = ""

    # validate values
    if not df_intent:
        reporter.message("error", f"[red]No intent provided![/red]: {row}")
        return (
            files_to_write,
            intents_cnt,
            phrases_cnt,
            entities_cnt,
            langs_used,
            nomatch_cnt,
            ml_disabled_str,
        )

    if "-" in df_intent:
        reporter.message(
            "error", f"[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]"
        )

    # check for priority, appended to DF intent name with curly brackets {}
    df_intent, priority = utils.check_priority(df_intent)

    if not df_context:
        reporter.message("error", f"[red]No context provided![/red]: {row}")
        return (
            files_to_write,
            intents_cnt,
            phrases_cnt,
            entities_cnt,
            langs_used,
            nomatch_cnt,
            ml_disabled_str,
        )
    language = language.lower()
    dtmf_only: bool = False
    if language == "dtmf":
        dtmf_only = True
        language = constants.DEFAULT_LANGUAGE

    if language not in constants.VALID_LANGUAGES:
        reporter.message(
            "warning",
            f"[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue], using [yellow]'{constants.DEFAULT_LANGUAGE}'[/yellow] as default.",
        )
        language = constants.DEFAULT_LANGUAGE

    langs_used = language  # store for return

    if not action:
        reporter.message("error", f"[red]No action provided![/red]: {row}")
        return (
            files_to_write,
            intents_cnt,
            phrases_cnt,
            entities_cnt,
            langs_used,
            nomatch_cnt,
            ml_disabled_str,
        )

    clean_action: str = action

    if action.endswith("^"):
        machine_learning = "FALSE"
        clean_action = action.removesuffix("^")

    # phrases are read from the '-NM' file, but the intent returns 'nomatch'
    if clean_action.endswith("-NM"):
        clean_action = "nomatch"

    # dtmf value is optional, unless language is dtmf
    if dtmf_only and not dtmf_value:
        reporter.message("error", f"[red]No DTMF value provided![/red]: {row}")
        return (
            files_to_write,
            intents_cnt,
            phrases_cnt,
            entities_cnt,
            langs_used,
            nomatch_cnt,
            ml_disabled_str,
        )

    dtmf_list: list = []
    if dtmf_value:
        dtmf_list = dtmf_value.split("|")

    if not machine_learning:
        machine_learning = constants.MACHINE_LEARNING_DEFAULT
    machine_learning = machine_learning.lower()
    if machine_learning not in constants.VALID_ML_VALUES:
        reporter.message(
            "error",
            f"Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}",
        )
        return (
            files_to_write,
            intents_cnt,
            phrases_cnt,
            entities_cnt,
            langs_used,
            nomatch_cnt,
            ml_disabled_str,
        )

    # set output file paths
    output_file_path: Path = Path(default_path, constants.DEFAULT_INTENTS_DIR)
    # create new directory for the intents if it does not exist
    Path(output_file_path).mkdir(parents=True, exist_ok=True)

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
    intent_data["auto"] = bool(utils.strtobool(machine_learning))
    intent_data["contexts"][0] = df_context
    intent_data["responses"][0]["action"] = clean_action
    intent_data["responses"][0]["messages"][0]["lang"] = language
    intent_data["priority"] = priority

    intents_cnt += 1  # store for return
    if not utils.strtobool(machine_learning):
        ml_disabled_str = df_intent
    if clean_action == "nomatch":
        nomatch_cnt += 1

    if df_entity:
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
        # optional to pass entity
        for entity in df_entity.split("|"):
            (ent_type, ent_name, ent_value, ent_required) = utils.check_alias(entity)
            # add values to the JSON object
            entity_data: dict = json.loads(entity_json)
            entity_data["id"] = str(uuid.uuid4())
            entity_data["name"] = ent_name
            entity_data["required"] = ent_required
            entity_data["dataType"] = ent_type
            entity_data["value"] = ent_value
            entity_list.append(entity_data)
            entities_cnt += 1

        # add proper JSON to the output
        intent_data["responses"][0]["parameters"] = entity_list

    # We want the default language to be 'en' on the intent name,
    # check to see if the file already exists before continuing
    # don't recreate the intent, but the phrase files can still be updated

    # print JSON file for intent
    # save info to print later
    if language == "en":  # TODO: figure out a better way to make this work
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
                rows = [row for row in reader if any(row)]  # Filter out empty rows
                for row in rows:
                    row_str: str = "".join(row)  # convert to string
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

    # print JSON file for phrase
    # with open(output_phrase_file, mode="w", encoding="utf-8") as phrase_output:
    # json.dump(phrase_list, phrase_output, indent=4)
    files_to_write[output_phrase_file] = phrase_list

    return (
        files_to_write,
        intents_cnt,
        phrases_cnt,
        entities_cnt,
        langs_used,
        nomatch_cnt,
        ml_disabled_str,
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
    # check if config file contains a path, the training phrases will match the config location
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
            if not reporter.confirm("Continue processing files"):
                raise exceptions.IntentionalException(
                    "\n[bold][red]Abort processing...[/bold][/red]\n"
                    "User aborted due to duplicate phrases"
                )
