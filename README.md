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
  
Originally written in Perl, this script has been converted to Python for easier use and maintenance. This script is used to create Dialogflow ES Intents. It can be used in two modes: Standard and Natural Language (NL). The Standard mode is used to create intents based on the `intent.cfg` file. The NL mode is used to create intents based on the training phrases in the NL directory and uses `intents_nl.cfg` file. Standard mode is the default mode when not setting the NL flag.

## Usage

```unix
PS: python .\intentional.py -h
usage: intentional [-h] [-nl] [-r] [-v [VERTICAL]] [-c [CONTEXT]] [-lc] [-q] [--version]

This is a script to create Dialogflow ES Intents

options:
  -h, --help            show this help message and exit.
  --config [CONFIG]     Name of the config file when not using the standard files.
  -q, --quiet           Use this flag to suppress output.
  --version             show program's version number and exit.  

Natural Language Mode:
  -nl, --natural-language
                        Use the script in NL mode using specific NL config and directories for training phrases.
  -r, --reuse           Reuse the previously created intents_nl.cfg file.
  -v, --vertical [VERTICAL]
                        Vertical prefix abbreviation used for the NL intent names. **This will rebuild intents_nl.cfg**
  -c, --context [CONTEXT]
                        Context used for the NL intent names (default: GetIntent). **This will rebuild intents_nl.cfg**
  -lc, --lowercase      Certain clients coded the NL actions in lowercase instead of the standard uppercase.This should only be used for these clients that already have been using it.
  ```
  
### Examples

- `python .\intentional.py`
- `python .\intentional.py -nl -v FIN -c GetIntent -lc`
- `python .\intentional.py -nl -reuse`

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

The `intent.cfg` (used in STANDARD mode) needs a specific syntax separated by commas. This also follows the standard grammar design documentation.

The `intents_nl.cfg` (used in NL mode) is generated from the NL training phrases available in the corresponding directories. The format for both is the same as described below.

### Design Document

|Intent| Context| Language| Action| Entities| DTMF| Disable ML| Slot Filling|
|-|-|-|-|-|-|-|-|
|MYAC.NewServicehomeOrBus.Home| MYAC-NewServiceHomeOrBus-Home| en| home| | 1| TRUE| FALSE|

### intent.cfg

`MYAC.NewServicehomeOrBus.Home,MYAC-NewServiceHomeOrBus-Home,en,home,,1,TRUE,FALSE`

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

The language codes tested include `en`, `es`, and `dtmf`. The `dtmf` option will only add training phrases corresponding the DTMF value(s) passed in with the config. This may not be needed.

The standards naming convention for intent names are to include periods (`.`) to separate module abbreviations, prompt names and prompt options. The standard naming convention for context names are to include dashes (`-`) for the same separations.

Using Machine Learning (ML) is enabled by default. In order to disable ML the flag must be passed in as `TRUE`. This is not required to be used for backwards compatibility and only changes the intent when set to TRUE from the config file. Reasons this should be used include when using a regex entity and only a value which matches the entity should trigger the intent.

~~When using slot filling [default is `FALSE`] training phrases are not needed. This will also set the correct events based on context name.~~ **THIS FEATURE IS NOT CURRENTLY USED**!

## Natural Language Mode

When using the NL mode the config file will be generated from the available intents in the corresponding NL directory. The format is the same as described above. As we'll likely be using the standard mode more often the standard mode is the default mode when not setting the NL flag.

There are some special features of the NL intents.

### Special Features

1. If an intent ends in `-NM` the return action will contain `nomatch` rather than the normal action. This indicates an intent that will get matched with phrases but is handled as nomatch by nerve and reprompted. This intent could be for phrases that get handled incorrectly by the dialogflow agent.
2. If an intent ends with a caret (`^`) in the excel file then that will signal the intent to disable machine learning on that intent only. This can help with greedy phrases. This functions the same as setting the flag for non-NL intents.
3. The config file that is built for NL will autopopulate fields based on file name (i.e. using ^) and also based on phrase information for entities.
