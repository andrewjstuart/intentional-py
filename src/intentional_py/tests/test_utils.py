import re
from pathlib import Path

import pytest

from intentional_py import exceptions, utils


def test_timestamp_matches_the_backup_file_name_format() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{6}", utils.timestamp())


def test_safe_join_returns_the_joined_path_for_a_plain_name(tmp_path: Path) -> None:
    assert utils.safe_join(tmp_path, "pay.txt") == tmp_path / "pay.txt"


def test_safe_join_rejects_parent_directory_traversal(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigurationError):
        utils.safe_join(tmp_path, "../../etc/passwd")


def test_safe_join_rejects_an_absolute_path(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigurationError):
        utils.safe_join(tmp_path, str(Path(tmp_path.anchor) / "etc" / "passwd"))


def test_find_phrase_file_rejects_a_traversal_action(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigurationError):
        utils.find_phrase_file(tmp_path, "../../etc/passwd")
