# Intentional (Python)

- [Intentional (Python)](#intentional-python)
  - [Usage](#usage)
    - [Examples](#examples)
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
  
Originally written in Perl, this script has been converted to Python for easier use and maintenance. This script is used to create Dialogflow ES Intents. It can be used in two modes: Standard and Natural Language (NL). The Standard mode is used to create intents based on the `intent.cfg` file. The NL mode is used to create intents based on the training phrases in the NL directory and uses `intents_nl.cfg` file. Standard mode is the default mode when not setting the NL flag.

## Usage

```unix
PS> python -m intentional_py --help

 Usage: python -m intentional_py [OPTIONS] COMMAND [ARGS]...                                                                                                                                 

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version             -v                 Show the application's version and exit                                            │
│ --config              -config      TEXT  Name of the config file when not using the standard files. [default: intents.cfg]  │
│ --quiet               -q                 Use this flag to suppress output.                                                  │
│ --install-completion                     Install completion for the current shell.                                          │
│ --show-completion                        Show completion for the current shell, to copy it or customize the installation.   │
│ --help                                   Show this message and exit.                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ nl | natural-language   Use specific NL config and directories for training phrases.                                        │
│ extract                 Extract data from EXCEL file, saving phrases into correct directory                                 │
│ validate                Optionally validate directories, phrase files, config files before running script                   |    
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


PS> python -m intentional_py nl --help

 Usage: python -m intentional_py nl [OPTIONS]                                                                                                                                                

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


PS> python -m intentional_py extract --help

 Usage: python -m intentional_py extract [OPTIONS]                                                                                                                                                             

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


PS> python -m intentional_py validate --help

Usage: python -m intentional_py validate [OPTIONS]                                                                                                                                                            

 Optionally validate directories, phrase files, config files before running script

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --config          TEXT  Name of the config file when not using the standard files.                                     │
│ --quiet   -q            Use this flag to suppress most output.                                                         │
│ --help                  Show this message and exit.                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

  ```
  
### Examples

- `python -m intentional.py`
- `python -m intentional.py nl -v FIN -c GetIntent -lc`
- `python -m intentional.py nl --reuse`
- `python -m intentional_py extract`
- `python -m intentional_py extract --file 'NL English Data.xlsm'`
- `python -m intentional_py validate --file test.cfg`
- `python -m intentional_py validate`

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
├─README.md
├─intentional.py
├─intents.cfg
├─intents_nl.cfg    
```

The output will be created in the `intents` directory.

## Configuration Files

The default `intent.cfg` (used in STANDARD mode) needs a specific syntax separated by commas. This also follows the standard grammar design documentation.

The default `intents_nl.cfg` (used in NL mode) is generated from the NL training phrases available in the corresponding directories. The format for both is the same as described below.

The config file for either mode can be substituted for the file passed in using the `--config` flag and subsequent filename. The format remains the same.

### Design Document

|Intent| Context| Language| Action| Entities| DTMF| Disable ML|
|-|-|-|-|-|-|-|
|MYAC.NewServicehomeOrBus.Home| MYAC-NewServiceHomeOrBus-Home| en| home| | 1| TRUE|

### intent.cfg

`MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,TRUE`

### Special Notes

1. Both the `context` and DTMF values allow multiple entries separated by pipe (`|`)
2. The `entity` value will allow brackets which are used to as the alias for the returned entity.
    The default parameter name (alias) used by dialogflow is the entity name. Some clients have
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

Using Machine Learning (ML) is enabled by default. In order to disable ML the flag must be passed in as `TRUE`. This is not required to be used for backwards compatibility and only changes the intent when set to TRUE from the config file. Reasons this should be used include when using a regex entity and only a value which matches the entity should trigger the intent.

~~When using slot filling [default is `FALSE`] training phrases are not needed. This will also set the correct events based on context name.~~ **THIS FEATURE IS NOT CURRENTLY USED**!

## Natural Language Mode

When using the NL mode the config file will be generated from the available intents in the corresponding NL directory. The format is the same as described above. As we'll likely be using the standard mode more often the standard mode is the default mode when not setting the NL flag.

There are some special features of the NL intents.

### Special Features

1. If an intent ends in `-NM` the return action will contain `nomatch` rather than the normal action. This indicates an intent that will get matched with phrases but is handled as nomatch by nerve and reprompted. This intent could be for phrases that get handled incorrectly by the dialogflow agent.
2. If an intent ends with a caret (`^`) in the excel file then that will signal the intent to disable machine learning on that intent only. This can help with greedy phrases. This functions the same as setting the flag for non-NL intents.
3. The config file that is built for NL will auto-populate fields based on file name (i.e. using ^) and also based on phrase information for entities.

## Extraction Mode

Use this setting as an alternative to exporting data from an excel file. These are mostly used to organize NL phrases, but could also be used to organize DD phrases. The expected format of the excel file is multiple tabs (intents) with phrases in the first column. Using the `extract` mode of this script will pull the phrases out and save them in the correct directory based on the language provided and the mode (DD or NL).

## Validation Mode

This setting can be used to find possible issues BEFORE running the script. It highlights potential issues in missing directories, phrase files, and common typos in intent and context names. No files is created when using this setting, only information to the screen.

# Installation/Running the script

This script is designed to be run from the command line. It is recommended to use a virtual environment to run the script. The script is written in Python 3.13.1.

Clone this repository as normal and ensure you have python installed locally. Once the repository is cloned, open the directory with VSCode and run these commands to create a virtual environment and install the necessary packages when first ran:

```
uv venv
uv run .\src\intentional_py\intentional.py --help
```

There is an alternative method to run the script on windows using the `intentional.exe` file, still using the command line. This is a standalone executable file and does not require Python to be installed on the machine. This is available in the [repository release](https://github.com/andrewjstuart/intentional-py/releases).

It was built using the following commands:
```
uv build
uv run pyinstaller --onefile src/intentional_py/intentional.py
```

Once the executable is either created or pulled from the repository, it can be run from the command line using the following commands:
```
./intentional.exe
./intentional.exe nl -v FIN -c GetIntent -lc
./intentional.exe nl --reuse
./intentional.exe extract
```