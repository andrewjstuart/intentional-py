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

from intentional_py import compare as comparing
from intentional_py import exceptions, models, utils
from intentional_py import validate as validating
from intentional_py.reporting import BuildResult, CompareResult, PackageResult, Reporter


def intents(
    mode: str,
    config: Path,
    base_dir: Path,
    reporter: Reporter,
    clean: bool = False,
    rules: models.NamingRules | None = None,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
    export: Path | None = None,
    package_style: str = "restore",
) -> BuildResult:
    """Build the intents described in the config file, after the preflight checks in validate.py.

    Args:
        mode (str): Directed dialog (DD) or Natural Language (NL), which selects the phrase folder.
        config (Path): The name of the config file to use to build intents.
        base_dir (Path): Project directory containing the training phrases and receiving the intents.
        reporter (Reporter): Receives messages and progress.
        clean (bool): Zip and remove everything in the intents folder before writing.
        rules (NamingRules | None): intent/context naming rules; defaults to the
            original hardcoded behavior when not given.
        layout (ProjectLayout | None): project folder/file names; defaults to the
            original hardcoded layout when not given.
        languages (LanguageSettings | None): supported language codes/names; defaults to
            the original hardcoded set (en/es/fr) when not given.
        export (Path | None): an agent export zip to also merge this same build into,
            in one step instead of a separate Package run; the intents folder is
            always written the same way either way. Nothing zip-related happens
            without this - the default is still just the intents folder.
        package_style (str): "restore" (default) or "import"; see package_export().
            Only meaningful when `export` is given.

    Returns:
        BuildResult: counts, changes since the previous build, the output folder, and
        (when `export` is given) the merge into it as `package`.
    """
    layout = layout or models.ProjectLayout()
    languages = languages or models.LanguageSettings()
    files_to_write, result, t1_start, removals = _generate(
        mode, config, base_dir, reporter, rules, layout, languages
    )
    output_dir = Path(base_dir, layout.intents_dir)

    previous = (
        [path for path in output_dir.glob("*") if path.is_file()]
        if output_dir.is_dir()
        else []
    )
    if any(path.suffix == ".json" for path in previous):
        try:
            result.changes = comparing.compare(
                _summarize(files_to_write),
                comparing.load(output_dir),
                "the previous build",
            )
        except exceptions.IntentionalException as error:
            reporter.message(
                "warning", f"Could not compare with the previous build: {error}"
            )
    if clean and previous:
        stamp = utils.timestamp()
        result.backup = Path(base_dir, f"{layout.intents_dir}_{stamp}.zip")
        with utils.file_errors(result.backup):
            utils.zip_directory(output_dir, result.backup, previous)
            for path in previous:
                path.unlink()

    result.removed = _remove_marked_intents(removals, output_dir, reporter, languages)

    output_dir.mkdir(parents=True, exist_ok=True)
    for file, data in files_to_write.items():
        with utils.file_errors(file), open(file, mode="w", encoding="utf-8") as output:
            json.dump(data, output, indent=4)

    result.output_dir = output_dir
    if export is not None:
        result.package = _merge_into_export(
            files_to_write, removals, export, reporter, languages, package_style
        )
    result.elapsed = perf_counter() - t1_start
    return result


def compare_build(
    mode: str,
    config: Path,
    base_dir: Path,
    source: Path,
    reporter: Reporter,
    rules: models.NamingRules | None = None,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
) -> CompareResult:
    """Compare what the config would build with an agent export or intents folder; writes nothing."""
    files_to_write, _result, t1_start, _removals = _generate(
        mode, config, base_dir, reporter, rules, layout, languages
    )
    result = comparing.compare(
        _summarize(files_to_write), comparing.load(source), str(source)
    )
    result.elapsed = perf_counter() - t1_start
    return result


