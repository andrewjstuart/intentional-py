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
    Save report… optionally saves the completed result as Markdown (for documentation or a user story) or CSV.
    Open folder opens the folder that was written.

A typical NL workflow: Extract the phrases from Excel, then Build NL. For directed dialog: Validate, then Build DD.

Project folder layout:
   Training Phrases\\en\\        DD phrase files (en, es, fr)
   Training Phrases\\en\\NL\\    NL phrase files
   intents.cfg                 DD config
   intents_nl.cfg              NL config (created by Build NL)
   intents\\                    output for Dialogflow

These are this project's own convention, not a Dialogflow requirement, and can be
changed on the Settings tab if a project needs different folder or file names.
""",
    "Build DD": """\
Builds directed dialog intents from a config file.

Config file: leave blank for intents.cfg in the project folder, or choose another file. Its folder is used for the Training Phrases input and the intents output.

Each config row has 7 comma-separated values; the last one is optional:
   Intent, Context, Language, Action, Entities, DTMF, Machine learning
   e.g. MYAC.Billing.Pay,MYAC-Billing-Pay,en,pay,,1,FALSE

• The phrases are read from Training Phrases\\<language>\\<action>.txt.
• Language can be en, es, fr, or dtmf (DTMF values only).
• The English row supplies the shared intent definition. With no English row, one is generated in memory from the first row and uses the matching English phrase file.
• Two rows can share the same intent and language on purpose, with a different Action, to swap in a different phrase file without duplicating the intent: the first such row still defines the intent (context, action, priority, entities, machine learning); later rows only replace the phrases. A row that is a byte-for-byte copy of an earlier row is dropped automatically instead, with a warning.
• Machine learning stays on when the last value is TRUE, blank or left off; FALSE turns it off.
• An action ending in ^ also turns machine learning off for that intent.
• A priority can follow the intent name in braces, e.g. MYAC.Billing.Pay{high}.
• Entities are separated by | ; a trailing * marks a required entity and [name] sets its alias.
• DTMF values must each be a single digit 0-9, # or *; anything else is an error.

Errors (missing intent, context or action; invalid DTMF values; or a forbidden character in an intent name — see the Settings tab) stop the build before any file is written.

Edit config… opens the config file as a table: add, edit, reorder or delete rows, check them with the same rules as a build, and save (the previous file is kept as .bak).

Clear the intents folder first zips everything in the intents folder and removes it before building, so intents that are no longer in the config are not left behind to be imported. Without it, the results list any intents that are no longer built but are still in the folder.

Each build lists what changed since the previous build in the intents folder.
""",
    "Build NL": """\
Builds natural language intents from the phrase files in Training Phrases\\<language>\\NL.

• Vertical prefix: starts every intent name, e.g. RTL gives RTL.Billing.
• Context: the context used by all NL intents; prefilled from the Settings tab's NL defaults (GetIntent unless changed).
• Reuse existing config: build from the current NL config instead of recreating it from the phrase files.
• Lowercase actions: also writes a lowercase action for clients whose NL actions are lowercase.

File names control the intents:
• BILLING.txt becomes the intent RTL.Billing with the action BILLING.
• A name ending in ^ (e.g. PAY_BILL^.txt) turns machine learning off.
• A name ending in -NM (e.g. OTHER-NM.txt) returns the action nomatch.
• Phrases can mark entities as <entity|text>, e.g. pay <sys.unit-currency|$20>.

If the same phrase appears in more than one file, a scrollable dialog lists the duplicates so you can choose Continue or Stop.
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

The phrase files are checked too:
• Entity tags must look like <entity|text>; a missing '<', '>' or '|' is reported with its line numbers.
• An entity used in a phrase must be in the row's Entities column.
• Empty phrase files are reported.
• DD intents that share a phrase are reported only when they also share a language and a context, since the context decides which intent is active.
""",
    "Compare": """\
Shows what a build would change in the Dialogflow agent, without writing any files.

1. Export the agent from the Dialogflow ES console (Settings > Export and Import > Export as ZIP).
2. Choose the export zip, an unzipped export folder, or an intents folder.
3. Choose the mode and config file, then press Compare.

The results list the intents a build would add, the intents that would change (contexts, action, priority, machine learning, entities, and phrases added or removed per language), and the intents only in the export.

Intents only in the export are not built by this config. They may belong to other modules, or be intents that should now be deleted from the agent by hand.

IDs and timestamps are ignored, since they change with every build and export.
""",
    "Design doc": """\
Creates a config file from the Excel design document.

The workbook needs one sheet with a header row and one intent per row below it. The header names are found automatically, anywhere in the first rows:
   Intent, Context, Language, Action, Entities, DTMF, Machine Learning

• Sheet: leave blank to use the first sheet with an Intent, Context, Language and Action header.
• Machine Learning uses the same values as the config: TRUE or blank keeps it on; FALSE turns it off.
• Blank rows are skipped.
• An existing config file is copied to a timestamped backup before it is replaced.
• The new rows are checked with the same rules as a build; press Edit config… to fix any problems.
""",
    "Settings": """\
Project-wide settings, saved to your profile so they apply to every project, on the
CLI and the GUI, until changed again. They are not Dialogflow requirements, just this
project's own conventions, so a project with different standards can change them.

Naming rules:
• Forbidden in an intent name (error): the intent name becomes a file name, so '/' and '\\\\' can never be allowed here, but the default '-' can be changed or cleared.
• Discouraged in a context (warning): defaults to '.'.

Project layout:
• Training phrases folder, Intents output folder, NL phrases subfolder: the folder names used under the project folder.
• Directed dialog config file, Natural language config file: the default file names used when a config box is left blank.

NL defaults:
• Context prefilled for Build NL: the context used for every NL intent (see Build NL); prefills the Context box there, but a build still falls back to this if the box is cleared.

Reset to defaults restores the original values in the form, but Save settings is what actually saves them.
""",
}
