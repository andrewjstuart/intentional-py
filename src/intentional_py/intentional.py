"""CLI interface for intentional-py using Typer.

Provides the intentional-cli command:
- Standard DD mode (default): Create intents from intents.cfg
- Natural Language (nl): Create intents from training phrases with auto-config
- Extract (x): Extract phrases from Excel files
- Validate: Validate project structure before processing
- Compare: Compare what a build would produce with an agent export
- Design: Create the config file from the Excel design document
- GUI (gui): Open the graphical interface

Uses Typer with Rich formatting for a modern terminal experience.
"""

import re
import sys
from pathlib import Path
from typing import Annotated

import typer
import typer.core
from rich import print
from rich.console import Console

from intentional_py import (
    __app_name__,
    __version__,
    constants,
    design_doc,
    exceptions,
    user_settings,
)
from intentional_py import build_intents as build
from intentional_py import extract as extracting
from intentional_py import report as report_writer
from intentional_py import validate as validating
from intentional_py.models import (
    LanguageSettings,
    NamingRules,
    NlDefaults,
    ProjectLayout,
)
from intentional_py.rich_reporter import RichReporter

console = Console()


class AliasGroup(typer.core.TyperGroup):
    """Typer Group subclass that supports commands with aliases.
    To alias a command, include the aliases in the command name,
    separated by pipes or commas.
    """

    _CMD_SPLIT_P = re.compile(r" ?[,|] ?")

    def get_command(self, ctx, cmd_name):
        cmd_name = self._group_cmd_name(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _group_cmd_name(self, default_name):
        for cmd in self.commands.values():
            name = cmd.name
            if name and default_name in self._CMD_SPLIT_P.split(name):
                return name
        return default_name


app = typer.Typer(rich_markup_mode="rich", name="intentional_py", cls=AliasGroup)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} version {__version__}")
        raise typer.Exit()


def _report_callback(path: Path | None) -> Path | None:
    if path and path.suffix.casefold() not in {".md", ".markdown", ".csv"}:
        raise typer.BadParameter("Use a Markdown (.md) or CSV (.csv) extension.")
    if path and not path.parent.exists():
        raise typer.BadParameter(f"Folder does not exist: {path.parent}")
    return path


def _save_report(
    path: Path | None,
    title: str,
    result: report_writer.Result,
    reporter: RichReporter,
) -> None:
    if path:
        saved = report_writer.write(path, title, result, reporter.issues)
        reporter.message("info", f"[green]Report saved to[/green] [blue]{saved}[/blue]")


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show the application's version and exit",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-config",
            help="Name of the config file when not using the standard files. (default: intents.cfg)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    clean: Annotated[
        bool,
        typer.Option(
            "--clean",
            help="Zip and remove everything in the intents folder before building, so no old intents are left.",
        ),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
    test: Annotated[
        bool,
        typer.Option(
            "--test",
            "-t",
            help="This is only used for testing to alter output",
            hidden=True,
        ),
    ] = False,
    ctx: typer.Context = typer.Option(None),
) -> None:
    # default to standard DD functionality
    if ctx.invoked_subcommand is None:
        quiet = False if test else quiet
        reporter = RichReporter(quiet=quiet, test=test)
        layout = user_settings.load_project_layout()
        # the config's folder holds the training phrases and receives the intents
        config = (config or Path(layout.dd_config)).resolve()
        try:
            result = build.intents(
                "DD",
                config,
                config.parent,
                reporter,
                clean,
                user_settings.load_naming_rules(),
                layout,
                user_settings.load_language_settings(),
            )
            reporter.show_build(result)
            _save_report(report, "Build DD intents", result, reporter)
        except exceptions.IntentionalException as e:
            console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e!s}\n")
            raise typer.Exit(code=1)
    else:
        # Using another mode i.e. NL, Validate, Extract, GUI
        pass