def package_export(
    base_dir: Path,
    export: Path,
    reporter: Reporter,
    layout: models.ProjectLayout | None = None,
    style: str = "restore",
) -> PackageResult:
    """Merge the intents already built in base_dir's intents folder into a copy of an
    agent export zip, matching one of Dialogflow ES's own Import/Restore actions:

    - "restore" (default): a complete copy of the export, since Restore replaces the
      whole agent - anything missing is deleted. New/changed intents are added;
      everything else (including any intent only in the export, never built here)
      carries over unchanged.
    - "import": a partial zip of just the new/changed intents, since Import only adds
      or overwrites and never deletes; agent.json/package.json aren't included, since
      this tool never writes them.

    Unlike intents()'s own `export`/`package_style` parameters, this doesn't build
    anything - DD and NL builds both write to the same intents folder, so there's no
    config or mode to pick here, just whatever is already there. Build first if the
    intents folder needs updating. There's no config here to carry a '-'/'--' row's
    intent forward either, so an intent removed from a past build stays in the export
    unless deleted from it by hand (or from `restore`-style, with `-`/`--` still in
    the config, via intents()'s combined build-and-merge instead) - packaging on its
    own never deletes anything already in the export that it didn't just replace.

    The export itself is never modified; the copy is written next to it with the style
    and a timestamp appended to its name.
    """
    layout = layout or models.ProjectLayout()
    output_dir = Path(base_dir, layout.intents_dir)
    if not output_dir.is_dir():
        raise exceptions.FileSystemError(
            f"[red]No intents folder to package: [blue]{output_dir}[/blue][/red]\n"
            "Build the intents first."
        )
    t1_start = perf_counter()
    files_to_write = _read_existing_intents(output_dir)
    if not files_to_write:
        raise exceptions.ValidationError(
            f"[red]The intents folder is empty[/red]: [cyan]{output_dir}[/cyan]\n"
            "Build the intents first."
        )
    result = _merge_into_export(
        files_to_write, [], export, reporter, models.LanguageSettings(), style
    )
    result.elapsed = perf_counter() - t1_start
    return result


def _read_existing_intents(output_dir: Path) -> dict[Path, dict]:
    """Every intent/usersays JSON file already in an intents folder, keyed by path -
    for packaging a build that's already up to date, without rebuilding it."""
    files: dict[Path, dict] = {}
    for path in sorted(output_dir.glob("*.json")):
        with utils.file_errors(path):
            files[path] = json.loads(path.read_text(encoding="utf-8-sig"))
    return files


def _merge_into_export(
    files_to_write: dict,
    removals: list[models.RemovalRow],
    export: Path,
    reporter: Reporter,
    languages: models.LanguageSettings,
    style: str,
) -> PackageResult:
    """Shared by intents() (building and packaging in one step) and package_export()
    (packaging an existing build's output without rebuilding it): the actual zip merge,
    see package_export()'s docstring for the "restore"/"import" styles.
    """
    diff = comparing.compare(
        _summarize(files_to_write), comparing.load(export), str(export)
    )

    prefix, names = comparing.export_contents(export)
    name_set = set(names)
    marked_intents = {removal.intent for removal in removals}

    result = PackageResult(source=export, style=style)
    result.added = diff.added
    result.changed = diff.changed
    result.unchanged = diff.unchanged
    result.unmarked = sorted(
        name for name in diff.removed if name not in marked_intents
    )

    output = export.with_name(
        f"{export.stem}_{style}_{utils.timestamp()}{export.suffix}"
    )
    if style == "import":
        if marked_intents:
            result.needs_manual_removal = sorted(marked_intents)
            reporter.message(
                "warning",
                "[yellow]Dialogflow's Import can't delete intents[/yellow]; remove "
                + ", ".join(result.needs_manual_removal)
                + " from the agent by hand, or use --style restore instead.",
            )
        comparing.write_import_zip(files_to_write, prefix, output)
    else:
        targets = [
            (removal, arcnames)
            for removal in removals
            if (
                arcnames := comparing.removal_arcnames(
                    removal, prefix, name_set, languages
                )
            )
        ]
        _confirm_removals(targets, reporter, lambda name: Path(name).name)
        removed_arcnames: set[str] = set()
        for removal, arcnames in targets:
            for arcname in arcnames:
                removed_arcnames.add(arcname)
                reporter.message(
                    "info",
                    f"[yellow]Removed[/yellow] {Path(arcname).name} (row {removal.row_number})",
                )
        result.removed = sorted(Path(name).name for name in removed_arcnames)
        comparing.merge_export(export, files_to_write, removed_arcnames, prefix, output)
    result.output = output
    return result


def _summarize(files_to_write: dict) -> dict:
    return comparing.summarize(
        {Path(file).name: data for file, data in files_to_write.items()}
    )


