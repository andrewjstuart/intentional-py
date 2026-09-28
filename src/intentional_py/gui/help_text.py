"""Help text shown by the GUI's Help window, one section per tab."""

SECTIONS: dict[str, str] = {
    "Getting started": """\
Intentional creates Dialogflow ES intent files from a config file and training phrase text files.

1. Choose the Project folder at the top of the window. It holds the Training Phrases folder, the config files, and receives the intents folder.
2. Pick a tab for the task, fill in the options, and press its button.
3. The results appear below the tabs:
   • Figures: the main counts for the job.
   • Issues: every error and warning, with the config row it refers to. Errors stop a build; warnings do not.
   • Details: tables such as the validation checklist or where files were saved.
   • Log: every message from the job.
   Open folder opens the folder that was written.

A typical NL workflow: Extract the phrases from Excel, then Build NL. For directed dialog: Validate, then Build DD.

Project folder layout:
   Training Phrases\\en\\        DD phrase files (en, es, fr)
   Training Phrases\\en\\NL\\    NL phrase files
   intents.cfg                 DD config
   intents_nl.cfg              NL config (created by Build NL)
   intents\\                    output for Dialogflow
""",
    "Build DD": """\
Builds directed dialog intents from a config file.

Config file: leave blank for intents.cfg in the project folder, or choose another file. Its folder is used for the Training Phrases input and the intents output.

Each config row has 7 comma-separated values:
   Intent, Context, Language, Action, Entities, DTMF, Machine learning
   e.g. MYAC.Billing.Pay,MYAC-Billing-Pay,en,pay,,1,TRUE

• The phrases are read from Training Phrases\\<language>\\<action>.txt.
• Language can be en, es, fr, or dtmf (DTMF values only).
• An action ending in ^ disables machine learning for that intent.
• A priority can follow the intent name in braces, e.g. MYAC.Billing.Pay{high}.
• Entities are separated by | ; a trailing * marks a required entity and [name] sets its alias.

Errors (missing intent, context or action, or '-' in an intent name) stop the build before any file is written.
""",
    "Build NL": """\
Builds natural language intents from the phrase files in Training Phrases\\<language>\\NL.

• Vertical prefix: starts every intent name, e.g. RTL gives RTL.Billing.
• Context: the context used by all NL intents (default GetIntent).
• Reuse existing config: build from the current NL config instead of recreating it from the phrase files.
• Lowercase actions: also writes a lowercase action for clients whose NL actions are lowercase.

File names control the intents:
• BILLING.txt becomes the intent RTL.Billing with the action BILLING.
• A name ending in ^ (e.g. PAY_BILL^.txt) disables machine learning.
• A name ending in -NM (e.g. OTHER-NM.txt) returns the action nomatch.
• Phrases can mark entities as <entity|text>, e.g. pay <sys.unit-currency|$20>.

If the same phrase appears in more than one file, the phrases are listed under Details and you are asked whether to continue.
""",
    "Extract": """\
Saves the phrases from an Excel workbook (.xlsb, .xlsm or .xlsx) as text files.

• Each sheet becomes one text file named after the sheet, with the phrases in the first column.
• NL mode writes to Training Phrases\\<language>\\NL; DD mode writes to Training Phrases\\<language>.
• The phrases being replaced are saved to a timestamped zip file first. DD mode keeps the NL folder.
• The whole workbook is read before anything changes, so a file that cannot be read changes nothing.
• A sheet with no phrases creates an empty file and a warning.
""",
    "Validate": """\
Checks a project before building, without creating any files.

• Config file: choose one, or leave blank to check intents.cfg and intents_nl.cfg in the project folder.
• Checks that the Training Phrases folders exist for each language.
• Runs the same config checks as a build: errors would stop a build, warnings are listed but a build would continue.
• Phrase files are looked for in both the language folder and its NL folder.
""",
}
