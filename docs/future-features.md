# Future Features

Ideas that have been discussed but not built yet, with the steps to build each one. Add new ideas at the end, and move an idea to the [user guide](user-guide.md) once it is implemented.

- [Upload intents directly to Dialogflow](#upload-intents-directly-to-dialogflow)
- [Import zip merged into an agent export](#import-zip-merged-into-an-agent-export)
- [Code-signed Windows executables](#code-signed-windows-executables)
- [Author and validate entity types](#author-and-validate-entity-types)

---

## Upload intents directly to Dialogflow

**Status:** tabled. It needs Google Cloud credentials, sign-in and audit logging, which should be designed carefully.

**What it would do:** push the built intents straight into a Dialogflow ES agent, instead of exporting, importing and cleaning up by hand. It could also delete intents that are no longer in the config, after confirmation.

**Considerations**

- Access is through the Dialogflow ES API (`google-cloud-dialogflow`), which needs a Google Cloud project, the agent's project ID, and a signed-in user or service account with the **Dialogflow API Admin** (or Client) role.
- Credentials must never be stored in the repository or in `settings.json`. Prefer Google's own sign-in (`gcloud auth application-default login`) so the tool never handles a key file. If service-account keys are used, keep them outside the project folder.
- Changes made through the API are immediate, so a dry run (the existing `compare` feature) should always be shown and confirmed first.
- Every upload should be logged: who, when, which agent, and which intents were created, updated or deleted.
- Deleting intents is the riskiest part and should be a separate, explicit confirmation. The `batch_update_intents`/`batch_delete_intents` split below is the API equivalent of the `import`/`restore` package styles in [Import zip merged into an agent export](#import-zip-merged-into-an-agent-export) - an upload command could reuse that same `-`/`--` removal-row marking to decide what to delete, instead of a separate `--delete-missing` flag.

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

**Status:** implemented for the CLI (`intentional-cli package --style restore|import`, see the [user guide](user-guide.md#package-an-updated-agent-export)) and covered by [test_package_export.py](../src/intentional_py/tests/test_package_export.py), but only against a synthetic zip - it still needs checking against a real Dialogflow ES export, and a GUI/web front end.

**What it does:** takes the current agent export, adds or replaces the intents from a build, and produces a new zip matching one of Dialogflow's own actions:

- `restore`: a **complete** zip, for the **Restore** action, which replaces the whole agent - anything missing is deleted. A `-`/`--` removal row deletes its files from the copy too.
- `import`: a **partial** zip of just the new/changed intents, for the **Import** action, which only adds or overwrites and never deletes. `agent.json`/`package.json` aren't included, since this tool never writes them and Import leaves them alone anyway. A removal row has no effect on the zip in this style (there's nothing Import can do with it); those intents are listed in the result to delete from the agent by hand instead.

**Considerations**

- The export's layout is now confirmed: a top-level `intents/` folder (where the intent and usersays JSON live), `agent.json` and `package.json` at the root, and other folders for entities etc. `compare._intents_prefix()` still detects the `intents/` location from the zip's own contents rather than hardcoding it, as a safety net in case some exports differ (e.g. nest it under an agent-name folder) - this hasn't come up yet.
- Which Dialogflow action keeps the rest of the agent unchanged, and which can delete, is also confirmed: **Restore** replaces everything (so a `restore`-style zip has to be complete), **Import** only adds/overwrites and never deletes (so a `-`/`--` removal row needs a `restore`-style zip to actually take effect - `package_export()` surfaces this as `needs_manual_removal` when `import` is chosen instead).
- Intents that are no longer used still have to be deleted from the agent by hand unless marked with a `-`/`--` [removal row](user-guide.md#special-values) **and** packaged with `--style restore`. The result lists everything else only in the export as "only in the export" either way.
- Entities (`entities/`) and agent settings in the export are kept unchanged by `restore` style - carried over as-is rather than parsed, since this tool doesn't build them - and left out of an `import`-style zip entirely, since Import would leave them alone anyway.

**Remaining steps**

1. Test both actions with a copy of a real agent's export to confirm `package_export()`'s assumptions (particularly that `import` really does leave unmentioned intents/entities alone) - adjust `compare.py`'s zip handling if anything differs.
2. Add a GUI **Package** button (likely a second action on the **Compare** tab, since it needs the same export file and shows the same comparison first, with a choice of style) and a web action, mirroring how `compare` is wired into `gui/actions.py` and `web/actions.py`.
3. Once confirmed against a real export, remove the "experimental" caveat from the user guide.

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