@app.command("nl | natural-language")
def natural_language(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Name of the config file when not using the standard files. (default: intents_nl.cfg)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    reuse: Annotated[
        bool,
        typer.Option(
            "--reuse",
            "-r",
            help="Reuse the previously created NL config file.",
            rich_help_panel="Natural Language Options",
        ),
    ] = False,
    vertical: Annotated[
        str,
        typer.Option(
            "--vertical",
            "-v",
            help="Vertical prefix abbreviation used for the NL intent names. [bold red]Rebuilds the NL config file[/bold red]",
            rich_help_panel="Natural Language Options",
        ),
    ] = "",
    context: Annotated[
        str | None,
        typer.Option(
            "--context",
            "-c",
            help="Context used for the NL intent names. [bold red]Rebuilds the NL config file[/bold red] (default: GetIntent)",
            rich_help_panel="Natural Language Options",
        ),
    ] = None,
    lowercase: Annotated[
        bool,
        typer.Option(
            "--lowercase",
            "-lc",
            help="Certain clients coded the NL actions in lowercase instead of the standard uppercase.",
            rich_help_panel="Natural Language Options",
        ),
    ] = False,
    clean: Annotated[
        bool,
        typer.Option(
            "--clean",
            help="Zip and remove everything in the intents folder before building, so no old intents are left.",
        ),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
    test: Annotated[
        bool,
        typer.Option(
            "--test",
            "-t",
            help="This is only used for testing to alter output",
            hidden=True,
        ),
    ] = False,
) -> None:
    """
    Use specific NL config and directories for training phrases.
    """

    quiet = False if test else quiet
    reporter = RichReporter(quiet=quiet, test=test)
    layout = user_settings.load_project_layout()
    context = context or user_settings.load_nl_defaults().context
    # the config's folder holds the training phrases and receives the intents
    config = (config or Path(layout.nl_config)).resolve()
    try:
        # rebuild the NL config unless --reuse is given and it exists; ask for a vertical if missing
        file_not_exist: bool = not config.exists()
        if not reuse or file_not_exist:
            if file_not_exist:
                print(
                    f"Existing config [red]{config}[/red] not found, creating [yellow]new config[/yellow]"
                )
            if not vertical:
                use_vertical: str = typer.prompt(
                    "No vertical prefix abbreviation provided.\nEnter a vertical prefix abbreviation: "
                )
                vertical = use_vertical
            build.nl_config(config, vertical, context, lowercase, reporter, layout)

        result = build.intents(
            "NL",
            config,
            config.parent,
            reporter,
            clean,
            user_settings.load_naming_rules(),
            layout,
            user_settings.load_language_settings(),
        )
        reporter.show_build(result)
        _save_report(report, "Build NL intents", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e!s}\n")
        raise typer.Exit(code=1)


@app.command("x | extract")
def extract(
    xl_file: Annotated[
        Path | None,
        typer.Option(
            "--file",
            "-f",
            help="Name of the EXCEL file used to extract data",
            rich_help_panel="Extract File Options",
        ),
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Mode to save data: [yellow]'DD'[/yellow] or [yellow]'NL'[/yellow]",
            rich_help_panel="Extract File Options",
        ),
    ] = "NL",
    language: Annotated[
        str,
        typer.Option(
            "--language",
            "--lang",
            "-l",
            help="Language abbreviation to use: [green]'en', 'es', 'fr'[/green] by default (see 'language-settings')",
            rich_help_panel="Extract File Options",
        ),
    ] = "en",
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Use this flag to suppress most output.",
        ),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
    test: Annotated[
        bool,
        typer.Option(
            "--test",
            "-t",
            help="This is only used for testing to alter output",
            hidden=True,
        ),
    ] = False,
) -> None:
    """
    Extract data from EXCEL file, saving phrases into correct directory
    """
    try:
        # check options
        valid_langs: list = sorted(user_settings.load_language_settings().codes)
        valid_modes: list = ["dd", "nl"]
        # we'll always have a language and mode because of defaults
        if language.lower() not in valid_langs:
            print("[red]Invalid language code used![/red]")
            new_language: str = typer.prompt(
                f"Please provide a valid language code such as {valid_langs}: "
            )
            if new_language.lower() not in valid_langs:
                raise exceptions.ConfigurationError(
                    f"Invalid language code: {new_language}. Valid codes: {valid_langs}\n[bold][red]Abort processing...[/bold][/red]"
                )
            else:
                language = new_language
        if mode.lower() not in valid_modes:
            print("[red]Invalid mode used![/red]")
            new_mode: str = typer.prompt(
                f"Please provide a valid mode such as {valid_modes}: "
            )
            if new_mode.lower() not in valid_modes:
                raise exceptions.ConfigurationError(
                    f"Invalid mode: {new_mode}. Valid modes: {valid_modes}\n[bold][red]Abort processing...[/bold][/red]"
                )
            else:
                mode = new_mode

        if xl_file is None:
            new_xl_file: str = typer.prompt(
                "Please provide an EXCEL filename (or path) to use for extraction"
            )
            xl_file = Path(new_xl_file)

        if not xl_file.is_file():
            raise exceptions.FileSystemError(
                f"{xl_file} does [red]NOT[/red] exist as a file.\n[bold][red]Abort processing...[/bold][/red]"
            )
        quiet = False if test else quiet
        reporter = RichReporter(quiet=quiet, test=test)
        # phrases go to the CWD; tests keep them beside the Excel file instead
        base_dir = xl_file.parent if test else Path.cwd()
        result = extracting.excel_data(
            xl_file,
            mode.upper(),
            language.lower(),
            base_dir,
            reporter,
            user_settings.load_project_layout(),
        )
        reporter.show_extract(result)
        _save_report(report, "Extract phrases", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e!s}\n")
        raise typer.Exit(code=1)


