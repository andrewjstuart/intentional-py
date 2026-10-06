# User Guide

How to use Intentional from the graphical interface (GUI), the command line (CLI), or the experimental web version. For downloading and a quick start, see the [README](../README.md).

- [Project folder](#project-folder)
- [Config files](#config-files)
  - [Columns](#columns)
  - [Special values](#special-values)
- [Phrase files](#phrase-files)
- [Tasks](#tasks)
  - [Build directed dialog (DD) intents](#build-directed-dialog-dd-intents)
  - [Build natural language (NL) intents](#build-natural-language-nl-intents)
  - [Validate a project](#validate-a-project)
  - [Extract phrases from Excel](#extract-phrases-from-excel)
  - [Create the config from the design document](#create-the-config-from-the-design-document)
  - [Compare with an agent export](#compare-with-an-agent-export)
  - [Merge or package into an agent export](#merge-or-package-into-an-agent-export)
- [Save a job report](#save-a-job-report)
- [The GUI](#the-gui)
- [The CLI](#the-cli)
  - [Commands and options](#commands-and-options)
  - [Examples](#examples)
- [Web (experimental)](#web-experimental)
- [Files and errors](#files-and-errors)

## Project folder

Every task works on a project folder laid out like this:

```text
Intent Creation/
├── intents/                 the JSON files to import into Dialogflow (created by a build)
├── Training Phrases/
│   ├── en/                  DD phrase files, one per action, e.g. pay.txt
│   │   └── NL/              NL phrase files
│   └── es/
│       └── NL/
├── intents.cfg              the DD config
└── intents_nl.cfg           the NL config (created by the NL build)
```

In the GUI, choose this folder as the **Project folder**. On the CLI, either run the command from this folder or pass `--config` with the path of a config file in it: the config file's folder is used for `Training Phrases` and `intents`.

These folder and file names are this project's own convention, not a Dialogflow requirement, and can be changed with the `project-layout` command (or the GUI's **Settings** tab) if a project needs different names; see [Commands and options](#commands-and-options). Once changed, the new names apply to every project, on the CLI and the GUI, until changed again.

## Config files

A config file has one intent per line, with comma-separated values. `intents.cfg` is written by hand, from the design document, or with the GUI's config editor. `intents_nl.cfg` is created by the NL build from the NL phrase files. Both use the same format, and a different file can be used with `--config` (or the config box in the GUI).

### Columns

| Intent | Context | Language | Action | Entities | DTMF | Machine Learning (optional) |
|-|-|-|-|-|-|-|
| MYAC.NewServicehomeOrBus.Home | MYAC-NewServiceHomeOrBus-Home | en | home | | 1 | FALSE |

The same row in the config file:

```text
MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,FALSE
```

- **Intent**: by convention, parts are separated by periods (`.`). A `-` is not allowed in the name.
- **Context**: by convention, parts are separated by dashes (`-`).
- These two naming rules are this project's own convention, not a Dialogflow requirement, and can be changed with the `naming-rules` command (or the GUI's **Settings** tab) if a project needs different standards; see [Commands and options](#commands-and-options).
- **Language**: `en` (English) is the default, `es` (Spanish) the next most common, or `dtmf` to add only the DTMF values as phrases. Dialogflow ES supports many more languages than these two, and this tool validates against whichever ones are configured (see below) — the CLI/GUI can add any of them with `language-settings`. When an intent has several language rows, its default-language row (`en` unless changed) supplies the shared intent definition and every row supplies that language's phrases. If it has no default-language row, one is generated in memory from the first row: its context, action, entities, DTMF and machine-learning value are reused, and phrases are read from the matching `Training Phrases/<default language>/<action>.txt`. The config file itself is not changed. Two rows can also share the same intent **and** language on purpose, to swap in a different set of phrases without duplicating the intent; see [Special values](#special-values).
  - The supported language set (and which one is the default) is this project's own convention, not a Dialogflow requirement, and can be changed with the `language-settings` command (or the GUI's **Settings** tab); see [Commands and options](#commands-and-options). It's just which codes this tool accepts and validates — a language doesn't need a `Training Phrases` folder until a config row actually uses it (see [Validate a project](#validate-a-project)).
- **Action**: the value returned by the intent; the phrases are read from `<action>.txt`.
- **Entities** and **DTMF** can be empty, but their commas are still needed so the columns line up.
- **Machine Learning** is optional, for configs written before the column existed. It maps directly to Dialogflow's JSON `auto` field:

  | Config or design document | Generated JSON | Meaning |
  |-|-|-|
  | `TRUE` | `"auto": true` | Machine learning on |
  | blank or column omitted | `"auto": true` | Machine learning on (default) |
  | `FALSE` | `"auto": false` | Machine learning off |

  Any other value is treated as `TRUE` and shown as a warning. These rows are the same:

  ```text
  MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,TRUE
  MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,
  MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1
  ```

  Reasons to turn machine learning off include a regex entity, where only a value that matches the entity should trigger the intent.

### Special values

1. **Several contexts or DTMF values**: separate them with a pipe (`|`). A DTMF value must be a single digit `0`-`9`, `#` or `*`; anything else is an error.
2. **Entity alias**: Dialogflow uses the entity name as the parameter name by default. Some clients use a different name, set in brackets: `digits4[last_4]` assigns the `digits4` entity to the `last_4` parameter.
3. **Several entities**: separate them with a pipe (`|`). A star (`*`) marks a required entity: `digits4*|digits9-10|sys.phone-number|sys.unit-currency|sys.date`.
4. **Priority**: add it in curly brackets after the intent name, e.g. `GLB.Reuse.No{high}` or `GLB.Reuse.Yes{1}`.

   | Value | Or |
   |-|-|
   | `highest` | `1` |
   | `high` | `2` |
   | `normal` (default) | `3` |
   | `low` | `4` |
   | `ignore` | `5` |

5. **Action ending in a caret (`^`)**: turns machine learning off for that intent, the same as `FALSE` in the last column.
6. **Repeating a row to swap phrases**: two rows can share the same intent and language, with a different Action, so the intent keeps returning one action but reads its phrases from a different file:

   ```text
   MYAC.NewServiceHomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,FALSE
   MYAC.NewServiceHomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home_altphrases,,1,FALSE
   ```

   The **first** row still defines the intent (context, action, priority, entities, machine learning) — here, the intent returns `home` and reads `Training Phrases/en/home.txt`. Every later row for the same intent and language replaces the phrases with its own Action's file instead (`home_altphrases.txt` above), rather than adding to the first row's phrases. A warning is shown whenever this happens, naming the rows involved.

   This only applies when rows differ in some way. A row that is a byte-for-byte copy of an earlier row (every column the same) is an accidental duplicate rather than an intentional phrase swap, and is dropped automatically, with a warning naming the row it duplicates.

7. **Removing an intent (or one of its languages)**: start the row with `-` or `--` instead of building it — the rest of the row is the usual format, just naming what to remove rather than what to create:

   ```text
   MYAC.NewServiceHomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,FALSE
   -MYAC.NewServiceHomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,FALSE
   ```

   - `-` asks for confirmation first (a single dash is easy to mistake for a typo); `--` removes without asking, since it's unambiguous intent. Three or more dashes (`---`, `----`, ...) are treated the same as `--`.
   - A removal row in the **default language** (`en` unless changed, see [language-settings](#commands-and-options)) removes the whole intent: its shared definition file and every language's phrases file. If another row for the same intent in a different language is still being built and isn't itself marked for removal, a warning says so — removing the default-language row takes the rest of the intent with it.
   - A removal row in any **other** language only removes that one language's phrases file; the intent and its other languages are left alone.
   - This affects a regular build, not just comparing with an agent export: a previous build's leftover files for a removed intent are deleted, instead of silently lingering the way they would if the row were simply deleted from the config without a `-`/`--` marker (that case is still only reported as a warning, since nothing says it's safe to delete them).
   - **Validate** reports what's marked for removal without deleting anything, so this can be checked before a real build.

## Phrase files

Each intent's training phrases are in a text file named after its action, one phrase per line: `Training Phrases/<language>/<action>.txt` for DD, and `Training Phrases/<language>/NL/<action>.txt` for NL. The DTMF values from the config are added as extra phrases.

A phrase that contains an entity marks the matching words as `<entity|words>`, like an XML tag:

| Description | Example |
|-|-|
| entire phrase matches the entity | `<sys.phone-number\|4027160012>` |
| partial match | `account number is <digits9\|761384602>` |
| partial match with required entity | `paying <sys.unit-currency*\|$90.46> for this bill` |
| partial match with alias | `my phone number is <sys.phone-number[phone]\|4027160012>` |
| multiple entities | `phone number is <sys.phone-number\|4027160012> and my account number is <digits9\|761384602>` |
| multiple entities | `pay my bill for <sys.unit-currency\|$105> on <sys.date\|october 5th>` |

## Tasks

Each task is a tab in the GUI and a command on the CLI.

| Task | GUI tab | CLI |
|-|-|-|
| Build DD intents | Build DD | `intentional-cli` |
| Build NL intents | Build NL | `intentional-cli nl` |
| Check a project without building | Validate | `intentional-cli validate` |
| Extract phrases from Excel | Extract | `intentional-cli extract` |
| Create the config from the design document | Create Config | `intentional-cli design` |
| Compare with an agent export | Compare | `intentional-cli compare` |
| Merge with an agent export | Merge | `intentional-cli merge` |
| Package for an agent export | Package | `intentional-cli package` |

### Build directed dialog (DD) intents

Reads `intents.cfg` (or the chosen config) and writes the intent JSON files to the `intents` folder, ready to import into Dialogflow.

- The config is checked first. **Errors** (a missing intent, context or action, an intent name containing `-`, or a row without 6 or 7 values) stop the build before any file is written. **Warnings** (such as a missing phrase file, a `.` in a context, or a defaulted language) are listed, and the build continues. The checks are listed under [Validate a project](#validate-a-project).
- Each build is compared with the previous build in the `intents` folder, and the result shows how many intents were added, changed and unchanged.
- Intents that are no longer in the config are listed as a warning, because their files are still in the `intents` folder and would be imported.
- **Clear the intents folder first** (`--clean`) zips everything in the `intents` folder to `intents_<date>_<time>.zip` in the project folder and removes it before building, so only the current intents are left. This also removes intents built from a different config into the same folder.
- **Agent export (optional)** (`--export`): also merges this same build into a copy of that export zip, in the same step - no separate [merge or package](#merge-or-package-into-an-agent-export) run needed. Nothing zip-related happens without it, and the `intents` folder is written exactly the same either way. Choose which Dialogflow action the copy is for with **Package** (**None**, **Merge (restore - complete)**, or **Zip (import - partial)**; the GUI/web wording for `--style`, which still takes `restore`, the default, or `import`).

### Build natural language (NL) intents

Creates `intents_nl.cfg` from the phrase files in `Training Phrases/<language>/NL`, then builds the intents the same way as DD.

- **Vertical** (`-v`): the prefix for the intent names, e.g. `FIN` gives `FIN.PayBill`. Asked for if missing.
- **Context** (`-c`): the context for every NL intent. Defaults to the saved `nl-defaults` context (`GetIntent` unless changed).
- **Lowercase actions** (`-lc`): also writes each action in lowercase, for clients that coded the NL actions that way.
- **Reuse existing config** (`--reuse`): builds from the existing `intents_nl.cfg` instead of creating it again.
- **Agent export (optional)** (`--export`) and **Package** (`--style`): the same as for [Build DD](#build-directed-dialog-dd-intents) - also merges this build into a copy of the export zip, in the same step.

When the config is created:

1. A phrase file ending in `-NM` gives an intent whose action is `nomatch`: it catches phrases the agent would otherwise match wrongly, and the caller is reprompted.
2. A phrase file ending in a caret (`^`) turns machine learning off for that intent, which helps with greedy phrases.
3. The entities are filled in from the entity tags in the phrases.
4. Phrases that appear in more than one file are shown in a scrollable confirmation dialog in the GUI, with **Continue** and **Stop** buttons. The CLI lists them before asking whether to continue. Phrases containing "uh" or "um" are also listed for review.

### Validate a project

Reports problems **before** a build, without writing any files. Validate runs the same config checks as a build, so it reports exactly what a build would, and also checks that the `Training Phrases` folder exists, along with a language's subfolder for each language actually used in the config (a supported language that isn't used yet doesn't need one), and that the config files exist. Phrase files are looked for in both the language folder and its `NL` folder.

The phrase files are checked too, as warnings:

- Entity tags must use the `<entity|words>` form. A tag missing its `<`, `>` or `|` is reported with its line numbers.
- An entity used in a phrase must be listed in the row's Entities column (aliases and the `*` marker are ignored when comparing).
- An empty phrase file is reported, since the intent would have no phrases.
- An intent with no English (`en`) row is reported, including the first row used to generate its English row. The matching English phrase file is checked too.
- In DD configs, two intents that share a phrase are reported only when they also share a language and a context, because the context decides which intent is active at that point in the call. The NL build checks for duplicate phrases itself.

With `--config`, the folder of that config file is checked; without it, the standard config files in the current folder are.

### Extract phrases from Excel

Saves the phrases from an Excel workbook (`.xlsb`, `.xlsm` or `.xlsx`) as phrase files. Each sheet is one intent, with its phrases in the first column; the sheet name becomes the file name. Duplicate phrases in a sheet are removed and the rest are sorted. Choose the mode (DD or NL, default NL) and the language (default `en`; see [Config files](#config-files) for the full supported set and how to add more).

The whole workbook is read before anything is changed, so a file that cannot be read leaves the existing phrases untouched. The phrases being replaced are saved to a zip file first:

- NL replaces the `Training Phrases/<language>/NL` folder and saves it as `Training Phrases/<language>/NL_<date>_<time>.zip`.
- DD replaces only the `.txt` files directly in `Training Phrases/<language>` (the `NL` folder is kept) and saves them as `Training Phrases/<language>_<date>_<time>.zip`.

On the CLI, the phrases are saved under the current folder, so run `extract` from the project folder.

### Create the config from the design document

Creates `intents.cfg` from the Excel design document, so the rows don't have to be copied by hand.

- The workbook needs a sheet with a header row and one intent per row below it. The header row is found automatically near the top of the sheet, by these column names: `Intent`, `Context`, `Language`, `Action`, `Entities`, `DTMF` and `Machine Learning`.
- **Sheet** (`--sheet`) chooses the sheet; without it, the first sheet with Intent, Context, Language and Action headers is used.
- **Machine Learning uses the same values in the design document and config file:** `TRUE` or blank keeps it on; `FALSE` turns it off.
- Blank rows are skipped. An existing config file is copied to `<name>_<date>_<time>.cfg` before it is replaced.
- The new rows are checked with the same rules as a build, and any errors or warnings are listed. In the GUI, **Edit config…** opens the new file to fix them.

### Compare with an agent export

Shows what a build would change in the Dialogflow agent, without writing any files:

1. Export the agent from the Dialogflow ES console (**Settings > Export and Import > Export as ZIP**).
2. Compare it: choose the export on the **Compare** tab, or run `intentional-cli compare --export agent.zip`. Add `--mode NL` for an NL config, and `--config` for a config other than the standard one. The export can also be an unzipped export folder or an `intents` folder.

The result lists:

- the intents the build would **add**,
- the intents that would **change**, and what changed: contexts, action, priority, machine learning, entities, and training phrases added or removed per language,
- the intents **only in the export**. These are not built by this config: they may belong to other modules, or be intents to delete from the agent by hand.

IDs and timestamps are ignored, since they change with every build and export. For NL, the existing `intents_nl.cfg` is used; build the NL config first if the phrase files have changed.

### Merge or package into an agent export

> **Experimental:** the `intents/` folder's exact location inside the zip is detected from the export's own contents rather than hardcoded, since only one real export has been checked so far. Report anything that looks wrong.

Takes the intents already built in the `intents` folder and puts them into a copy of an agent export zip, so the copy can be used straight away instead of adding and removing intents by hand. There are two outcomes, matching Dialogflow ES's own **Restore**/**Import** actions:

- **Merge** (`intentional-cli merge`): a **complete** copy of the export, for Dialogflow's **Restore** action, which replaces the whole agent - anything missing from the zip is deleted from the agent. New and changed intents are added, replacing any existing file with the same name; everything else (other intents, entities, `agent.json`, `package.json`) is carried over unchanged.
- **Package** (`intentional-cli package`): a **partial** copy with just the new or changed intents, for Dialogflow's **Import** action, which only adds new intents and overwrites ones with the same name, and never deletes.

Either way:

1. Build the intents first (DD and NL both write to the same `intents` folder, so there's nothing to build here - just whatever's already there is used). An intent removed with a `-`/`--` [removal row](#special-values) in a past build is already gone from this folder by the time it's built, so there's nothing left for merging/packaging to do about it on its own; it stays in the export unless deleted from it by hand, or [built with the export given](#build-directed-dialog-dd-intents) while the removal row is still in the config.
2. Export the agent, the same as for [Compare with an agent export](#compare-with-an-agent-export). The export's confirmed layout is a top-level `intents/` folder (where the intent and training-phrase JSON live) alongside `agent.json` and `package.json`, plus other folders such as `entities/`.
3. Choose the export zip and run: the **Merge**/**Package** tab, or `intentional-cli merge --export agent.zip` / `intentional-cli package --export agent.zip` (with `--project` if not run from the project folder).

The **export itself is never modified.** A copy is written next to it (downloaded, on the web version), named after it with the style (`restore` for Merge, `import` for Package) and a timestamp added (e.g. `agent_restore_2026-01-15_143022.zip`).

This can also be done **as part of a regular build**, in one step instead of building then merging/packaging separately: add the export on the **Build DD**/**Build NL** tab and choose **Merge** or **Zip** from its **Package** dropdown (**None**, the default, does nothing zip-related), or `--export`/`--style restore|import` on `intentional-cli`/`intentional-cli nl`. A `-`/`--` removal row still in the config also deletes its files from a `restore`-style copy this way (an `import`-style copy can't delete anything either way - those intents are listed in the result to delete from the agent by hand).

Either way, intents only in the export (not in the `intents` folder) are listed, same as Compare, in case any should be deleted from the agent by hand.

## Save a job report

Saving a report is optional. After any completed GUI job, select **Save report…** beside **Open folder**. Choose:

- **Markdown (`.md`)** (default): easy to read, keep with project documentation, or paste into a user story or ticket.
- **CSV (`.csv`)**: useful when the results need to be filtered or opened in a spreadsheet.

The report records when it was created, the task, summary counts, errors and warnings, and the relevant details such as built intent names, validation checks, changed intents and output locations. It does not include the full log.

On the CLI, add `--report <file.md>` or `--report <file.csv>` to any task command. Nothing is saved when this option is omitted. For example:

```text
intentional-cli.exe --config billing.cfg --report billing-build.md
intentional-cli.exe validate --config billing.cfg --report billing-validation.csv
intentional-cli.exe compare --export agent.zip --report billing-changes.md
```

## The GUI

Start the GUI with `intentional.exe`, `uv run intentional`, or `uv run intentional-cli gui` (optionally with `--project <folder>`). The GUI doesn't take command-line options; if `intentional` or `intentional.exe` is started with any, it opens normally and shows a reminder to use `intentional-cli` instead.

- **Project folder**: see [Project folder](#project-folder). The list offers recently used folders, and the last one opens at start-up. The version number is shown next to it.
- **Tabs**: one per [task](#tasks), plus a **Settings** tab for the naming rules, project layout, NL defaults and supported languages (see below); these apply to every project, not just the current one, so they are kept separate from the per-project tasks. Leave a config box blank to use the standard file in the project folder.
- **Settings** tab: the saved naming rules, project layout, NL defaults and supported languages, editable directly (mirrors the `naming-rules`, `project-layout`, `nl-defaults` and `language-settings` CLI commands). Languages are one `code=Name` per line (e.g. `de=German`). **Reset to defaults** only changes the form; **Save settings** is what actually saves all four sections. Reopening the tab reloads the currently saved values, in case they were changed elsewhere (e.g. the CLI) since it was last open.
- **Edit config…** (on the build and Create Config tabs) opens the config file as a table. Rows can be added, edited (double-click), duplicated, deleted and reordered. **Check** runs the same checks as a build and colours the rows with errors or warnings. **Save** writes the file and keeps the previous version as `<name>.bak`.
- **?** (top-right corner): **Help** (also **F1**), which opens at the section for the current tab; **Check for updates**; **Check for updates at start-up**; **Appearance** (**Match system**, **Light**, or **Dark** — remembered for next time); and **About Intentional**. When a newer release is available, a **Version … available** link appears next to the version number. A failed automatic check is silent; a failed manual check shows the network error.

Below the tabs, the results of the last job are shown:

- **Headline**: whether the job succeeded, how long it took and how many warnings it had, with **Save report…** and an **Open folder** button for the folder that was written.
- **Figures**: the main counts, such as intents, phrases and files, or passed and failed checks.
- **Issues**: every error and warning, with the config row it refers to. The tab title shows the counts, and it opens automatically when there is anything to fix.
- **Details**: tables for the job, such as the validation checklist, intents with machine learning off, the NL config summary, changes since the previous build, and where extracted phrases and their backup were saved.
- **Log**: every message from the job as plain text.

The recent project folders, the NL options, the Extract and Compare choices, **Clear the intents folder first** and the last **Package** choice (Build DD/Build NL's optional in-step merge) are remembered between sessions, in `%APPDATA%\Intentional\settings.json` on Windows (`~/.config/intentional/settings.json` elsewhere).

## The CLI

Run the CLI as `intentional-cli.exe` on Windows, or `uv run intentional-cli` from source (or `python -m intentional_py`). The examples below use `uv run intentional-cli`; with the executable, replace that with `intentional-cli.exe`, e.g. `intentional-cli.exe nl -v FIN`. More about `uv run` is in the [uv documentation](https://docs.astral.sh/uv/).

### Commands and options

Every command has `--help`, and `-q` / `--quiet` to show less output. Every task command also accepts optional `--report <file.md|file.csv>`; the extension chooses Markdown or CSV.

| Command | Options |
|-|-|
| *(none)*: build DD intents | `--config <file>` (default from `project-layout`, originally `intents.cfg`), `--clean`, `-e` / `--export <zip>`, `--style restore\|import` (default `restore`) |
| `nl` (or `natural-language`): build NL intents | `-v` / `--vertical <prefix>`, `-c` / `--context <name>` (default from `nl-defaults`, originally `GetIntent`), `-lc` / `--lowercase`, `-r` / `--reuse`, `--config <file>` (default from `project-layout`, originally `intents_nl.cfg`), `--clean`, `-e` / `--export <zip>`, `--style restore\|import` (default `restore`) |
| `extract` (or `x`) | `-f` / `--file <workbook>`, `-m` / `--mode DD\|NL` (default `NL`), `-l` / `--lang <code>` (default `en`; valid codes come from `language-settings`) |
| `validate` | `--config <file>` |
| `compare` | `-e` / `--export <zip or folder>` (required), `-m` / `--mode DD\|NL` (default `DD`), `--config <file>` |
| `merge` | `-e` / `--export <zip>` (required), `-p` / `--project <folder>` (default the current folder) |
| `package` | `-e` / `--export <zip>` (required), `-p` / `--project <folder>` (default the current folder) |
| `design` | `-f` / `--file <workbook>` (required), `-s` / `--sheet <name>`, `--config <file>` (default from `project-layout`, originally `intents.cfg`) |
| `naming-rules` | `--set-intent-forbidden-chars <chars>`, `--set-context-discouraged-chars <chars>`, `--reset`. With no options, shows the current values. Saved to the user's profile (`%APPDATA%\Intentional\naming_rules.json` on Windows, `~/.config/intentional/naming_rules.json` elsewhere), so it applies to every project, on the CLI and the GUI, until changed again. |
| `project-layout` | `--set-training-phrases-dir <name>`, `--set-intents-dir <name>`, `--set-nl-subfolder <name>`, `--set-dd-config <file>`, `--set-nl-config <file>`, `--reset`. With no options, shows the current values. Saved to the user's profile (`%APPDATA%\Intentional\project_layout.json` on Windows, `~/.config/intentional/project_layout.json` elsewhere), so it applies to every project, on the CLI and the GUI, until changed again. |
| `nl-defaults` | `--set-context <name>`, `--reset`. With no options, shows the current value. Saved to the user's profile (`%APPDATA%\Intentional\nl_defaults.json` on Windows, `~/.config/intentional/nl_defaults.json` elsewhere), so it applies to every project, on the CLI and the GUI, until changed again. |
| `language-settings` | `--add <code>` (looks up the name in the full Dialogflow ES catalog) or `--add <code>=<Name>` (repeatable), `--remove <code>` (repeatable), `--set-default <code>`, `--reset`. With no options, shows the current values. Not a Dialogflow requirement to support every language it supports - this is just which ones this tool checks for and accepts in a config file's Language column. Saved to the user's profile (`%APPDATA%\Intentional\language_settings.json` on Windows, `~/.config/intentional/language_settings.json` elsewhere), so it applies to every project, on the CLI and the GUI, until changed again. |
| `gui` | `-p` / `--project <folder>` |

`intentional-cli --version` (or `-v`) shows the version.

### Examples

```text
uv run intentional-cli
uv run intentional-cli --config "C:\Projects\Billing\intents.cfg"
uv run intentional-cli --clean
uv run intentional-cli --export agent.zip
uv run intentional-cli --export agent.zip --style import
uv run intentional-cli nl -v FIN -c GetIntent -lc
uv run intentional-cli nl --reuse
uv run intentional-cli extract
uv run intentional-cli extract --file "NL_English_Data.xlsm"
uv run intentional-cli validate
uv run intentional-cli validate --config test.cfg
uv run intentional-cli validate --config test.cfg --report validation.md
uv run intentional-cli compare --export agent.zip
uv run intentional-cli compare --export agent.zip --mode NL
uv run intentional-cli merge --export agent.zip
uv run intentional-cli package --export agent.zip
uv run intentional-cli package --export agent.zip --project "C:\Projects\Billing"
uv run intentional-cli design --file "Billing design.xlsx"
uv run intentional-cli design --file "Billing design.xlsx" --sheet Intents --config billing.cfg
uv run intentional-cli gui --project "C:\Projects\Billing"
```

## Web (experimental)

A third, experimental way to use Intentional, running entirely in the browser via [Pyodide](https://pyodide.org/) (Python compiled to WebAssembly) — the same core as the CLI/GUI, with nothing uploaded anywhere. Open the hosted copy and nothing needs installing or running: **[andrewjstuart.github.io/intentional-py](https://andrewjstuart.github.io/intentional-py/)**.

To run it yourself from source instead, see [Development](development.md#running-the-web-version) for how it's built; the short version:

```bash
python web/serve.py
```

This builds the project wheel automatically if it's missing or out of date, serves the `web` folder on `localhost`, and opens it in your browser.

- **Open project** from a zip or a folder (pick which with the **Project from** radio buttons - a folder needs a browser that supports picking one, e.g. Chrome/Edge/Firefox/Safari), the same layout as the GUI/CLI: config file(s) and `Training Phrases` at the root. Or **Start empty project** to begin with nothing.
- **Task**: choose a button; the fields and a one-line description below change to match what it needs. Extract and Create Config also need a single Excel file; Compare, Merge and Package need an agent export zip; Build DD/Build NL's **Package** dropdown can also merge/zip the same build into an export in one step (**None**, the default, does nothing zip-related).
- Run as many tasks as you like against the same open project — Extract's phrases are immediately there for Build Intents (NL), Create Config's config is immediately there for Build Intents (DD), with no downloading or re-uploading in between.
- **Download project**, next to the open project's file count, zips the current state at any point — the config, phrases, and any built `intents` folder. This is always a zip, even if the project was opened from a folder.
- Running **Merge**/**Package** - or **Build Intents (DD)**/**Build Intents (NL)** with its **Package** dropdown set - shows a **Download `<name>`** button once it finishes, for the merged copy of the export. The export you uploaded is never modified, and the merged copy isn't added to the project (even when it came from a build), so it has its own download button instead of being part of **Download project**.
- **? Help** (top-right): the same per-task explanations as the GUI's Help window, opening on the section for the currently selected task.
- The page follows the browser's light/dark mode by default; the button next to **? Help** overrides and remembers the choice.

Differences from the GUI/CLI: the web version always uses the standard naming rules, folder names and supported language set (no Settings tab yet), and any confirmation prompt (a Build NL duplicate-phrase warning, or a `-` removal row) is answered "yes" automatically instead of asking — a `--` row is the way to remove something deliberately without relying on that.

## Files and errors

Config and phrase files must be saved as UTF-8. A file in another encoding, a file locked by another program (such as Excel), or an Excel file that can't be read stops the task with a message naming the file.
