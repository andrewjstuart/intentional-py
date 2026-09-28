"""Background job runner that forwards core output to the UI thread through a queue.

Events are tuples whose first item names the event:
    ("message", level, text)
    ("table", columns, rows, level)
    ("progress_start", label, total)
    ("progress", done, total)
    ("confirm", question, details, answer_dict, threading.Event)
    ("done", result)
    ("failed", text)
"""

import queue
import threading
import traceback
from collections.abc import Callable, Iterator, Sequence
from typing import Any, TypeVar

from intentional_py import exceptions
from intentional_py.gui.actions import plain_text
from intentional_py.reporting import Level

T = TypeVar("T")


class GuiReporter:
    """Reporter used on the worker thread; each call becomes an event for the UI thread."""

    def __init__(self, events: queue.Queue) -> None:
        self.events = events

    def message(self, level: Level, text: str) -> None:
        self.events.put(("message", level, plain_text(text).strip("\n")))

    def table(
        self, columns: list[str], rows: list[list[str]], level: Level = "info"
    ) -> None:
        self.events.put(
            (
                "table",
                [plain_text(column) for column in columns],
                [[plain_text(cell) for cell in row] for row in rows],
                level,
            )
        )

    def track(self, items: Sequence[T], label: str) -> Iterator[T]:
        total = len(items)
        self.events.put(("progress_start", plain_text(label), total))
        for done, item in enumerate(items, start=1):
            yield item
            self.events.put(("progress", done, total))

    def confirm(self, question: str, details: Sequence[str] | None = None) -> bool:
        answer: dict = {}
        answered = threading.Event()
        self.events.put(("confirm", question, list(details or []), answer, answered))
        answered.wait()
        return bool(answer.get("value"))


class JobRunner:
    def __init__(self) -> None:
        self.events: queue.Queue = queue.Queue()

    def start(self, job: Callable[[GuiReporter], Any]) -> None:
        reporter = GuiReporter(self.events)

        def run() -> None:
            try:
                self.events.put(("done", job(reporter)))
            except exceptions.IntentionalException as error:
                self.events.put(("failed", plain_text(str(error)).strip()))
            except Exception:  # noqa: BLE001 - surface unexpected errors instead of losing them on this thread
                self.events.put(("failed", traceback.format_exc()))

        threading.Thread(target=run, daemon=True).start()