@app.command("validate")
def validate(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="Name of the config file when not using the standard files.",
        ),
    ] = Path(""),
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
    test: Annotated[
        bool,
        typer.Option(
            "--test",
            "-t",
            help="This is only used for testing to alter output",
            hidden=True,
        ),
    ] = False,
) -> None:
    """
    Optionally validate directories, phrase files, config files before running script
    """
    try:
        quiet = False if test else quiet
        reporter = RichReporter(quiet=quiet, test=test)
        # without a valid config file, the standard files in the CWD are validated
        base_dir = config.resolve().parent if config.is_file() else Path.cwd()
        result = validating.validate(
            config,
            base_dir,
            reporter,
            user_settings.load_naming_rules(),
            user_settings.load_project_layout(),
            user_settings.load_language_settings(),
        )
        reporter.show_validate(result)
        _save_report(report, "Validate", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)


@app.command("gui")
def gui(
    project: Annotated[
        Path | None,
        typer.Option(
            "--project",
            "-p",
            help="Project folder to open in the GUI. (default: current directory)",
        ),
    ] = None,
) -> None:
    """
    Open the graphical interface.
    """
    if project is not None and not project.is_dir():
        console.print(
            f"\n[bold][red]✗ Error:[/red][/bold] Project folder does not exist: {project}\n"
        )
        raise typer.Exit(code=1)
    try:
        # imported here so the CLI works without the optional GUI packages
        import tkinter

        from intentional_py.gui import app as gui_app
    except ImportError as e:
        if getattr(sys, "frozen", False):
            # the packaged CLI leaves the GUI out; it ships as intentional.exe
            hint = "Run [cyan]intentional.exe[/cyan] to open the GUI."
        else:
            hint = (
                "Install it with [cyan]uv sync --extra gui[/cyan] or "
                "[cyan]pip install intentional-py\\[gui][/cyan]."
            )
        console.print(
            f"\n[bold][red]✗ Error:[/red][/bold] The GUI is not available ({e}).\n{hint}\n"
        )
        raise typer.Exit(code=1)
    try:
        gui_app.main((project or Path.cwd()).resolve())
    except tkinter.TclError as e:
        console.print(
            f"\n[bold][red]✗ Error:[/red][/bold] Could not open the GUI ({e}).\n"
            "This usually means no display is available (e.g. a headless server or "
            "a container/SSH session without X11 forwarding). Use intentional-cli's "
            "other commands instead, or connect with a display available.\n"
        )
        raise typer.Exit(code=1)


