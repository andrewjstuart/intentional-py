import typer
from rich import print
from typing_extensions import Annotated
import re
import os
import typer.core
from intentional_py import __app_name__, __version__
from intentional_py import build_intents as build
from intentional_py import extract as xtract
from intentional_py import validate as valid


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
        str,
        typer.Option(
            "--config",
            "-config",
            help="Name of the config file when not using the standard files.",
        ),
    ] = "intents.cfg",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
    ctx: typer.Context = typer.Option(None),
) -> None:
    # default to standard DD functionality
    if ctx.invoked_subcommand is None:
        build.intents("DD", config, quiet)
    else:
        # Using another mode i.e. NL, Validate, Extract
        pass


@app.command("nl | natural-language")
def natural_language(
    config: Annotated[
        str,
        typer.Option(
            "--config",
            help="Name of the config file when not using the standard files.",
        ),
    ] = "intents_nl.cfg",
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
    ] = "GetIntent",
    lowercase: Annotated[
        bool,
        typer.Option(
            "--lowercase",
            "-lc",
            help="Certain clients coded the NL actions in lowercase instead of the standard uppercase.",
            rich_help_panel="Natural Language Options",
        ),
    ] = False,
) -> None:
    """
    Use specific NL config and directories for training phrases.
    """

    # check if file exists, otherwise prompt for nl config file name
    file_not_exist: bool = not os.path.exists(config)
    if not reuse or file_not_exist:
        if file_not_exist:
            print(
                f"Existing config [red]{config}[/red] not found, creating [yellow]new config[/yellow]"
            )
            # uses default name and intent
        if not vertical:
            use_vertical: str = typer.prompt(
                "No vertical prefix abbreviation provided.\nEnter a vertical prefix abbreviation: "
            )
            vertical = use_vertical
        build.nl_config(config, vertical, context, lowercase, quiet)
    else:
        # print("Reusing the previously created NL config file")
        pass

    build.intents("NL", config, quiet)


@app.command("extract")
def extract(
    xl_file: Annotated[
        str,
        typer.Option(
            "--file",
            "-f",
            help="Name of the EXCEL file used to extract data",
            rich_help_panel="Extract File Options",
        ),
    ] = "",
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
) -> None:
    """
    Extract data from EXCEL file, saving phrases into correct directory
    """
    # check options
    valid_langs: list = ["en", "es", "fr"]
    valid_modes: list = ["dd", "nl"]
    # we'll always have a language and mode because of defaults
    if language.lower() not in valid_langs:
        print(f"[red]Invalid language code used![/red]")
        new_language: str = typer.prompt(
            f"Please provide a valid language code such as {valid_langs}: "
        )
        if new_language.lower() not in valid_langs:
            print(
                f"[red]Invalid language code used![/red]\n[bold][red]Abort processing...[/bold][/red]"
            )
            exit()
        else:
            language = new_language
    if mode.lower() not in valid_modes:
        print(f"[red]Invalid mode used![/red]")
        new_mode: str = typer.prompt(
            f"Please provide a valid mode such as {valid_modes}: "
        )
        if new_mode.lower() not in valid_modes:
            print(
                f"[red]Invalid mode used![/red]\n[bold][red]Abort processing...[/bold][/red]"
            )
            exit()
        else:
            mode = new_mode

    if not xl_file:
        new_xl_file: str = typer.prompt(
            "Please provide an EXCEL filename (or path) to use for extraction: "
        )
        xl_file = new_xl_file

    if not os.path.exists(xl_file) and not os.path.isfile(xl_file):
        print(
            f"{xl_file} does [red]NOT[/red] exist as a file.\n[bold][red]Abort processing...[/bold][/red]"
        )
        exit()

    xtract.excel_data(xl_file, mode.upper(), language.lower(), quiet)


@app.command("validate")
def validate(
    config: Annotated[
        str,
        typer.Option(
            "--config",
            help="Name of the config file when not using the standard files.",
        ),
    ] = "",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Use this flag to suppress most output."),
    ] = False,
) -> None:
    """
    Optionally validate directories, phrase files, config files before running script
    """

    valid.validate(config, quiet)


if __name__ == "__main__":
    app()
