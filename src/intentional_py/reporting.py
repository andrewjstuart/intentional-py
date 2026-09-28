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

    def confirm(self, question: str) -> bool: ...


@dataclass
class BuildResult:
    intents: int = 0
    phrases: int = 0
    entities: int = 0
    languages: list[str] = field(default_factory=list)
    files: int = 0
    nomatch: int = 0
    ml_disabled: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    output_dir: Path | None = None


@dataclass
class ExtractResult:
    output_dir: Path
    files: int = 0
    phrases: int = 0
    empty_sheets: list[str] = field(default_factory=list)
    backup: Path | None = None
    elapsed: float = 0.0


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