@app.command("compare")
def compare(
    export: Annotated[
        Path,
        typer.Option(
            "--export",
            "-e",
            help="Agent export (zip or unzipped folder), or an intents folder, to compare with.",
        ),
    ],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Mode of the config: [yellow]'DD'[/yellow] or [yellow]'NL'[/yellow]",
        ),
    ] = "DD",
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Config file to build from. (default: intents.cfg, or intents_nl.cfg for NL)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
) -> None:
    """
    Compare what the config would build with an agent export, without writing any files
    """
    reporter = RichReporter(quiet=quiet)
    try:
        mode = mode.upper()
        if mode not in constants.VALID_MODES:
            raise exceptions.ConfigurationError(
                f"Invalid mode: {mode}. Valid modes: DD, NL"
            )
        layout = user_settings.load_project_layout()
        default = layout.nl_config if mode == "NL" else layout.dd_config
        config = (config or Path(default)).resolve()
        result = build.compare_build(
            mode,
            config,
            config.parent,
            export.resolve(),
            reporter,
            user_settings.load_naming_rules(),
            layout,
            user_settings.load_language_settings(),
        )
        reporter.show_compare(result)
        _save_report(report, "Compare intents", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)


@app.command("package")
def package(
    export: Annotated[
        Path,
        typer.Option(
            "--export",
            "-e",
            help="Agent export zip to merge this config's build into. The export itself is never modified; a timestamped copy is written next to it.",
        ),
    ],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Mode of the config: [yellow]'DD'[/yellow] or [yellow]'NL'[/yellow]",
        ),
    ] = "DD",
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Config file to build from. (default: intents.cfg, or intents_nl.cfg for NL)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
) -> None:
    """
    Merge this config's build into a copy of an agent export zip, ready to re-import: new or changed intents are added, and a '-'/'--' removal row also deletes its files from the copy.
    """
    reporter = RichReporter(quiet=quiet)
    try:
        mode = mode.upper()
        if mode not in constants.VALID_MODES:
            raise exceptions.ConfigurationError(
                f"Invalid mode: {mode}. Valid modes: DD, NL"
            )
        layout = user_settings.load_project_layout()
        default = layout.nl_config if mode == "NL" else layout.dd_config
        config = (config or Path(default)).resolve()
        result = build.package_export(
            mode,
            config,
            config.parent,
            export.resolve(),
            reporter,
            user_settings.load_naming_rules(),
            layout,
            user_settings.load_language_settings(),
        )
        reporter.show_package(result)
        _save_report(report, "Package export", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)


@app.command("design")
def design(
    xl_file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Excel design document with the intent rows"),
    ],
    sheet: Annotated[
        str,
        typer.Option(
            "--sheet",
            "-s",
            help="Sheet to read. (default: the first sheet with an intent header row)",
        ),
    ] = "",
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Config file to write; an existing one is backed up first. (default: intents.cfg)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Save a Markdown (.md) or CSV (.csv) report of the completed job.",
            callback=_report_callback,
        ),
    ] = None,
) -> None:
    """
    Create the config file from the Excel design document
    """
    reporter = RichReporter(quiet=quiet)
    try:
        if not xl_file.is_file():
            raise exceptions.FileSystemError(
                f"{xl_file} does [red]NOT[/red] exist as a file."
            )
        layout = user_settings.load_project_layout()
        config = config or Path(layout.dd_config)
        result = design_doc.config_from_design(
            xl_file.resolve(),
            config.resolve(),
            reporter,
            sheet,
            user_settings.load_naming_rules(),
        )
        reporter.show_design(result)
        _save_report(report, "Create config from design document", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)


