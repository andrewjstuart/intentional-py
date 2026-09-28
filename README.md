# Intentional (Python)

[![Tests](https://github.com/andrewjstuart/intentional-py/actions/workflows/tests.yml/badge.svg)](https://github.com/andrewjstuart/intentional-py/actions/workflows/tests.yml)

- [Intentional (Python)](#intentional-python)
  - [Download](#download)
  - [Usage](#usage)
    - [Examples](#examples)
  - [Graphical Interface (GUI)](#graphical-interface-gui)
  - [Directory Structure](#directory-structure)
  - [Configuration Files](#configuration-files)
    - [Design Document](#design-document)
    - [intent.cfg](#intentcfg)
    - [Special Notes](#special-notes)
  - [Phrases](#phrases)
  - [Natural Language Mode](#natural-language-mode)
    - [Special Features](#special-features)
  - [Extraction Mode](#extraction-mode)
  - [Validation Mode](#validation-mode)
  - [Installation/Running the script](#installationrunning-the-script)
  - [Packaging the Windows executables](#packaging-the-windows-executables)
  - [Releases and automated builds](#releases-and-automated-builds)
  - [Testing](#testing)
  
Originally written in Perl, this script has been converted to Python for easier use and maintenance. This script is used to create Dialogflow ES Intents. It can be used in two modes: Standard and Natural Language (NL). The Standard mode is used to create intents based on the `intent.cfg` file. The NL mode is used to create intents based on the training phrases in the NL directory and uses `intents_nl.cfg` file. Standard mode is the default mode when not setting the NL flag.

Everything is available from the command line (CLI) on Windows or Linux, and from a [graphical interface (GUI)](#graphical-interface-gui). Both can be run from source with uv, or as standalone Windows executables that do not need Python installed: `intentional.exe` (GUI) and `intentional-cli.exe` (CLI).

## Download

The Windows executables are attached to each [release](https://github.com/andrewjstuart/intentional-py/releases). Under **Assets** of the latest release, download:

- `intentional.exe` for the GUI (double-click to start), and/or
- `intentional-cli.exe` for the CLI (run it from a terminal, e.g. `intentional-cli.exe nl -v FIN`).

No installation or Python is needed. `SHA256SUMS.txt` lists each file's checksum; `Get-FileHash .\intentional.exe` in PowerShell shows the checksum of a downloaded file for comparison.

The executables are not code-signed, so the first time one is started Windows SmartScreen may show "Windows protected your PC". Select **More info**, then **Run anyway**.

Each release also includes the matching source code (`Source code (zip)`), which can be run or built with the steps in [Installation/Running the script](#installationrunning-the-script).

## Usage

The CLI is installed as the `intentional-cli` command and can also be run with `python -m intentional_py`. Besides the default Standard mode, the script has four commands: `nl`, `extract`, `validate`, and `gui`. The `nl` command is used to create intents using the NL mode. The `extract` command is used to extract data from an excel file and save the phrases into the correct directory. The `validate` command is used to validate directories, phrase files, and config files before running the script. The `gui` command opens the graphical interface.

More information on using `uv run` and the `uv` tool can be found [here](https://docs.astral.sh/uv/).

```unix
PS> uv run intentional-cli --help

 Usage: intentional-cli [OPTIONS] COMMAND [ARGS]...                                                                                                                                 

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version             -v                 Show the application's version and exit                                            │
│ --config              -config      PATH  Name of the config file when not using the standard files. [default: intents.cfg]  │
│ --quiet               -q                 Use this flag to suppress most output.                                             │
│ --install-completion                     Install completion for the current shell.                                          │
│ --show-completion                        Show completion for the current shell, to copy it or customize the installation.   │
│ --help                                   Show this message and exit.                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ nl | natural-language   Use specific NL config and directories for training phrases.                                        │
│ x | extract             Extract data from EXCEL file, saving phrases into correct directory                                 │
│ validate                Optionally validate directories, phrase files, config files before running script                   │
│ gui                     Open the graphical interface.                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


PS> uv run intentional-cli nl --help

 Usage: intentional-cli nl [OPTIONS]                                                                                                                                                

 Use specific NL config and directories for training phrases.

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --config          TEXT  Name of the config file when not using the standard files. [default: intents_nl.cfg]        │
│ --quiet   -q            Use this flag to suppress output.                                                           │
│ --help                  Show this message and exit.                                                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Natural Language Options ──────────────────────────────────────────────────────────────────────────────────────────╮
│ --reuse      -r             Reuse the previously created NL config file.                                            │
│ --vertical   -v       TEXT  Vertical prefix abbreviation used for the NL intent names. Rebuilds the NL config file  │
│ --context    -c       TEXT  Context used for the NL intent names. Rebuilds the NL config file [default: GetIntent]  │
│ --lowercase  -lc            Certain clients coded the NL actions in lowercase instead of the standard uppercase.    │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


PS> uv run intentional-cli extract --help

 Usage: intentional-cli extract [OPTIONS]                                                                                                                                                             

 Extract data from EXCEL file, saving phrases into correct directory

╭─ Options─────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --quiet  -q        Use this flag to suppress most output.                                                            │
│ --help             Show this message and exit.                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Extract File Options ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ --file             -f      TEXT  Name of the EXCEL file used to extract data                                         │
│ --mode             -m      TEXT  Mode to save data: 'DD' or 'NL' [default: NL]                                       │
│ --language,--lang  -l      TEXT  Language abbreviation to use: 'en', 'es', 'fr' [default: en]                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


PS> uv run intentional-cli validate --help

Usage: intentional-cli validate [OPTIONS]                                                                                                                                                            

 Optionally validate directories, phrase files, config files before running script

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --config          TEXT  Name of the config file when not using the standard files.                                   │
│ --quiet   -q            Use this flag to suppress most output.                                                       │
│ --help                  Show this message and exit.                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

  ```
  
### Examples

- `uv run intentional-cli`
- `uv run intentional-cli --config "C:\Projects\Billing\intents.cfg"`
- `uv run intentional-cli nl -v FIN -c GetIntent -lc`
- `uv run intentional-cli nl --reuse`
- `uv run intentional-cli extract`
- `uv run intentional-cli extract --file 'NL_English_Data.xlsm'`
- `uv run intentional-cli validate --config test.cfg`
- `uv run intentional-cli validate`
- `uv run intentional-cli gui`
- `uv run intentional-cli gui --project "C:\Projects\Billing"`

The same commands work with the Windows executable by replacing `uv run intentional-cli` with `intentional-cli.exe`, for example `intentional-cli.exe nl -v FIN`.

When `--config` is passed to the Standard or `nl` mode, the config file's folder is used for the `Training Phrases` input and the `intents` output. Without it, the default config file in the current directory is used. `validate --config` checks the folder of the config file passed in, or the standard config files in the current directory when no valid file is given.

Configuration problems found before a build (missing intent, context or action, an intent name containing `-`, or a row without 6 or 7 values) stop the build before any file is written, so they can be fixed first.

## Graphical Interface (GUI)

The GUI provides the same features as the CLI. Start it with any of these:

- `uv run intentional`
- `uv run intentional-cli gui` (optionally with `--project <folder>` to open a project folder)
- the standalone `intentional.exe` on Windows (see [Packaging the Windows executables](#packaging-the-windows-executables))

The GUI does not take command-line options. If `intentional` or `intentional.exe` is started with any, it opens normally and shows a reminder to use `intentional-cli` instead.

The window contains:

- **Project folder**: the folder containing `Training Phrases`, the config files and the `intents` output. It defaults to the current directory. The version number is shown next to it.
- **Build DD**: builds intents from a config file (blank uses `intents.cfg` in the project folder).
- **Build NL**: builds the NL config and intents using the vertical prefix, context, and the "Reuse existing config" and "Lowercase actions" options.
- **Extract**: extracts phrases from an Excel file into the project's `Training Phrases` folder for the selected mode and language.
- **Validate**: validates a config file, or the standard config files when left blank.

The **?** button in the top-right corner opens **Help** (also **F1**), which explains each mode, the project folder layout and the config format, and **About Intentional**, which shows the version. Help opens at the section for the current tab.

Below the tabs, the results of the last job are shown:

- **Headline**: whether the job succeeded, how long it took and how many warnings it had, with an **Open folder** button for the intents or phrase folder that was written.
- **Figures**: the main counts, such as intents, phrases and files, or passed and failed checks for Validate.
- **Issues**: every error and warning in a table, with the config row it refers to. The tab title shows the counts, and it opens automatically when there is anything to fix.
- **Details**: tables for the job, such as the validation checklist, intents with machine learning disabled, the NL config summary, duplicate phrases, and where extracted phrases and their backup were saved.
- **Log**: every message from the job as plain text.

If duplicate phrases are found while building the NL config, they are listed under Details and a dialog asks whether to continue.

## Directory Structure

The script will look for the following directory structure:

```unix
Intent Creation/
├───intents/
└───Training Phrases/
│   ├───en/
|   │   └───NL
│   ├───es/
|   │   └───NL
├───intents.cfg
├───intents_nl.cfg    
```

The output will be created in the `intents` directory.

## Configuration Files

The default `intent.cfg` (used in STANDARD mode) needs a specific syntax separated by commas. This also follows the standard grammar design documentation.

The default `intents_nl.cfg` (used in NL mode) is generated from the NL training phrases available in the corresponding directories. The format for both is the same as described below.

The config file for either mode can be substituted for the file passed in using the `--config` flag and subsequent filename. The format remains the same.

### Design Document

|Intent| Context| Language| Action| Entities| DTMF| Machine Learning (optional)|
|-|-|-|-|-|-|-|
|MYAC.NewServicehomeOrBus.Home| MYAC-NewServiceHomeOrBus-Home| en| home| | 1| FALSE|

### intent.cfg

`MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,FALSE`

The last column is optional and can be left blank or left off entirely, so these rows are the same and keep machine learning enabled:

```unix
MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,TRUE
MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,
MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1
```

The Entities and DTMF values can be empty, but their commas are still needed so the columns line up.

### Special Notes

1. Both the `context` and DTMF values allow multiple entries separated by pipe (`|`)
2. The `entity` value will allow brackets which are used to as the alias for the returned entity.
    The default parameter name (alias) used by Dialogflow is the entity name. Some clients have
    changed this value however and need special handling when using the script.
    - Example from config:
        - `,digits4[last_4],`
        will assign the `digits4` entity to phrases using the `last_4` as a parameter name
3. The `entity` value also accepts pipe (`|`) as a separator for multiple entity intents. This
    will become more important as we create more multi-entity intents. Additionally the
    star (`*`) will be used to indicate which, if any, are the required entities.
    - Example from config:
        - `,digits4*|digits9-10|sys.phone-number|sys.unit-currency|sys.date,`
4. Phrases which use entities need to specify which part of the phrase and which entity should be matched to that specific section. These use the format `<ENTITY|PHRASE>` with greater than and less than signs similar to XML tags.
    - These are used in both directed dialog and natural language phrases.
    - Example from phrase file:
        - `this is an example of a <entitiyname|phrase> with an entity`

    | Description | Example in Training Phrase|
    |-------------|---------------------------|
    | entire phrase matches the entity | `<sys.phone-number\|4027160012>` |
    | partial match | `account number is <digits9\|761384602>` |
    | partial match with required entity | `paying <sys.unit-currency*\|$90.46> for this bill` |
    | partial match with alias | `my phone number is <sys.phone-number[phone]\|4027160012>` |
    | multiple entities | `phone number is <sys.phone-number\|4027160012> and my account number is <digits9\|761384602>` |
    | multiple entities | `pay my bill for <sys.unit-currency\|$105> on <sys.date\|october 5th>` |

5. Intents can also set the intent priority passing in the values within curly brackets after the intent name.
    - Example from config:
        - `GLB.Reuse.No{high}`
        - `GLB.Reuse.Yes{1}`
    - Acceptable values are listed below and are converted to a numeric value when creating the intent
        - "highest" or "1"
        - "high" or "2"
        - "normal" or "3" (default)
        - "low" or "4"
        - "ignore" or "5"

## Phrases

The corresponding training phrases need to be present in a text file named the same as the return action.

The DTMF value is also added to the training phrases but separate of the phrase file. If using entities then the training phrases need to callout the phrases which match the entity.

The language codes tested include `en`, `es`, and `dtmf`. The `dtmf` option will only add training phrases corresponding the DTMF value(s) passed in with the config.

The standards naming convention for intent names are to include periods (`.`) to separate module abbreviations, prompt names and prompt options. The standard naming convention for context names are to include dashes (`-`) for the same separations.

Machine Learning (ML) is enabled by default. The Machine Learning column is optional, for backwards compatibility with configs written before it existed: when it is blank or left off, ML stays enabled (`TRUE`). Set it to `FALSE` to disable ML for that intent; ending the action with a caret (`^`) does the same. Reasons to disable ML include using a regex entity where only a value which matches the entity should trigger the intent. Any other value is treated as `TRUE` and shown as a warning.

~~When using slot filling [default is `FALSE`] training phrases are not needed. This will also set the correct events based on context name.~~ **THIS FEATURE IS NOT CURRENTLY USED**!

## Natural Language Mode

When using the NL mode the config file will be generated from the available intents in the corresponding NL directory. The format is the same as described above. As we'll likely be using the standard mode more often the standard mode is the default mode when not setting the NL flag.

There are some special features of the NL intents.

### Special Features

1. If an intent ends in `-NM` the return action will contain `nomatch` rather than the normal action. This indicates an intent that will get matched with phrases but is handled as nomatch by nerve and reprompted. This intent could be for phrases that get handled incorrectly by the Dialogflow agent.
2. If an intent ends with a caret (`^`) in the excel file then that will signal the intent to disable machine learning on that intent only. This can help with greedy phrases. This functions the same as setting the flag for non-NL intents.
3. The config file that is built for NL will auto-populate fields based on file name (i.e. using ^) and also based on phrase information for entities.

## Extraction Mode

Use this setting as an alternative to exporting data from an excel file. These are mostly used to organize NL phrases, but could also be used to organize DD phrases. The expected format of the excel file is multiple tabs (intents) with phrases in the first column. Using the `extract` mode of this script will pull the phrases out and save them in the correct directory based on the language provided and the mode (DD or NL).

The whole Excel file is read before anything is changed, so a file that cannot be read leaves the existing phrases untouched. The phrases being replaced are then saved to a timestamped zip file:

- NL mode replaces the `Training Phrases/<language>/NL` folder and saves it as `Training Phrases/<language>/NL_<date>_<time>.zip`.
- DD mode replaces only the `.txt` files directly in `Training Phrases/<language>` (the `NL` folder is kept) and saves them as `Training Phrases/<language>_<date>_<time>.zip`.

## Validation Mode

This setting can be used to find possible issues BEFORE running the script. It highlights potential issues in missing directories, phrase files, and common typos in intent and context names. No files are created when using this setting, only information to the screen (or the GUI log).

The Standard and NL builds run the same config checks automatically before creating any JSON, so `validate` reports exactly what a build would. Errors (such as a missing intent, context or action, or an intent name containing `-`) fail the check and would stop a build. Warnings (such as a missing phrase file, a `.` in a context, or a defaulted language) are listed but a build would continue. Phrase files are looked for in both the language folder and its `NL` folder.

## Installation/Running the script

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and the dependencies. Python 3.11 or newer is required. Clone the repository, open the directory with VSCode, and run these commands from the project folder:

| Task | Command |
|-|-|
| Create or update the environment (CLI, GUI and dev tools) | `uv sync --extra dev --extra gui` |
| CLI only | `uv sync` |
| Run the CLI | `uv run intentional-cli --help` |
| Run the GUI | `uv run intentional` or `uv run intentional-cli gui` |
| Run the tests | `uv run pytest` |
| Lint | `uv run ruff check src` |
| Update the lock file after editing `pyproject.toml` | `uv lock` |
| Upgrade the dependencies | `uv lock --upgrade`, then `uv sync --extra dev --extra gui` |
| List dependencies with newer releases than `pyproject.toml` allows | `uv tree --outdated --depth 1` |

`uv lock --upgrade` moves every dependency, including the `gui` and `dev` extras, to the newest release allowed by the ranges in `pyproject.toml`. To go past a range (for example a new major version), raise it in `pyproject.toml` after checking the release notes, then run `uv lock`.

Text files (config and phrase files) must be saved as UTF-8. A file in another encoding, a file locked by another program (such as Excel), or an Excel file that cannot be read stops the run with a message naming the file.

The GUI packages are optional (`gui` extra), so the CLI can be installed without them. If `intentional-cli gui` is run without them, it explains how to install them.

If uv reports `invalid peer certificate: UnknownIssuer` (common behind a corporate proxy), add `--system-certs` to the uv command to use the operating system's certificates.

## Packaging the Windows executables

The GUI and the CLI can each be built as a standalone Windows executable that does not require Python to be installed. Releases are normally built automatically by GitHub Actions (see [Releases and automated builds](#releases-and-automated-builds)); these steps build them by hand:

| Executable | Spec file | Use |
|-|-|-|
| `intentional.exe` | `intentional-gui.spec` | The GUI. Opens without a console window. |
| `intentional-cli.exe` | `intentional-cli.spec` | The CLI. Run it from a terminal with the same options as `intentional-cli`. |

On Windows, from the project folder:

```bash
uv sync --extra dev --extra gui
uv run pyinstaller --noconfirm intentional-gui.spec
uv run pyinstaller --noconfirm intentional-cli.spec
```

The executables are created in the `dist` folder. The version is shown in the GUI's title bar and next to the project folder, by `intentional-cli.exe --version`, and in each executable's file properties (Explorer > Properties > Details). The file properties are generated from the version in `pyproject.toml` by `version_info.py`. Both spec files only build on Windows; on Linux the CLI is run with `uv run intentional-cli`.

`intentional-cli.exe` is meant to be run from a terminal (for example `intentional-cli.exe nl -v FIN`). Double-clicking it runs the default Standard mode using `intents.cfg` in the executable's folder, then the console closes immediately. The GUI is not included in `intentional-cli.exe`, so `intentional-cli.exe gui` points to `intentional.exe` instead.

## Releases and automated builds

[GitHub Actions](https://docs.github.com/actions) runs two workflows from the `.github/workflows` folder on GitHub's own machines, so no local Windows machine is needed to build a release. Their runs, logs and results are listed on the repository's **Actions** tab.

| Workflow | File | Runs when | What it does |
|-|-|-|-|
| Tests | `tests.yml` | A push to `main`, any pull request, or **Run workflow** | Runs the tests on Windows and Linux. A failure is shown on the pull request and on the badge at the top of this README. |
| Release | `release.yml` | A tag starting with `v` is pushed, or **Run workflow** | On Windows: runs the tests, builds both executables and `SHA256SUMS.txt`, and for a tag publishes them as a GitHub Release. |

Both workflows install with `uv sync --locked`, so they fail if `uv.lock` does not match `pyproject.toml`. Run `uv lock` and commit `uv.lock` to fix that.

### Publishing a release

1. Update the version in **both** `pyproject.toml` and `src/intentional_py/__init__.py` (a test fails if they differ), for example to `1.0.6`.
2. Run `uv lock`, since `uv.lock` records the project's version, then `uv run pytest`.
3. Commit the changes and merge them into `main`.
4. Create and push a tag named `v` followed by the version, from the commit to release:

   ```bash
   git checkout main
   git pull
   git tag v1.0.6
   git push origin v1.0.6
   ```

5. Open the **Actions** tab and follow the **Release** run. When it finishes, the release appears under **Releases** with `intentional.exe`, `intentional-cli.exe` and `SHA256SUMS.txt`, and release notes generated from the merged pull requests and commits since the previous release. Edit the release on GitHub to add or change the notes.

The release is built from exactly the tagged commit, and the build fails without publishing anything if the tag does not match the version in `pyproject.toml` or if any test fails. To retry after a fix, delete the tag (`git tag -d v1.0.6` and `git push origin :refs/tags/v1.0.6`) and, if a release was already published for it, delete that release on the **Releases** page; then tag the fixed commit again. A release can also be drafted on GitHub first: pushing its tag adds the executables to the existing release instead of creating a new one.

### Test builds without a release

On the **Actions** tab, select **Release**, then **Run workflow**, choose a branch and select **Run workflow** again. When the run finishes, download the executables from the **Artifacts** section at the bottom of the run's page (`intentional-windows`, a zip file). Nothing is published, and GitHub deletes artifacts after 90 days by default.

## Testing

Test files are included within this repository in the `src/intentional_py/tests` directory. They cover the CLI commands, the preflight config checks, the core functions used by both front ends, and the GUI actions (no display is needed for these). Install the dev tools with `uv sync --extra dev --extra gui`, then run the tests using `uv run pytest`. The GUI command test is skipped if the `gui` extra is not installed. The same tests run on GitHub for every push to `main` and every pull request (see [Releases and automated builds](#releases-and-automated-builds)).

```bash
[~intentional-py]> uv run pytest -q
.........................................                                [100%]
41 passed in 10.72s
```
