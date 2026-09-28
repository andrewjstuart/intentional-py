"""Windows version resource shared by the PyInstaller spec files.

The version is read from pyproject.toml, so the executables' file properties
(Explorer > Properties > Details) always match the release.
"""

import re
import tomllib
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)


def version_resource(exe_name: str, description: str) -> VSVersionInfo:
    with (Path(__file__).parent / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]
    version = project["version"]
    numbers = [int(part) for part in re.findall(r"\d+", version)[:4]]
    numbers += [0] * (4 - len(numbers))
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=tuple(numbers), prodvers=tuple(numbers)),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", project["authors"][0]["name"]),
                            StringStruct("FileDescription", description),
                            StringStruct("FileVersion", version),
                            StringStruct("InternalName", exe_name),
                            StringStruct("OriginalFilename", f"{exe_name}.exe"),
                            StringStruct("ProductName", "Intentional"),
                            StringStruct("ProductVersion", version),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
