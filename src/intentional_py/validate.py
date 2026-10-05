"""Validate project structure and configuration files.

preflight_config holds the config checks shared by the builds and the validate
command; validate also checks the Training Phrases folders and config files exist.
"""

import csv
import re
from pathlib import Path

from intentional_py import models, utils
from intentional_py.reporting import Check, Reporter, ValidateResult

MAX_LINES_LISTED = 5


def read_config_rows(config: Path) -> list[list[str]]:
    """Read a config file's non-blank rows."""
    with (
        utils.file_errors(config),
        config.open(mode="r", encoding="utf-8", newline="") as config_file,
    ):
        return [
            row for row in csv.reader(config_file) if any(cell.strip() for cell in row)
        ]


def preflight_config(
    config: Path,
    base_path: Path,
    mode: str | None,
    rules: models.NamingRules | None = None,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
) -> tuple[list[list[str]], list[str], list[str], list[models.RemovalRow]]:
    """Validate and normalize a config file's rows before a build starts; see check_rows."""
    return check_rows(
        read_config_rows(config), base_path, mode, rules, layout, languages
    )


def check_rows(
    rows: list[list[str]],
    base_path: Path,
    mode: str | None,
    rules: models.NamingRules | None = None,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
) -> tuple[list[list[str]], list[str], list[str], list[models.RemovalRow]]:
    """Validate and normalize config rows.

    Missing required values and malformed rows are fatal. Values that the
    builder can safely default are normalized and returned as warnings, as are
    problems found in the phrase files. A row that exactly matches an earlier
    row (an accidental copy-paste) is dropped before any other check runs.
    With mode None, phrase files may be in either the DD or the NL folder.
    rules (NamingRules | None): intent/context naming rules; defaults to the
        original hardcoded behavior when not given (see models.NamingRules).
    layout (ProjectLayout | None): project folder/file names; defaults to the
        original hardcoded layout when not given.
    languages (LanguageSettings | None): supported language codes/names; defaults to
        every Dialogflow ES language when not given (see models.LanguageSettings).

    Returns a 4th list of RemovalRow, for rows starting with '-' or '--' - these are
    never built; see build_intents.py for how they remove existing output instead.
    """
    layout = layout or models.ProjectLayout()
    languages = languages or models.LanguageSettings()
    fatal_errors: list[str] = []
    warnings: list[str] = []
    normalized_rows: list[list[str]] = []
    removals: list[models.RemovalRow] = []
    # (language, context, phrase) -> {intent: row number}, for the same-context duplicate check
    phrase_owners: dict[tuple[str, str, str], dict[str, int]] = {}
    intent_languages: dict[str, list[tuple[int, str]]] = {}
    first_intent_rows: dict[str, tuple[int, list[str]]] = {}
    seen_rows: dict[tuple[str, ...], int] = {}

    for row_number, row in enumerate(rows, start=1):
        if len(row) not in (6, 7):
            fatal_errors.append(
                f"Row {row_number}: expected 6 or 7 values, found {len(row)}."
            )
            continue

        # the machine learning column is optional, for configs written before it existed
        normalized_row = [cell.strip() for cell in row] + [""] * (7 - len(row))
        intent, context, language, action, entities, _dtmf_value, _machine_learning = (
            normalized_row
        )

        # ConfigRow runs the per-row rules (required fields, language, DTMF, machine learning);
        # cross-row and filesystem checks below stay here, since they involve more than one row
        parsed = models.ConfigRow.from_csv_row(row, row_number, rules, languages)
        language = parsed.language
        normalized_row[2] = parsed.language
        normalized_row[6] = parsed.machine_learning_text

        first_seen = seen_rows.setdefault(tuple(normalized_row), row_number)
        if first_seen != row_number:
            # an exact duplicate is dropped before its own errors/warnings are recorded, so an
            # accidental copy-paste of an already-invalid row doesn't report the same problem twice
            warnings.append(
                f"Row {row_number}: identical to row {first_seen}; the duplicate was dropped."
            )
            continue

        fatal_errors.extend(parsed.errors)
        warnings.extend(parsed.warnings)

        if parsed.removal:
            # never built, and excluded from the default-language-row synthesis below -
            # a lone removal row shouldn't cause a brand new build row to be invented
            removals.append(
                models.RemovalRow(
                    row_number=row_number,
                    intent=parsed.intent,
                    language=language,
                    confirmed=parsed.remove_confirmed,
                )
            )
            continue

        if intent:
            intent_languages.setdefault(intent, []).append((row_number, language))

        if action and language != "dtmf" and action != "nomatch":
            phrase_path = base_path / layout.training_phrases_dir / language
            phrase_dirs = {
                "DD": [phrase_path],
                "NL": [phrase_path / layout.nl_subfolder],
            }.get(mode, [phrase_path, phrase_path / layout.nl_subfolder])
            phrase_files = [
                utils.find_phrase_file(path, action) for path in phrase_dirs
            ]
            found = [
                phrase_file for phrase_file in phrase_files if phrase_file.exists()
            ]
            if not found:
                warnings.append(
                    f"Row {row_number}: phrase file '{phrase_files[0]}' was not found; "
                    "the intent will be generated without those phrases."
                )
            else:
                phrases = _read_phrases(found[0])
                warnings.extend(
                    f"Row {row_number}: {problem}"
                    for problem in _phrase_problems(found[0], phrases, entities)
                )
                # NL builds ask about duplicate phrases themselves, and NL intents share a context
                if mode != "NL" and intent:
                    for phrase in phrases:
                        key_phrase = " ".join(phrase.casefold().split())
                        for single_context in filter(
                            None, (c.strip() for c in context.split("|"))
                        ):
                            owners = phrase_owners.setdefault(
                                (language, single_context, key_phrase), {}
                            )
                            owners.setdefault(intent, row_number)

        normalized_rows.append(normalized_row)
        if intent:
            first_intent_rows.setdefault(intent, (row_number, normalized_row))

    for intent, language_rows in intent_languages.items():
        rows_by_language: dict[str, list[int]] = {}
        for row_number, language in language_rows:
            rows_by_language.setdefault(language, []).append(row_number)
        for language, row_numbers in rows_by_language.items():
            if len(row_numbers) > 1:
                # owner's row keeps the intent definition (build_intents.write_intent mirrors
                # this by picking the first row); winner's row is the one whose phrases end up
                # in the usersays file, since build_intents writes it once per row, last wins
                winner = row_numbers[-1]
                owner = row_numbers[0]
                others = ", ".join(str(number) for number in row_numbers[:-1])
                warnings.append(
                    f"Row {winner}: intent '{intent}' also has language '{language}' "
                    f"in row(s) {others}; its phrases will be used, but row {owner}'s "
                    "context, action, priority, entities and machine learning are kept."
                )
        if not any(
            language == languages.default_language for _, language in language_rows
        ):
            row_number, source_row = first_intent_rows[intent]
            language = source_row[2]
            english_row = source_row.copy()
            english_row[2] = languages.default_language
            normalized_rows.append(english_row)
            # "English" and "an" when the default is still 'en', same wording as before
            # this was configurable; generalizes to whatever default_language is now
            name = languages.languages.get(
                languages.default_language, languages.default_language
            )
            article = "an" if name[:1].lower() in "aeiou" else "a"
            warnings.append(
                f"Row {row_number}: intent '{intent}' has no {name} "
                f"('{languages.default_language}') row; {article} {name} row will be "
                f"synthesized from this row ('{language}')."
            )
            action = english_row[3]
            if action and action != "nomatch":
                phrase_path = (
                    base_path / layout.training_phrases_dir / languages.default_language
                )
                phrase_dirs = {
                    "DD": [phrase_path],
                    "NL": [phrase_path / layout.nl_subfolder],
                }.get(mode, [phrase_path, phrase_path / layout.nl_subfolder])
                phrase_files = [
                    utils.find_phrase_file(path, action) for path in phrase_dirs
                ]
                found = [path for path in phrase_files if path.exists()]
                if not found:
                    warnings.append(
                        f"Row {row_number}: synthesized {name} row for '{intent}': phrase file "
                        f"'{phrase_files[0]}' was not found; the {name} intent "
                        "will be generated without those phrases."
                    )
                else:
                    phrases = _read_phrases(found[0])
                    warnings.extend(
                        f"Row {row_number}: synthesized {name} row for '{intent}': {problem}"
                        for problem in _phrase_problems(
                            found[0], phrases, english_row[4]
                        )
                    )
    warnings.extend(_duplicate_phrase_warnings(phrase_owners))

    removals_by_intent: dict[str, list[models.RemovalRow]] = {}
    for removal in removals:
        removals_by_intent.setdefault(removal.intent, []).append(removal)
    for intent, intent_removals in removals_by_intent.items():
        default_removals = [
            r for r in intent_removals if r.language == languages.default_language
        ]
        if not default_removals:
            continue
        # removing the default-language row removes the whole intent; warn if another
        # language is still being built for it and wasn't itself marked for removal
        still_built = sorted(
            {language for _row_number, language in intent_languages.get(intent, [])}
        )
        if still_built:
            warnings.append(
                f"Row {default_removals[0].row_number}: removing '{intent}' "
                f"('{languages.default_language}') also removes its "
                f"{', '.join(still_built)} files, which {'is' if len(still_built) == 1 else 'are'} "
                "not marked for removal."
            )
    return normalized_rows, fatal_errors, warnings, removals


