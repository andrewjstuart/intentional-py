"""Reporter implementation for the browser front end.

Unlike RichReporter (prints) and GuiReporter (streams to a Tkinter window via a
queue), this collects everything in memory and hands it back once the job is
done, since the first version renders a result rather than live progress.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TypeVar

from rich.errors import MarkupError
from rich.text import Text

from intentional_py.reporting import Level

T = TypeVar("T")


def plain_text(text: str) -> str:
    """Strip Rich markup, the same way gui/actions.py does for its own display."""
    try:
        return Text.from_markup(text).plain
    except MarkupError:
        return text


class WebReporter:
    def __init__(self) -> None:
        self.messages: list[tuple[Level, str]] = []
        self.tables: list[tuple[list[str], list[list[str]], Level]] = []

    def message(self, level: Level, text: str) -> None:
        self.messages.append((level, plain_text(text)))

    def table(
        self, columns: list[str], rows: list[list[str]], level: Level = "info"
    ) -> None:
        plain_columns = [plain_text(column) for column in columns]
        plain_rows = [[plain_text(cell) for cell in row] for row in rows]
        self.tables.append((plain_columns, plain_rows, level))

    def track(self, items: Sequence[T], label: str) -> Iterator[T]:
        # no progress bar yet; the browser UI shows the result once the job finishes
        yield from items

    def confirm(self, question: str, details: Sequence[str] | None = None) -> bool:
        # today's only caller is the NL duplicate-phrase prompt; a real browser
        # confirm (pausing for a JS round trip) is future work, not this spike
        return True
