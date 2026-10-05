"""Rich terminal implementation of the Reporter used by the CLI."""

import re
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
from rich.text import Text

from intentional_py import utils
from intentional_py.reporting import (
    BuildResult,
    Check,
    CompareResult,
    DesignResult,
    ExtractResult,
    Level,
    PackageResult,
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
        self.issues: list[tuple[Level, str, str]] = []

    def _hidden(self, level: Level) -> bool:
        return self.quiet and level != "error"

    def message(self, level: Level, text: str) -> None:
        if level in {"warning", "error"}:
            plain = Text.from_markup(text).plain.strip()
            plain = re.sub(r"^(Warning|Error):\s*", "", plain)
            match = re.match(r"Row (\d+):\s*(.*)", plain, re.DOTALL)
            self.issues.append(
                (level, match[1], match[2]) if match else (level, "", plain)
            )
        if not self._hidden(level):
            self.console.print(text)

    def table(
        self, columns: list[str], rows: list[list[str]], level: Level = "info"
    ) -> None:
        if level in {"warning", "error"}:
            title = " | ".join(Text.from_markup(column).plain for column in columns)
            self.issues.extend(
                (
                    level,
                    "",
                    f"{title}: "
                    + " | ".join(Text.from_markup(cell).plain for cell in row),
                )
                for row in rows
            )
        if self._hidden(level):
            return
        table = Table(*columns, box=box.ROUNDED)
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

    def confirm(self, question: str, details: Sequence[str] | None = None) -> bool:
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
        if result.machine_learning_off:
            self.table(
                ["Intents with Machine Learning Off"],
                [[name] for name in result.machine_learning_off],
            )
        if result.backup:
            self.message(
                "info",
                f"[green]Previous intents saved to[/green] [blue]{result.backup}[/blue]",
            )
        changes = result.changes
        if changes:
            summary = (
                f"Compared with the previous build: {len(changes.added)} added, "
                f"{len(changes.changed)} changed, {changes.unchanged} unchanged."
            )
            self.message("info", summary)
            if changes.removed and not result.backup and not self._hidden("warning"):
                self.console.print(
                    f"[yellow]Warning:[/yellow] {len(changes.removed)} intent(s) are no longer built but "
                    "their files are still in the intents folder: "
                    f"{', '.join(changes.removed)}. Use --clean to remove them."
                )

    def show_compare(self, result: CompareResult) -> None:
        self.table(
            ["Time", "Added", "Changed", "Unchanged", "Only in export"],
            [
                [
                    f"{result.elapsed:.3f} s",
                    str(len(result.added)),
                    str(len(result.changed)),
                    str(result.unchanged),
                    str(len(result.removed)),
                ]
            ],
        )
        if result.added:
            self.table(["New intents"], [[name] for name in result.added])
        if result.changed:
            self.table(
                ["Changed intent", "Changes"],
                [[change.name, "\n".join(change.details)] for change in result.changed],
            )
        if result.removed:
            self.table(
                [f"Only in {result.source} (not built by this config)"],
                [[name] for name in result.removed],
            )

    def show_package(self, result: PackageResult) -> None:
        self.table(
            ["Time", "Added", "Changed", "Unchanged", "Removed", "Only in export"],
            [
                [
                    f"{result.elapsed:.3f} s",
                    str(len(result.added)),
                    str(len(result.changed)),
                    str(result.unchanged),
                    str(len(result.removed)),
                    str(len(result.unmarked)),
                ]
            ],
        )
        if result.added:
            self.table(["New intents"], [[name] for name in result.added])
        if result.changed:
            self.table(
                ["Changed intent", "Changes"],
                [[change.name, "\n".join(change.details)] for change in result.changed],
            )
        if result.removed:
            self.table(
                ["Removed (marked with '-'/'--')"], [[name] for name in result.removed]
            )
        if result.unmarked:
            self.table(
                [f"Only in {result.source} (not built by this config)"],
                [[name] for name in result.unmarked],
            )
        if result.output:
            self.message(
                "info",
                f"[green]Updated export written to[/green] [blue]{result.output}[/blue]",
            )

    def show_design(self, result: DesignResult) -> None:
        self.table(
            ["Sheet", "Rows", "Config"],
            [[result.sheet, str(result.rows), str(result.config)]],
        )
        if result.backup:
            self.message(
                "info",
                f"[green]Previous config saved to[/green] [blue]{result.backup}[/blue]",
            )
        for error in result.errors:
            self.console.print(f"    Error: {error}", style="red", markup=False)
        if not self.quiet:
            for warning in result.warnings:
                self.console.print(
                    f"    Warning: {warning}", style="yellow", markup=False
                )
        if result.errors:
            self.message(
                "error",
                "[red]Fix the errors in the design document before building.[/red]",
            )

    def show_extract(self, result: ExtractResult) -> None:
        if self.test:
            self.console.print("extract complete")
        else:
            self.table(
                ["Time", "Files", "Phrases"],
                [[f"{result.elapsed:.3f} s", str(result.files), str(result.phrases)]],
            )
        if result.backup:
            self.message(
                "info",
                f"[green]Previous phrases saved to[/green] [blue]{result.backup}[/blue]",
            )
        for sheet_name in result.empty_sheets:
            if not self._hidden("warning"):
                self.console.print(
                    f"[yellow]Warning:[/yellow] sheet [blue]{sheet_name}[/blue] has no phrases; "
                    "an empty text file was created."
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
        for check in result.configs:
            self.console.print(self._grid([check]))
            if not self.quiet:
                for detail in check.details:
                    # details can contain paths, so they are printed without markup
                    style = "red" if detail.startswith("Error") else "yellow"
                    self.console.print(f"    {detail}", style=style, markup=False)

    @staticmethod
    def _grid(checks: list[Check]) -> Table:
        grid = Table.grid(expand=False)
        grid.add_column(ratio=1, no_wrap=True)
        grid.add_column(ratio=1, no_wrap=True, justify="center")
        for check in checks:
            grid.add_row(check.label, _OK if check.ok else _FAIL)
        return grid
