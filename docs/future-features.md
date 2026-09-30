# Future Features

Ideas that have been discussed but not built yet, with the steps to build each one. Add new ideas at the end, and move an idea to the [user guide](user-guide.md) once it is implemented.

- [Upload intents directly to Dialogflow](#upload-intents-directly-to-dialogflow)
- [Import zip merged into an agent export](#import-zip-merged-into-an-agent-export)
- [Code-signed Windows executables](#code-signed-windows-executables)
- [Author and validate entity types](#author-and-validate-entity-types)
- [Configurable supported language set](#configurable-supported-language-set)

---

## Upload intents directly to Dialogflow

**Status:** tabled. It needs Google Cloud credentials, sign-in and audit logging, which should be designed carefully.

**What it would do:** push the built intents straight into a Dialogflow ES agent, instead of exporting, importing and cleaning up by hand. It could also delete intents that are no longer in the config, after confirmation.

**Considerations**

- Access is through the Dialogflow ES API (`google-cloud-dialogflow`), which needs a Google Cloud project, the agent's project ID, and a signed-in user or service account with the **Dialogflow API Admin** (or Client) role.
- Credentials must never be stored in the repository or in `settings.json`. Prefer Google's own sign-in (`gcloud auth application-default login`) so the tool never handles a key file. If service-account keys are used, keep them outside the project folder.
- Changes made through the API are immediate, so a dry run (the existing `compare` feature) should always be shown and confirmed first.
- Every upload should be logged: who, when, which agent, and which intents were created, updated or deleted.
- Deleting intents is the riskiest part and should be a separate, explicit confirmation.

**Implementation steps**

1. Add an optional `dialogflow` extra in `pyproject.toml` with `google-cloud-dialogflow`, so the CLI and GUI work without it.
2. Add `src/intentional_py/upload.py`:
   - Connect with `dialogflow_v2.IntentsClient()` using Application Default Credentials.
   - List the agent's intents (`list_intents`, with the full intent view) and map them by display name.
   - Convert the built intent JSON into `dialogflow_v2.Intent` objects: training phrases with entity parts, parameters, input contexts, action, priority, and the ML setting.
   - Use `batch_update_intents` to create and update, and `batch_delete_intents` for removals.
3. Reuse `compare` to produce the change list, and require confirmation before anything is sent.
4. Add a CLI command, e.g. `intentional-cli upload --project-id <id> [--delete-missing] [--yes]`, and an **Upload** tab in the GUI that shows the comparison first.
5. Write an upload log file (JSON lines) in the project folder, and show a summary in the results panel.
6. Tests: mock the Dialogflow client and check the requests that would be sent. Never call the real API from the tests or the GitHub workflows.
7. Document the sign-in steps and the required roles in the user guide.

---

## Import zip merged into an agent export

**Status:** tabled. Needs a check of how the Dialogflow console's **Import** and **Restore** behave with a partial zip.

**What it would do:** take the current agent export, add or replace the intents from a build, and produce a new zip that can be imported, so the agent is not left missing the intents that this config does not build.

**Considerations**

- **Restore** replaces the whole agent with the zip, which would delete any intent not in it. That is why a zip of only the new intents is not safe.
- **Import** is documented as adding new intents and replacing ones with the same name, while keeping the rest. Verify this with a test agent first; if it holds, a zip of only the built intents plus the export's `agent.json` and `package.json` may be enough.
- Intents that are no longer used still have to be deleted from the agent by hand. The `compare` results already list them as "only in the export".
- Entities (`entities/`) and agent settings in the export must be kept unchanged.

**Implementation steps**

1. Test **Import** and **Restore** with a copy of an agent to confirm which one keeps unrelated intents.
2. Add `merge_export(export_zip, intents_dir, output_zip)` to `compare.py` or a new module:
   - Copy every file from the export zip except the `intents/` files being replaced.
   - Add the built intent and usersays files, matched by intent name, so the export's copies are replaced.
   - Keep `agent.json`, `package.json` and `entities/` from the export as they are.
3. Add a CLI command, e.g. `intentional-cli package --export agent.zip --output agent_updated.zip`, and a button on the **Compare** tab.
4. Show the comparison with the export, and list the intents that must be deleted by hand, before writing the zip.
5. Tests: build a small export zip, merge a build into it, and check that the unrelated intents and entities are unchanged.

---

## Code-signed Windows executables

**What it would do:** remove the "Windows protected your PC" SmartScreen warning when the executables are first started.

**Considerations**

- Requires a code-signing certificate from a certificate authority (a paid, yearly cost). An EV certificate removes the warning immediately; a standard one builds reputation over time.
- The certificate or signing service credentials must be stored as GitHub Actions secrets, never in the repository.

**Implementation steps**

1. Obtain a certificate, or use a cloud signing service such as Azure Trusted Signing.
2. Add a signing step to `.github/workflows/release.yml` after the PyInstaller builds and before the checksums are written (for example with `signtool` or the signing service's GitHub action).
3. Update the README's Download section to remove the SmartScreen instructions.

---

## Author and validate entity types

**Status:** tabled. Needs a real Dialogflow ES agent export (zip) with at least one custom map entity and one regexp entity, to confirm the exact `entities/` file layout before generating anything (Google's public docs describe the REST API JSON and the CSV import/export format, but not the raw zip's file names or field casing).

**What it would do:** two related pieces, matching this tool's original goal of doing as much as possible outside the slow Dialogflow ES web console:

1. **Author entity types** (map, list and regexp) the same way intents are authored now: a new config file, one row per entity entry (`EntityType, Kind, Value, Synonyms`), generating the `entities/` files alongside the existing `intents/` output. Regexp entries are validated locally (a real regex compile check) before anything is written, catching a broken pattern immediately instead of after importing into Dialogflow.
2. **Validate entity references already used in `intents.cfg`'s Entities column** against what's actually available, so a typo or a forgotten entity is caught before a build, not after importing into Dialogflow:
   - `sys.*` references checked against the known list of Dialogflow ES system entities (see below), warning on anything not recognized.
   - Custom entity references checked against either an existing agent export zip (if the user points the tool at one for comparison) or entities defined via this tool's own new entity config, warning if a referenced custom entity isn't found in either place.

**Known system entities** (from the [System entities reference](https://cloud.google.com/dialogflow/es/docs/reference/system-entities), current as of this writing — re-check before implementing, since Google adds/deprecates these over time):

```text
Date and Time:     date-time, date, date-period, time, time-period
Numbers:           number, cardinal, ordinal, number-integer, number-sequence, flight-number
Amounts w/ Units:  unit-area, unit-currency, unit-length, unit-speed, unit-volume, unit-weight,
                   unit-information, percentage, temperature, duration, age
Unit Names:        currency-name, unit-area-name, unit-length-name, unit-speed-name,
                   unit-volume-name, unit-weight-name, unit-information-name
Geography:         address, zip-code, geo-capital, geo-country, geo-country-code, geo-city,
                   geo-state, place-attraction, airport, location
Contacts:          email, phone-number
Names:             person
Music:             music-artist, music-genre
Other:             color, language
Generic:           any, url
```

(Several more, like `street-address`, `given-name`, `last-name`, `geo-city-us`/`-gb`, are documented as deprecated in favor of the ones above; worth excluding from a fresh implementation rather than encouraging their use.)

**Considerations**

- The exact zip file layout (`entities/<name>.json` + `entities/<name>_entries_<lang>.json`, field names, whether regexp entries need a language-specific entries file at all) needs to be confirmed against a real export before writing any generation code, the same way the existing intent JSON was clearly built by matching a real export rather than guessing from the REST API schema.
- Regexp entities have real limits worth validating locally too: max 50 per agent, max 2000 characters for the compound (all entries `|`-joined) pattern, and they can't be combined with fuzzy matching.
- Custom-entity validation needs a way to point the tool at an existing agent export for comparison — `compare.py` already reads agent export zips for the intents comparison feature, so extending it to also read the `entities/` folder is likely the natural way to do this rather than building a second zip reader.
- This is validation-only for `sys.*` entities (there's nothing to "author", they already exist in Dialogflow); only custom entities would actually get new files generated.

**Implementation steps**

1. Get a real agent export zip with a custom map entity and a regexp entity; inspect its `entities/` folder to confirm the exact file/field format.
2. Add the system-entity list to `constants.py` (e.g. `VALID_SYSTEM_ENTITIES`), and a per-row check in `models.py` (or a new module) that warns when an Entities-column value starts with `sys.` but isn't in that list.
3. Design the new entity config format (columns, one row per entry) and a `models.EntityDefinition`-style model with the same fatal-error/warning split as `ConfigRow`, including the regex compile check for `KIND_REGEXP` rows.
4. Add generation of `entities/*.json` alongside `intents/*.json` in `build_intents.py`, using the confirmed real format from step 1.
5. Extend `compare.py`'s export-loading to also read `entities/`, so custom entity references can be checked against an existing export, and expose this as part of `validate`/`check_rows` (warning, not error, since the entity might simply not exist yet).
6. CLI: a new config file option alongside `--config`; GUI: a new tab or a section of the existing Design doc / config editor flow.
7. Tests: a fixture agent export zip with known entities (map, list, regexp) to validate against; a broken regex to confirm it's caught before writing; a `sys.*` typo to confirm it warns.

---

## Configurable supported language set

**Status:** tabled. Noted during a review of hardcoded values alongside the configurable naming-rules/project-layout/NL-defaults settings, but out of scope for that change since it touches more of the codebase than a simple persisted default.

**What it would do:** let a user change the supported language set (`constants.VALID_LANGUAGES` / `LANGUAGE_NAMES` / `DEFAULT_LANGUAGE`, currently `en`/`es`/`fr`) the same way as `NamingRules`, `ProjectLayout` and `NlDefaults`, so a project that needs a different set (e.g. add `de`, drop `fr`) doesn't have to fork the tool.

**Considerations**

- Bigger than the other configurable settings: `VALID_LANGUAGES` and `LANGUAGE_NAMES` are read directly (not through an optional parameter) in several places — `models.ConfigRow`'s per-row language check, `validate.py`'s per-language folder checks, `extract`'s language option validation, and the GUI's language dropdowns (`gui/app.py`, `gui/config_editor.py`) — so this would need the same optional-parameter threading done for `ProjectLayout`, but across more files.
- `DEFAULT_LANGUAGE` ('en') is also used as the language a synthesized English row is generated in (see `check_rows()`); a configurable language set would need to decide what "the English row" becomes when English isn't necessarily in the set.
- A `LanguageSettings` model would need both the valid codes and their display names (for the GUI dropdowns), e.g. `{"en": "English", "de": "German"}`, not just a list of codes.

**Implementation steps**

1. Add a `LanguageSettings` Pydantic model to `models.py` (a dict of code → display name, plus which one is the default/English-equivalent), defaulting to the current hardcoded `en`/`es`/`fr`.
2. Add `language_settings_path()` / `load_language_settings()` / `save_language_settings()` to `user_settings.py`, mirroring the existing settings.
3. Thread an optional `languages: LanguageSettings | None = None` parameter through `models.ConfigRow.from_csv_row()`, `validate.py`'s per-language checks, and `extract`'s language validation, each defaulting to `None` → the current hardcoded set.
4. Add a `language-settings` CLI command and a matching section on the GUI's Settings tab; update `xl_language` / `compare`'s language dropdowns to read from the saved settings instead of `constants.LANGUAGE_NAMES` directly.
5. Tests: model defaults/overrides, `user_settings` round trip, a CLI test, and a build/validate test using a non-default language set (e.g. only `en`/`de`).
6. Document the change in the user guide and code guide, following the same pattern as the other configurable settings.