@app.command("naming-rules")
def naming_rules(
    set_intent_forbidden_chars: Annotated[
        str | None,
        typer.Option(
            "--set-intent-forbidden-chars",
            help="Characters that make an intent name invalid (a fatal error). (default: -)",
        ),
    ] = None,
    set_context_discouraged_chars: Annotated[
        str | None,
        typer.Option(
            "--set-context-discouraged-chars",
            help="Characters that make a context print a warning. (default: .)",
        ),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset both back to their original defaults."),
    ] = False,
) -> None:
    """
    Show or change the saved intent/context naming rules.

    These are not Dialogflow requirements, just this project's naming convention.
    Saved to the user's profile, so a change applies to every project, on the CLI
    and the GUI, until changed again.
    """
    rules = user_settings.load_naming_rules()
    changed = reset
    if reset:
        rules = NamingRules()
    if set_intent_forbidden_chars is not None:
        rules.intent_forbidden_chars = set_intent_forbidden_chars
        changed = True
    if set_context_discouraged_chars is not None:
        rules.context_discouraged_chars = set_context_discouraged_chars
        changed = True
    if changed:
        user_settings.save_naming_rules(rules)
        console.print(f"[green]Saved to {user_settings.naming_rules_path()}[/green]\n")
    console.print(
        f"Intent forbidden characters: [yellow]'{rules.intent_forbidden_chars}'[/yellow]"
    )
    console.print(
        f"Context discouraged characters: [yellow]'{rules.context_discouraged_chars}'[/yellow]"
    )


@app.command("project-layout")
def project_layout(
    set_training_phrases_dir: Annotated[
        str | None,
        typer.Option(
            "--set-training-phrases-dir",
            help="Folder holding the training phrases. (default: Training Phrases)",
        ),
    ] = None,
    set_intents_dir: Annotated[
        str | None,
        typer.Option(
            "--set-intents-dir",
            help="Folder that receives the built intents. (default: intents)",
        ),
    ] = None,
    set_nl_subfolder: Annotated[
        str | None,
        typer.Option(
            "--set-nl-subfolder",
            help="Subfolder, under each language, holding NL phrases. (default: NL)",
        ),
    ] = None,
    set_dd_config: Annotated[
        str | None,
        typer.Option(
            "--set-dd-config",
            help="Default directed dialog config file name. (default: intents.cfg)",
        ),
    ] = None,
    set_nl_config: Annotated[
        str | None,
        typer.Option(
            "--set-nl-config",
            help="Default natural language config file name. (default: intents_nl.cfg)",
        ),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option(
            "--reset", help="Reset all of these back to their original defaults."
        ),
    ] = False,
) -> None:
    """
    Show or change the saved project folder/file layout.

    This is not a Dialogflow requirement, just this project's organization.
    Saved to the user's profile, so a change applies to every project, on the CLI
    and the GUI, until changed again.
    """
    layout = user_settings.load_project_layout()
    changed = reset
    if reset:
        layout = ProjectLayout()
    if set_training_phrases_dir is not None:
        layout.training_phrases_dir = set_training_phrases_dir
        changed = True
    if set_intents_dir is not None:
        layout.intents_dir = set_intents_dir
        changed = True
    if set_nl_subfolder is not None:
        layout.nl_subfolder = set_nl_subfolder
        changed = True
    if set_dd_config is not None:
        layout.dd_config = set_dd_config
        changed = True
    if set_nl_config is not None:
        layout.nl_config = set_nl_config
        changed = True
    if changed:
        user_settings.save_project_layout(layout)
        console.print(
            f"[green]Saved to {user_settings.project_layout_path()}[/green]\n"
        )
    console.print(
        f"Training phrases folder: [yellow]'{layout.training_phrases_dir}'[/yellow]"
    )
    console.print(f"Intents output folder: [yellow]'{layout.intents_dir}'[/yellow]")
    console.print(f"NL phrases subfolder: [yellow]'{layout.nl_subfolder}'[/yellow]")
    console.print(f"Directed dialog config file: [yellow]'{layout.dd_config}'[/yellow]")
    console.print(
        f"Natural language config file: [yellow]'{layout.nl_config}'[/yellow]"
    )


