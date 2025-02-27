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
import csv
from pathlib import Path
import uuid
import json
from time import perf_counter
from intentional_py import utils as utils


def intents(
    mode: str,
    config: Path,
    quiet: bool,
    test: bool,
) -> None:
    """Build the intents described in the config file. Perform simple sanity checking on input to enforce standards.

    Args:
        mode (str): Determine if it's directed dialog (DD) or Natural Language (NL) which selects the appropriate phrase directories and config files.
        config (Path): The name of the config file to use to build intents.
        quiet (bool): Suppress most standard output to terminal.
    """
    # check if config file exists
    if not Path(config).exists():
        print(f"\n[red]Config file [blue]{config}[/blue] does not exist![/red]\n")
        return

    # Define custom progress bar
    if test:
        progress_bar = Progress(
            TextColumn(
                f"Creating [green]{mode}[/green] intents using [cyan]{config}[/cyan]"
            ),
        )
    else:
        progress_bar = Progress(
            TextColumn(
                f"Creating [green]{mode}[/green] intents using [cyan]{config}[/cyan]:"
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
    files_to_write: dict = {}
    data: dict = {}
    # counters
    intents_cnt: int = 0
    phrases_cnt: int = 0
    entities_cnt: int = 0
    langs_set: set = set()
    nomatch_cnt: int = 0
    file_cnt: int = 0
    ml_disabled_set: set = set()

    # check if config file contains a path, the training phrases will match the config location
    (default_path, temp_file, temp_file_extension) = utils.check_for_path(config)

    t1_start = perf_counter()
    # read the config file
    with open(config, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        rows = [row for row in reader if any(row)]  # Filter out empty rows
        if len(rows) == 0:
            print(
                f"[red]Config file does not contain data[/red]: [cyan]{config}[/cyan]"
            )
            return
        # Use custom progress bar
        with progress_bar as p:
            for row in p.track(rows):
                (
                    data,
                    temp_intents,
                    temp_phrases,
                    temp_entities,
                    temp_lang,
                    temp_nomatch,
                    temp_ml,
                ) = create_json(row, mode, default_path, quiet, test)

                # store output variables
                files_to_write.update(data)
                intents_cnt += temp_intents
                phrases_cnt += temp_phrases
                entities_cnt += temp_entities
                langs_set.add(temp_lang)
                nomatch_cnt += temp_nomatch
                ml_disabled_set.add(temp_ml) if temp_ml else next

            if files_to_write:
                for file, data in files_to_write.items():
                    with open(file, mode="w", encoding="utf-8") as output:
                        json.dump(data, output, indent=4)

    # assign output variables and format correctly
    file_cnt = len(files_to_write)
    langs_used: str = ", ".join(sorted(langs_set))
    t1_stop = perf_counter()
    time = f"{t1_stop - t1_start:.3f} s"

    # print a table with useful or interesting stats
    table = Table(
        "Time", "Intents", "Phrases", "Entities", "Languages", "Files", box=box.ROUNDED
    )

    if nomatch_cnt:
        table.add_column("NoMatch")
        table.add_row(
            time,
            str(intents_cnt),
            str(phrases_cnt),
            str(entities_cnt),
            str(langs_used),
            str(file_cnt),
            str(nomatch_cnt),
        )
    else:
        table.add_row(
            time,
            str(intents_cnt),
            str(phrases_cnt),
            str(entities_cnt),
            str(langs_used),
            str(file_cnt),
        )

    if test:
        print("build complete")
    else:
        console = Console()
        console.print(table) if not quiet else None

        if ml_disabled_set:
            ml_table = Table("Intents with ML Disabled", box=box.ROUNDED)
            for phrase in ml_disabled_set:
                ml_table.add_row(phrase)
            console.print(ml_table) if not quiet else None


def create_json(
    row: list,
    mode: str,
    default_path: Path,
    quiet: bool,
    test: bool,
) -> tuple[dict, int, int, int, str, int, str]:
    """Create JSON files described by config rows

    Args:
        row (list): line from config file
        mode (str): Determine if it's directed dialog (DD) or Natural Language (NL) which selects the appropriate phrase directories
        quiet (bool): Suppress most standard output to terminal.

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
    # print(row)
    # print(
    #    f"Intent: {df_intent} | Context: {df_context} | Language: {language} | Action: {action} | Entity: {df_entity} | DTMF: {dtmf_value} | ML: {machine_learning}"
    # )

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
        print(f"[red]No intent provided![/red]: {row}")
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
        print(f"[red]Incorrect intent name:[/red] [blue]{df_intent}[/blue]")

    # check for priority, appended to DF intent name with curly brackets {}
    df_intent, priority = utils.check_priority(df_intent)

    if not df_context:
        print(f"[red]No context provided![/red]: {row}")
        return (
            files_to_write,
            intents_cnt,
            phrases_cnt,
            entities_cnt,
            langs_used,
            nomatch_cnt,
            ml_disabled_str,
        )
    if "." in df_context:
        print(f"[red]Incorrect context name:[/red] [blue]{df_context}[/blue]")
    language = language.lower()
    dtmf_only: bool = False
    default_language: str = "en"
    if language == "dtmf":
        dtmf_only = True
        language = default_language

    if language not in {"en", "es", "fr", "dtmf"}:
        print(
            f"[red]Invalid language:[/red] [yellow]'{language}'[/yellow] for [blue]{df_intent}[/blue], using [yellow]'{default_language}'[/yellow] as default."
        )
        language = default_language

    langs_used = language  # store for return

    if not action:
        print(f"[red]No action provided![/red]: {row}")
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

    # dtmf value is optional, unless language is dtmf
    if dtmf_only and not dtmf_value:
        print(f"[red]No DTMF value provided![/red]: {row}")
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
        if not (
            set(dtmf_list).issubset(
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "#", "*"]
            )
        ):
            print(f"[red]INVALID DTMF VALUE! [blue]{dtmf_list}[/blue][/red]")

    if not machine_learning:
        machine_learning = "TRUE"  # default to true
    machine_learning = machine_learning.lower()
    if machine_learning not in {"true", "false"}:
        print(
            f"Machine Learning value needs to be [green]TRUE[/green] or [red]FALSE![/red]: {row}"
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
    output_file_path: Path = Path(default_path, "intents")
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
    intent_data["auto"] = machine_learning
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
    phrase_file_path: Path = Path(default_path, "Training Phrases", language)
    phrase_file_path = (
        Path(phrase_file_path, "NL") if mode == "NL" else phrase_file_path
    )

    if not phrase_file_path.exists():
        print(
            f"\n[red]Phrase file path [blue]{phrase_file_path}[/blue] does not exist![/red]\nCreating Path...\n"
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
        phrase_file: Path = Path(f"{action}.txt")
        phrase_file_path = Path(phrase_file_path, phrase_file)
        if phrase_file_path.exists():
            with open(phrase_file_path, mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                rows = [row for row in reader if any(row)]  # Filter out empty rows
                for row in rows:
                    row_str: str = "".join(row)  # convert to string
                    phrase_data: dict = json.loads(phrase_json)
                    phrase_data["id"] = str(uuid.uuid4())
                    (entity_list, temp_phrase_list) = utils.check_phrase_for_entity(
                        row_str
                    )
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
                                (ent_type, ent_name, ent_value, ent_required) = (
                                    utils.check_alias(entity_code[0])
                                )
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
        else:
            # don't print when nomatch is the file
            if not str(phrase_file) == "nomatch.txt":
                (
                    print(
                        f"\n[red]Phrase file [blue]{phrase_file}[/blue] does not exist in {phrase_file_path}![/red]\n"
                    )
                    if not test
                    else None
                )

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
    config: Path, vertical: str, context: str, lowercase: bool, quiet: bool, test: bool
) -> None:
    """Builds a config file for NL intent creation. It creates the file by reading the existing NL directories
    looking for text file corresponding the to intent names. These files contain training phrases for the
    intent the same as the directed dialog intent creation.

    Args:
        config (Path): name of the config file to create
        vertical (str): vertical abbreviation used in the intent names
        context (str): context used to reference all the intents at the same time
        lowercase (bool): flag to adjust the action to be lowercase and is only used by specific clients
        quiet (bool): Suppress most standard output to terminal.
    """
    # check if config file contains a path, the training phrases will match the config location
    (config_file_path, config_file_name, temp_file_extension) = utils.check_for_path(
        config
    )

    nl_table = Table(
        "Building Config",
        "Vertical",
        "Context",
        title="",
        box=box.ROUNDED,
    )
    table_row: list = [
        f"{config_file_name}",
        f"{vertical}",
        f"{context}",
    ]

    if lowercase:
        nl_table.add_column("Lowercase")
        table_row.append(f"[cyan]{lowercase}[/cyan]")

    # set phrase file path
    phrase_file_path: Path = Path(config_file_path, "Training Phrases")
    if not phrase_file_path.exists():
        print(
            f"[red]Phrase file path [blue]{phrase_file_path}[/blue] does not exist![/red]"
        )
        return

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
    config.unlink() if config.exists() else None

    # build the intent file
    for lang in sorted(languages_used):
        lang_path: Path = Path(lang, "NL")
        lang = Path(lang.stem)
        files_to_add: list = []
        entity_dict: dict = {}
        entity_set: set = set()
        filenames: list = [item.name for item in lang_path.iterdir() if item.is_file()]
        for filename in filenames:
            filepath = Path(lang_path, filename)
            if filepath.is_file() and filename.endswith(".txt"):
                files_to_add.append(Path(filename))

                # read phrase files looking for entities
                with open(filepath, mode="r", encoding="utf-8") as file:
                    reader = csv.reader(file)
                    rows = [row for row in reader if any(row)]  # Filter out empty rows
                    for row in rows:
                        row = "".join(row)  # convert to string
                        (entity_list, phrase_list) = utils.check_phrase_for_entity(row)
                        if entity_list:
                            for entity in entity_list:
                                # add to set to only keep unique entities
                                entity_set.add(str(entity))
                            # add them to dictionary to pull out later by filename
                            entity_dict[Path(filename)] = entity_set

        with open(config, mode="a", encoding="utf-8") as config_file:
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
                    intent = intent.rstrip("^")

                # if ACTION ends in "-NM", the action changes to 'nomatch', and the intent name is adjusted
                # and because we're already returning as a lowercase 'nomatch', the lowercase option is redundant
                if action.endswith("-NM"):
                    # intent = f"{vertical}.{str(action).rstrip("-NM").capitalize()}"
                    intent = intent.rstrip("-Nm")
                    config_file.write(
                        f"{intent},{context},{lang},nomatch,{entity},{dtmf},{str(ml).upper()}\n"
                    )

                elif lowercase:
                    # write it lowercase first, then with uppercase name
                    config_file.write(
                        f"{intent},{context},{lang},{action.lower()},{entity},{dtmf},{str(ml).upper()}\n"
                    )

                config_file.write(
                    f"{intent},{context},{lang},{action},{entity},{dtmf},{str(ml).upper()}\n"
                )

    nl_table.add_column("Status")
    if not config.exists():
        table_row.append("[red]FAIL[/red]")
        print("[red][bold]Abort processing...[/bold][/red]")
        exit()
    else:
        table_row.append("[green]COMPLETE[/green]")

    nl_table.add_row(*table_row)
    console = Console()
    console.print(nl_table) if not quiet else None

    # check for duplicate phrases in the training phrases
    for lang in sorted(languages_used):
        lang_path: Path = Path(lang, "NL")
        lang = Path(lang.stem)
        duplicates: set = utils.check_for_duplicate_phrases(lang_path, str(lang), quiet)
        if duplicates:
            duplicate_table = Table(
                f"[red]Duplicate phrases found in [yellow]'{lang}'[/yellow][/red]",
                box=box.ROUNDED,
            )
            for dup in duplicates:
                duplicate_table.add_row(dup)
            console = Console()
            console.print(duplicate_table)

            while True:
                continue_yn: str = input("\nContinue processing files Y/N? ")
                try:
                    continue_flag: int = utils.strtobool(continue_yn)
                    if continue_flag:
                        break
                    else:
                        print("\n[bold][red]Abort processing...[/bold][/red]")
                        exit()  # quit the program, after notifying of the duplications
                except ValueError:
                    print("Invalid input. Please enter 'yes' or 'no'")