def _read_phrases(phrase_file: Path) -> list[str]:
    with utils.file_errors(phrase_file), phrase_file.open(encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def _entity_name(entity: str) -> str:
    """The entity type without its alias ([...]) or required (*) markers, for comparison."""
    return entity.split("[", 1)[0].strip().rstrip("*").strip().casefold()


def _lines(numbers: list[int]) -> str:
    shown = ", ".join(str(number) for number in numbers[:MAX_LINES_LISTED])
    more = len(numbers) - MAX_LINES_LISTED
    return f"line{'s' if len(numbers) > 1 else ''} {shown}" + (
        f" and {more} more" if more > 0 else ""
    )


def _phrase_problems(phrase_file: Path, phrases: list[str], entities: str) -> list[str]:
    """Entity tag typos and unlisted entities in one phrase file, grouped per problem."""
    if not phrases:
        return [
            f"phrase file '{phrase_file.name}' is empty; the intent will have no phrases."
        ]
    listed = {_entity_name(entity) for entity in entities.split("|") if entity.strip()}
    unmatched: list[int] = []
    no_separator: list[int] = []
    unlisted: dict[str, list[int]] = {}
    for line_number, phrase in enumerate(phrases, start=1):
        tags = re.findall(r"<([^<>]*)>", phrase)
        if "<" in re.sub(r"<[^<>]*>", "", phrase) or ">" in re.sub(
            r"<[^<>]*>", "", phrase
        ):
            unmatched.append(line_number)
        for tag in tags:
            entity, separator, text = tag.partition("|")
            if not separator or not entity.strip() or not text.strip():
                no_separator.append(line_number)
            elif _entity_name(entity) not in listed:
                unlisted.setdefault(entity.strip(), []).append(line_number)
    problems = []
    name = phrase_file.name
    if unmatched:
        problems.append(f"'{name}' has an unmatched '<' or '>' on {_lines(unmatched)}.")
    if no_separator:
        problems.append(
            f"'{name}' has an entity tag without the <entity|text> form on {_lines(no_separator)}."
        )
    for entity, line_numbers in unlisted.items():
        problems.append(
            f"'{name}' uses the entity '{entity}' on {_lines(line_numbers)}, "
            "but it is not in the row's Entities column."
        )
    return problems


def _duplicate_phrase_warnings(
    phrase_owners: dict[tuple[str, str, str], dict[str, int]],
) -> list[str]:
    """One warning per pair of intents that share phrases in the same language and context."""
    shared: dict[tuple[int, str, int, str, str, str], list[str]] = {}
    for (language, context, phrase), owners in phrase_owners.items():
        if len(owners) < 2:
            continue
        ordered = sorted(owners.items(), key=lambda owner: owner[1])
        first_intent, first_row = ordered[0]
        for intent, row in ordered[1:]:
            shared.setdefault(
                (row, intent, first_row, first_intent, context, language), []
            ).append(phrase)
    warnings = []
    for (row, intent, first_row, first_intent, context, language), phrases in sorted(
        shared.items()
    ):
        example = phrases[0]
        count = f"{len(phrases)} phrases" if len(phrases) > 1 else "a phrase"
        warnings.append(
            f"Row {row}: '{intent}' shares {count} (e.g. '{example}') with '{first_intent}' "
            f"(row {first_row}), which has the same context '{context}' and language '{language}'."
        )
    return warnings


def validate(
    config: Path,
    base_dir: Path,
    reporter: Reporter,
    rules: models.NamingRules | None = None,
    layout: models.ProjectLayout | None = None,
    languages: models.LanguageSettings | None = None,
) -> ValidateResult:
    """Validates the directories and files for the project.

    Args:
        config (Path): config file to use for validation; the standard config files are used if it does not exist
        base_dir (Path): Project directory containing the training phrases and standard config files.
        reporter (Reporter): Receives messages.
        rules (NamingRules | None): intent/context naming rules; defaults to the
            original hardcoded behavior when not given.
        layout (ProjectLayout | None): project folder/file names; defaults to the
            original hardcoded layout when not given.
        languages (LanguageSettings | None): supported language codes/names; defaults to
            the original hardcoded set (en/es/fr) when not given.
    """
    layout = layout or models.ProjectLayout()
    languages = languages or models.LanguageSettings()
    result = ValidateResult()
    reporter.message("info", "[yellow]Validating directories and files[/yellow]\n")

    config_list: list = []
    if not config.is_file():
        # check both standard config files
        result.used_standard_configs = True
        config_list.extend(
            [
                Path(base_dir, layout.dd_config),
                Path(base_dir, layout.nl_config),
            ]
        )
    else:
        # check for this config file
        config_list.append(config)

    # check each config file now (not just whether it exists), so the directory check
    # below knows which languages are actually used - a supported language that isn't
    # in the config doesn't need a folder yet, it's only required once it's used
    used_languages: set[str] = set()
    # (file name, exists, ok, details)
    config_checks: list[tuple[str, bool, bool, list[str]]] = []
    for file in config_list:
        if not file.is_file():
            config_checks.append((file.name, False, False, []))
            continue
        # the same checks a build runs, so validate reports exactly what a build would
        rows, errors, warnings, removals = preflight_config(
            file, base_dir, None, rules, layout, languages
        )
        used_languages.update(row[2] for row in rows if row[2] != "dtmf")
        if not rows and not errors:
            errors = ["The config file does not contain data."]
        details = [f"Error: {error}" for error in errors]
        details += [f"Warning: {warning}" for warning in warnings]
        details += [
            f"Warning: Row {removal.row_number}: '{removal.intent}' "
            f"('{removal.language}') is marked for removal"
            + ("" if removal.confirmed else " and will ask for confirmation first")
            + "."
            for removal in removals
        ]
        config_checks.append((file.name, True, not errors, details))

    # check for directory structure - only for languages actually used in the config(s)
    # above, not every supported language, since an unused one doesn't need a folder yet
    phrase_path = Path(base_dir, layout.training_phrases_dir)
    phrases_exist = phrase_path.exists()
    result.directories.append(
        Check(f"{layout.training_phrases_dir} path", phrases_exist)
    )
    if phrases_exist:
        for code in sorted(used_languages, key=lambda c: languages.languages.get(c, c)):
            name = languages.languages.get(code, code)
            lang_path = Path(phrase_path, code)
            lang_exists = lang_path.exists()
            result.directories.append(Check(f"{name} path", lang_exists))
            if lang_exists:
                result.directories.append(
                    Check(
                        f"{name} {layout.nl_subfolder} path",
                        Path(lang_path, layout.nl_subfolder).exists(),
                    )
                )

    for file_name, exists, ok, details in config_checks:
        result.config_files.append(Check(f"Checking for {file_name}", exists))
        if exists:
            result.configs.append(Check(f"Validating {file_name}", ok, details))

    return result
