"""Rich terminal implementation of the Reporter used by the CLI."""

from collections.abc import Iterator, Sequence
from typing import TypeVar

from rich import box
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from intentional_py import utils
from intentional_py.reporting import (
    BuildResult,
    Check,
    ExtractResult,
    Level,
    ValidateResult,
)

T = TypeVar("T")

_OK = " [green]:heavy_check_mark:[/green]"
_FAIL = " [red]:x:[/red]"


class RichReporter:
    def __init__(self, quiet: bool = False, test: bool = False) -> None:
        self.quiet = quiet
        self.test = test
        self.console = Console()

    def _hidden(self, level: Level) -> bool:
        return self.quiet and level != "error"

    def message(self, level: Level, text: str) -> None:
        if not self._hidden(level):
            self.console.print(text)

    def table(
        self,
        columns: list[str],
        rows: list[list[str]],
        level: Level = "info",
        title: str = "",
    ) -> None:
        if self._hidden(level):
            return
        table = Table(*columns, title=title, box=box.ROUNDED)
        for row in rows:
            table.add_row(*row)
        self.console.print(table)

    def track(self, items: Sequence[T], label: str) -> Iterator[T]:
        if self.test:
            progress = Progress(TextColumn(label), console=self.console)
        else:
            progress = Progress(
                TextColumn(
                    f"{label}: [progress.percentage]{{task.percentage:>3.0f}}%\n"
                ),
                BarColumn(bar_width=15),
                MofNCompleteColumn(),
                TextColumn("|"),
                TimeRemainingColumn(elapsed_when_finished=True),
                console=self.console,
            )
        with progress:
            yield from progress.track(items)

    def confirm(self, question: str) -> bool:
        while True:
            answer = input(f"\n{question} Y/N? ")
            try:
                return bool(utils.strtobool(answer))
            except ValueError:
                self.console.print("Invalid input. Please enter 'yes' or 'no'")

    def show_build(self, result: BuildResult) -> None:
        if self.test:
            self.console.print("build complete")
            return
        columns = ["Time", "Intents", "Phrases", "Entities", "Languages", "Files"]
        row = [
            f"{result.elapsed:.3f} s",
            str(result.intents),
            str(result.phrases),
            str(result.entities),
            ", ".join(result.languages),
            str(result.files),
        ]
        if result.nomatch:
            columns.append("NoMatch")
            row.append(str(result.nomatch))
        self.table(columns, [row])
        if result.ml_disabled:
            self.table(
                ["Intents with ML Disabled"], [[name] for name in result.ml_disabled]
            )

    def show_extract(self, result: ExtractResult) -> None:
        if self.test:
            self.console.print("extract complete")
        else:
            self.table(
                ["Time", "Files", "Phrases"],
                [[f"{result.elapsed:.3f} s", str(result.files), str(result.phrases)]],
            )
        for sheet_name in result.empty_sheets:
            self.message(
                "warning",
                f"[yellow]Warning:[/yellow] sheet [blue]{sheet_name}[/blue] has no phrases; an empty text file was created.",
            )

    def show_validate(self, result: ValidateResult) -> None:
        if self.test:
            self.console.print("validation complete")
            return
        if not self.quiet:
            self.console.print(self._grid(result.directories))
            if result.used_standard_configs:
                self.console.print("Using [purple]STANDARD[/purple] config files")
            self.console.print(self._grid(result.config_files))
        self.console.print(self._grid(result.configs, show_details=not self.quiet))

    @staticmethod
    def _grid(checks: list[Check], show_details: bool = False) -> Table:
        grid = Table.grid(expand=False)
        grid.add_column(ratio=1, no_wrap=True)
        grid.add_column(ratio=1, no_wrap=True, justify="center")
        for check in checks:
            grid.add_row(check.label, _OK if check.ok else _FAIL)
            if show_details:
                for detail in check.details:
                    grid.add_row(f"{'.' * 5} {detail}", "")
        return grid