def _removal_targets(
    removal: models.RemovalRow, output_dir: Path, languages: models.LanguageSettings
) -> list[Path]:
    """Existing output files a removal row refers to: the whole intent (shared
    definition + every language's usersays file) for the default language, or just
    one language's usersays file otherwise."""
    if removal.language == languages.default_language:
        found = [
            path for path in (output_dir / f"{removal.intent}.json",) if path.exists()
        ]
        if output_dir.is_dir():
            found += sorted(output_dir.glob(f"{removal.intent}_usersays_*.json"))
        return found
    candidate = output_dir / f"{removal.intent}_usersays_{removal.language}.json"
    return [candidate] if candidate.exists() else []


def _confirm_removals(
    targets: list[tuple[models.RemovalRow, list]],
    reporter: Reporter,
    name_of,
) -> None:
    """Ask once for every target whose row isn't already confirmed (an unconfirmed '-'
    row); raises if declined. No-op when every target is '--' or already confirmed.
    Shared by _remove_marked_intents() (filesystem paths) and package_export() (zip
    entry names), via `name_of` to get a display name from either.
    """
    to_confirm = [
        (removal, items) for removal, items in targets if not removal.confirmed
    ]
    if not to_confirm:
        return
    details = [
        f"'{removal.intent}' ('{removal.language}'): "
        + ", ".join(name_of(item) for item in items)
        for removal, items in to_confirm
    ]
    if not reporter.confirm("Remove the intents marked for removal", details):
        raise exceptions.IntentionalException(
            "\n[bold][red]Abort processing...[/bold][/red]\n"
            "User declined to remove the marked intents"
        )


def _remove_marked_intents(
    removals: list[models.RemovalRow],
    output_dir: Path,
    reporter: Reporter,
    languages: models.LanguageSettings,
) -> list[str]:
    """Delete existing output for rows starting with '-' or '--'; a lone '-' (easier to
    mistake for a typo) asks to confirm first, '--' removes without asking."""
    targets = [
        (removal, paths)
        for removal in removals
        if (paths := _removal_targets(removal, output_dir, languages))
    ]
    if not targets:
        return []

    _confirm_removals(targets, reporter, lambda path: path.name)

    removed: list[str] = []
    for removal, paths in targets:
        for path in paths:
            with utils.file_errors(path):
                path.unlink(missing_ok=True)
            removed.append(path.name)
            reporter.message(
                "info",
                f"[yellow]Removed[/yellow] {path.name} (row {removal.row_number})",
            )
    return removed


def _generate(
    mode: str,
    config: Path,
    base_dir: Path,
    reporter: Reporter,
    rules: models.NamingRules | None = None,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
) -> tuple[dict, BuildResult, float, list[models.RemovalRow]]:
    """Check the config and create every intent's JSON in memory, keyed by output file."""
    layout = layout or models.ProjectLayout()
    languages = languages or models.LanguageSettings()
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
    rows, fatal_errors, warnings, removals = validating.preflight_config(
        config, base_dir, mode, rules, layout, languages
    )
    for warning in warnings:
        reporter.message("warning", f"[yellow]Warning:[/yellow] {warning}")
    if fatal_errors:
        raise exceptions.ValidationError(
            "Configuration validation failed:\n"
            + "\n".join(f"- {error}" for error in fatal_errors)
        )

    t1_start = perf_counter()
    if len(rows) == 0 and len(removals) == 0:
        raise exceptions.ValidationError(
            f"[red]Config file does not contain data[/red]: [cyan]{config}[/cyan]"
        )

    intents_with_english = {
        row[0] for row in rows if row[2] == languages.default_language
    }
    first_row_for_intent: dict[str, int] = {}
    first_english_row_for_intent: dict[str, int] = {}
    for row_number, row in enumerate(rows):
        first_row_for_intent.setdefault(row[0], row_number)
        if row[2] == languages.default_language:
            first_english_row_for_intent.setdefault(row[0], row_number)

    label = f"Creating [green]{mode}[/green] intents using [cyan]{config}[/cyan]"
    for row_number, row in enumerate(reporter.track(rows, label)):
        # only the intent's first English row (or its first row overall, if it has no
        # English row) owns the shared definition (context, action, priority, entities,
        # machine learning); every row still writes its own phrases, so a repeated
        # intent+language row can swap in different phrases without changing the intent
        write_intent = (
            row[2] == languages.default_language
            and first_english_row_for_intent[row[0]] == row_number
        ) or (
            row[0] not in intents_with_english
            and first_row_for_intent[row[0]] == row_number
        )
        (
            data,
            temp_intents,
            temp_phrases,
            temp_entities,
            temp_lang,
            temp_nomatch,
            temp_ml,
        ) = create_json(
            models.ConfigRow.from_csv_row(row, row_number + 1, rules, languages),
            mode,
            base_dir,
            reporter,
            write_intent,
            layout,
            languages,
        )

        # a duplicate (intent, language) row's phrases replace the earlier row's phrases
        # rather than merging with them, so they are not doubled; the intent itself still
        # keeps its first row's definition (see write_intent above and validate.py's warning)
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
    return files_to_write, result, t1_start, removals


