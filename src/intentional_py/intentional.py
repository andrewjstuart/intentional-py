"""CLI interface for intentional-py using Typer.

Provides the intentional-cli command:
- Standard DD mode (default): Create intents from intents.cfg
- Natural Language (nl): Create intents from training phrases with auto-config
- Extract (x): Extract phrases from Excel files
- Validate: Validate project structure before processing
- GUI (gui): Open the graphical interface

Uses Typer with Rich formatting for a modern terminal experience.
"""

import re
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
import typer.core
from rich import print
from rich.console import Console

from intentional_py import __app_name__, __version__, constants, exceptions
from intentional_py import build_intents as build
from intentional_py import extract as extracting
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
            reporter.show_build(build.intents("DD", config, config.parent, reporter))
        except exceptions.IntentionalException as e:
            console.print(f"\n[bold][red]✗ Error:[/red][/bold] {str(e)}\n")
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

        reporter.show_build(build.intents("NL", config, config.parent, reporter))
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {str(e)}\n")
        raise typer.Exit(code=1)


@app.command("x | extract")
def extract(
    xl_file: Annotated[
        Optional[Path],
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
        reporter.show_extract(
            extracting.excel_data(
                xl_file, mode.upper(), language.lower(), base_dir, reporter
            )
        )
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {str(e)}\n")
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
        reporter.show_validate(validating.validate(config, base_dir, reporter))
    except exceptions.IntentionalException as e:
        console.print(f"\n[bold][red]✗ Error:[/red][/bold] {e}\n")
        raise typer.Exit(code=1)


@app.command("gui")
def gui(
    project: Annotated[
        Optional[Path],
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