@app.command("nl-defaults")
def nl_defaults(
    set_context: Annotated[
        str | None,
        typer.Option(
            "--set-context",
            help="Default context prefilled for 'nl --context'. (default: GetIntent)",
        ),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset back to the original default."),
    ] = False,
) -> None:
    """
    Show or change the saved default NL context.

    This is not a Dialogflow requirement, just the name a team uses for the context
    shared by every NL intent. Saved to the user's profile, so a change applies to
    every project, on the CLI and the GUI, until changed again.
    """
    defaults = user_settings.load_nl_defaults()
    changed = reset
    if reset:
        defaults = NlDefaults()
    if set_context is not None:
        defaults.context = set_context
        changed = True
    if changed:
        user_settings.save_nl_defaults(defaults)
        console.print(f"[green]Saved to {user_settings.nl_defaults_path()}[/green]\n")
    console.print(f"Default NL context: [yellow]'{defaults.context}'[/yellow]")


@app.command("language-settings")
def language_settings(
    add: Annotated[
        list[str] | None,
        typer.Option(
            "--add",
            help="Add or update a language, as CODE=Name (e.g. --add de=German) or just "
            "CODE to look its name up in the full Dialogflow ES catalog. Repeatable.",
        ),
    ] = None,
    remove: Annotated[
        list[str] | None,
        typer.Option("--remove", help="Remove a language by its code. Repeatable."),
    ] = None,
    set_default: Annotated[
        str | None,
        typer.Option(
            "--set-default",
            help="Language every intent needs a row for, synthesized from another "
            "row's phrases when missing. (default: en)",
        ),
    ] = None,
    reset: Annotated[
        bool,
        typer.Option(
            "--reset", help="Reset back to the original supported languages (en/es/fr)."
        ),
    ] = False,
) -> None:
    """
    Show or change the saved supported language set.

    Not a Dialogflow requirement to support every one of these - this is just which
    languages this tool checks for and accepts in a config file's Language column.
    Saved to the user's profile, so a change applies to every project, on the CLI and
    the GUI, until changed again.
    """
    try:
        settings = user_settings.load_language_settings()
        changed = reset
        if reset:
            settings = LanguageSettings()
        for item in add or []:
            code, has_name, name = item.strip().partition("=")
            code = code.strip().lower()
            name = name.strip()
            if not code:
                raise exceptions.ConfigurationError(f"Invalid --add value: '{item}'.")
            if not has_name:
                name = constants.ALL_DIALOGFLOW_LANGUAGES.get(code, "")
                if not name:
                    raise exceptions.ConfigurationError(
                        f"'{code}' is not in the Dialogflow ES catalog; "
                        "use --add CODE=Name to give it a name."
                    )
            settings.languages[code] = name
            changed = True
        for item in remove or []:
            code = item.strip().lower()
            if code == settings.default_language:
                raise exceptions.ConfigurationError(
                    f"Cannot remove '{code}': it is the default language "
                    "(change --set-default first)."
                )
            settings.languages.pop(code, None)
            changed = True
        if set_default is not None:
            code = set_default.strip().lower()
            if code not in settings.languages:
                raise exceptions.ConfigurationError(
                    f"'{code}' is not in the supported language set; add it first."
                )
            settings.default_language = code
            changed = True
        if changed:
            user_settings.save_language_settings(settings)
            console.print(
                f"[green]Saved to {user_settings.language_settings_path()}[/green]\n"
            )
        console.print(
            f"Default language: [yellow]'{settings.default_language}'[/yellow]"
        )
        console.print("Supported languages:")
        for code, name in sorted(settings.languages.items()):
            console.print(f"  [yellow]{code}[/yellow]: {name}")
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)
