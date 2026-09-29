"""Front-end neutral reporting interface and result types.

The core modules report progress and messages through a ``Reporter`` and return
result objects, so the CLI and GUI can each present them in their own way.
Message text may contain Rich markup; non-Rich front ends should strip it.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, TypeVar

T = TypeVar("T")
Level = Literal["info", "warning", "error"]


class Reporter(Protocol):
    def message(self, level: Level, text: str) -> None: ...

    def table(
        self, columns: list[str], rows: list[list[str]], level: Level = "info"
    ) -> None: ...

    def track(self, items: Sequence[T], label: str) -> Iterator[T]: ...

    def confirm(self, question: str, details: Sequence[str] | None = None) -> bool: ...


@dataclass
class IntentChange:
    name: str
    details: list[str] = field(default_factory=list)


@dataclass
class CompareResult:
    source: str
    added: list[str] = field(default_factory=list)
    changed: list[IntentChange] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # only in the older intents
    unchanged: int = 0
    elapsed: float = 0.0


@dataclass
class BuildResult:
    intents: int = 0
    intent_names: list[str] = field(default_factory=list)
    phrases: int = 0
    entities: int = 0
    languages: list[str] = field(default_factory=list)
    files: int = 0
    nomatch: int = 0
    machine_learning_off: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    output_dir: Path | None = None
    changes: CompareResult | None = (
        None  # against the previous build in the intents folder
    )
    backup: Path | None = None  # zip of the intents folder, when it was cleared first


@dataclass
class ExtractResult:
    output_dir: Path
    files: int = 0
    phrases: int = 0
    empty_sheets: list[str] = field(default_factory=list)
    backup: Path | None = None
    elapsed: float = 0.0


@dataclass
class DesignResult:
    config: Path
    sheet: str
    rows: int = 0
    backup: Path | None = None  # copy of the config file that was replaced
    errors: list[str] = field(default_factory=list)  # from the same checks a build runs
    warnings: list[str] = field(default_factory=list)


@dataclass
class Check:
    label: str
    ok: bool
    details: list[str] = field(default_factory=list)


@dataclass
class ValidateResult:
    directories: list[Check] = field(default_factory=list)
    used_standard_configs: bool = False
    config_files: list[Check] = field(default_factory=list)
    configs: list[Check] = field(default_factory=list)
