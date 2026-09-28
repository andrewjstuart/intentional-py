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

from intentional_py import __app_name__, __version__, constants, design_doc, exceptions
from intentional_py import build_intents as build
from intentional_py import extract as extracting
from intentional_py import report as report_writer
from intentional_py import validate as validating
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
        Path,
        typer.Option(
            "--config",
            "-config",
            help="Name of the config file when not using the standard files.",
        ),
    ] = Path(constants.DEFAULT_DD_CONFIG),
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
        # the config's folder holds the training phrases and receives the intents
        config = config.resolve()
        try:
            result = build.intents("DD", config, config.parent, reporter, clean)
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
        Path,
        typer.Option(
            "--config",
            help="Name of the config file when not using the standard files.",
        ),
    ] = Path(constants.DEFAULT_NL_CONFIG),
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
        str,
        typer.Option(
            "--context",
            "-c",
            help="Context used for the NL intent names. [bold red]Rebuilds the NL config file[/bold red]",
            rich_help_panel="Natural Language Options",
        ),
    ] = constants.DEFAULT_NL_CONTEXT,
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
    # the config's folder holds the training phrases and receives the intents
    config = config.resolve()
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
            build.nl_config(config, vertical, context, lowercase, reporter)

        result = build.intents("NL", config, config.parent, reporter, clean)
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
            help="Language abbreviation to use: [green]'en', 'es', 'fr'[/green]",
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
        valid_langs: list = ["en", "es", "fr"]
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
            xl_file, mode.upper(), language.lower(), base_dir, reporter
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
        result = validating.validate(config, base_dir, reporter)
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
            help="Project folder to open in the GUI. [default: current directory]",
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
    gui_app.main(project.resolve() if project else None)


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
        typer.Option("--mode", "-m", help="Mode of the config: [yellow]'DD'[/yellow] or [yellow]'NL'[/yellow]"),
    ] = "DD",
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Config file to build from. [default: intents.cfg, or intents_nl.cfg for NL]",
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
            raise exceptions.ConfigurationError(f"Invalid mode: {mode}. Valid modes: DD, NL")
        default = constants.DEFAULT_NL_CONFIG if mode == "NL" else constants.DEFAULT_DD_CONFIG
        config = (config or Path(default)).resolve()
        result = build.compare_build(
            mode, config, config.parent, export.resolve(), reporter
        )
        reporter.show_compare(result)
        _save_report(report, "Compare intents", result, reporter)
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
        typer.Option("--sheet", "-s", help="Sheet to read. [default: the first sheet with an intent header row]"),
    ] = "",
    config: Annotated[
        Path,
        typer.Option("--config", help="Config file to write; an existing one is backed up first."),
    ] = Path(constants.DEFAULT_DD_CONFIG),
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
            raise exceptions.FileSystemError(f"{xl_file} does [red]NOT[/red] exist as a file.")
        result = design_doc.config_from_design(
            xl_file.resolve(), config.resolve(), reporter, sheet
        )
        reporter.show_design(result)
        _save_report(report, "Create config from design document", result, reporter)
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)