def create_json(
    row: models.ConfigRow,
    mode: str,
    default_path: Path,
    reporter: Reporter,
    write_intent: bool = True,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
) -> tuple[dict, int, int, int, str, int, str]:
    """Create the JSON for one config row, which must already have passed preflight_config.

    Args:
        row (models.ConfigRow): one config row, already validated and normalized.
        mode (str): Directed dialog (DD) or Natural Language (NL), which selects the phrase folder
        default_path (Path): project directory containing the training phrases and receiving the intents
        reporter (Reporter): Receives messages.
        write_intent (bool): Whether this row owns the shared intent definition file.
        layout (ProjectLayout | None): project folder/file names; defaults to the
            original hardcoded layout when not given.
        languages (LanguageSettings | None): supported language codes/names; defaults to
            the original hardcoded set (en/es/fr) when not given.

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
    layout = layout or models.ProjectLayout()
    languages = languages or models.LanguageSettings()
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
        language = languages.default_language
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
    output_file_path: Path = Path(default_path, layout.intents_dir)

    # safe_join rejects an intent name that would write outside output_file_path (e.g. '../');
    # models.ConfigRow already rejects a '/' or '\' in the name before this ever runs
    output_file = utils.safe_join(output_file_path, f"{df_intent}.json")
    output_phrase_file = utils.safe_join(
        output_file_path, f"{df_intent}_usersays_{language}.json"
    )

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
    if write_intent:
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

        files_to_write[output_file] = intent_data

    # set phrase file path
    phrase_file_path: Path = Path(default_path, layout.training_phrases_dir, language)
    phrase_file_path = (
        Path(phrase_file_path, layout.nl_subfolder)
        if mode == "NL"
        else phrase_file_path
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
            with (
                utils.file_errors(phrase_file_path),
                open(phrase_file_path, mode="r", encoding="utf-8") as file,
            ):
                reader = csv.reader(file)
                phrase_rows = [
                    phrase_row for phrase_row in reader if any(phrase_row)
                ]  # Filter out empty rows
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

    # this key is shared by every row with the same intent and language, so if a config
    # repeats one, only the last row processed for that pair ends up in the written file
    # (see write_intent above, and the duplicate-row warning in validate.py)
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
    config: Path,
    vertical: str,
    context: str,
    lowercase: bool,
    reporter: Reporter,
    layout: models.ProjectLayout | None = None,
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
        layout (ProjectLayout | None): project folder/file names; defaults to the
            original hardcoded layout when not given.
    """
    layout = layout or models.ProjectLayout()
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
    phrase_file_path: Path = Path(config_file_path, layout.training_phrases_dir)
    if not phrase_file_path.exists():
        raise exceptions.FileSystemError(
            f"[red]Phrase file path [blue]{phrase_file_path}[/blue] does not exist![/red]"
        )

    # determine languages available by the files available, and then which are used by the having text files
    languages_used: set = set()
    for lang in phrase_file_path.iterdir():
        lang_path: Path = Path(lang, layout.nl_subfolder)
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
        lang_path: Path = Path(lang, layout.nl_subfolder)
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
                with (
                    utils.file_errors(filepath),
                    open(filepath, mode="r", encoding="utf-8") as file,
                ):
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

        with (
            utils.file_errors(config),
            open(config, mode="a", encoding="utf-8") as config_file,
        ):
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
        lang_path: Path = Path(lang, layout.nl_subfolder)
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
