# Intentional (Python)

[![Tests](https://github.com/andrewjstuart/intentional-py/actions/workflows/tests.yml/badge.svg)](https://github.com/andrewjstuart/intentional-py/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


Intentional creates Dialogflow ES intents from a config file and training phrase files, ready to import into an agent. It was first written in Perl and converted to Python for easier use and maintenance.

It has a graphical interface (GUI) and a command line (CLI), with the same features. Both run on Windows or Linux from source, or as standalone Windows executables that don't need Python: `intentional.exe` (GUI) and `intentional-cli.exe` (CLI). An experimental browser-based prototype is also in progress (see [Web prototype](#web-prototype-experimental)).

## Documentation

| Guide | For |
|-|-|
| [User guide](docs/user-guide.md) | Using Intentional: the project folder, config and phrase files, every task, the GUI, and all CLI commands and options. |
| [Code guide](docs/code-guide.md) | Learning how the code works: what each Python file does, how they fit together, and where to start reading. |
| [Development](docs/development.md) | Running from source, testing, building the executables, and publishing a release. |
| [Release history](https://github.com/andrewjstuart/intentional-py/releases) | Changes and downloadable files for each published version. |
| [Future features](docs/future-features.md) | Ideas discussed but not built yet, with the steps to build each one. |

The GUI also has built-in help: select **?** > **Help**, or press **F1**.

## What it does

| Task | Description |
|-|-|
| [Build DD intents](docs/user-guide.md#build-directed-dialog-dd-intents) | Creates directed dialog intents from `intents.cfg` and the phrase files. |
| [Build NL intents](docs/user-guide.md#build-natural-language-nl-intents) | Creates the NL config from the NL phrase files, then the intents. |
| [Extract](docs/user-guide.md#extract-phrases-from-excel) | Saves the phrases from an Excel workbook as phrase files. |
| [Validate](docs/user-guide.md#validate-a-project) | Checks the config and phrase files without building anything. |
| [Compare](docs/user-guide.md#compare-with-an-agent-export) | Shows what a build would change compared with an agent export. |
| [Design doc](docs/user-guide.md#create-the-config-from-the-design-document) | Creates `intents.cfg` from the Excel design document. |

Every completed job can optionally be saved as a [Markdown or CSV report](docs/user-guide.md#save-a-job-report).

## Download

The Windows executables are attached to each [release](https://github.com/andrewjstuart/intentional-py/releases). Under **Assets** of the latest release, download:

- `intentional.exe` for the GUI (double-click to start), and/or
- `intentional-cli.exe` for the CLI (run it from a terminal, e.g. `intentional-cli.exe nl -v FIN`).

No installation or Python is needed. `SHA256SUMS.txt` lists each file's checksum; `Get-FileHash .\intentional.exe` in PowerShell shows the checksum of a downloaded file for comparison.

The executables aren't code-signed, so the first time one is started Windows SmartScreen may show "Windows protected your PC". Select **More info**, then **Run anyway**.

Each release also includes the matching source code (`Source code (zip)`), which can be run or built with the steps in [Development](docs/development.md).

## Quick start

Intentional works on a project folder like this (see [Project folder](docs/user-guide.md#project-folder)):

```text
Intent Creation/
├── intents/              created by a build: the files to import into Dialogflow
├── Training Phrases/
│   └── en/               one phrase file per action, e.g. pay.txt
│       └── NL/           NL phrase files
└── intents.cfg           one intent per line
```

These names are Intentional's own convention, not a Dialogflow requirement, and can be changed (see [Project folder](docs/user-guide.md#project-folder)).

**GUI**: start `intentional.exe`, choose the **Project folder**, and on the **Build DD** tab select **Build DD intents**. The results show below the tabs, and **Open folder** opens the `intents` folder.

**CLI**: from the project folder, run:

```text
intentional-cli.exe validate          check the project first
intentional-cli.exe                   build the DD intents
intentional-cli.exe nl -v FIN         build the NL intents with the FIN prefix
intentional-cli.exe --help            list every command
```

From source, use `uv run intentional` for the GUI and `uv run intentional-cli` for the CLI, after `uv sync --extra gui` (see [Development](docs/development.md#running-from-source)).

## Web prototype (experimental)

A third front end, running entirely in the browser via [Pyodide](https://pyodide.org/) (Python compiled to WebAssembly) — no server, no install, nothing leaves the browser tab. It reuses the same core as the CLI and GUI, so a project's config and phrase files validate identically everywhere.

Today it only covers **Validate**, uploaded as a project zip; the other tasks follow the same pattern and are future work. It isn't part of a release yet — run it from source:

```bash
uv build --wheel && cp dist/*.whl web/
python web/serve.py
```

This opens a local page (no internet needed once the one-time Pyodide/package download finishes); see [Development](docs/development.md#running-the-web-prototype) for details. The page follows your system's light/dark mode automatically, with a toggle to override it.
