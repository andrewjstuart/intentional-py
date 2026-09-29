"""Compare generated intents with a previous build or a Dialogflow ES agent export.

Intents are compared by name on the fields this tool writes: contexts, action,
priority, machine learning, parameters, and the training phrases per language.
IDs and timestamps are ignored, since they change with every build or export.
"""

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from intentional_py import exceptions, utils
from intentional_py.reporting import CompareResult, IntentChange

USERSAYS = re.compile(r"(.+)_usersays_([A-Za-z-]+)$")


def summarize(files: dict[str, Any]) -> dict[str, dict]:
    """Group intent and usersays JSON (keyed by file name) into one summary per intent."""
    intents: dict[str, dict] = {}
    for file_name, data in files.items():
        stem = Path(file_name).stem
        match = USERSAYS.match(stem)
        if match:
            phrases = sorted(
                "".join(part.get("text", "") for part in item.get("data", []))
                for item in data
                if isinstance(item, dict)
            )
            intents.setdefault(match[1], {}).setdefault("phrases", {})[match[2]] = (
                phrases
            )
        elif isinstance(data, dict):
            intents.setdefault(stem, {})["intent"] = _intent_fields(data)
    return intents


def _intent_fields(data: dict) -> dict:
    response = (data.get("responses") or [{}])[0]
    auto = data.get("auto", True)
    if isinstance(auto, str):
        auto = bool(utils.strtobool(auto))
    return {
        "contexts": sorted(data.get("contexts", [])),
        "action": response.get("action", ""),
        "priority": data.get("priority"),
        "machine learning": auto,
        "parameters": sorted(
            f"{p.get('name')} ({p.get('dataType')}{', required' if p.get('required') else ''})"
            for p in response.get("parameters", [])
        ),
    }


def load(source: Path) -> dict[str, dict]:
    """Intent summaries from an intents folder, an unzipped agent export, or an export zip."""
    if source.is_file() and zipfile.is_zipfile(source):
        with utils.file_errors(source), zipfile.ZipFile(source) as archive:
            names = [
                n
                for n in archive.namelist()
                if re.search(r"(^|/)intents/[^/]+\.json$", n)
            ]
            if not names:
                raise exceptions.FileSystemError(
                    f"No intents folder was found in {source}."
                )
            return summarize(
                {Path(n).name: _json(archive.read(n), f"{source}:{n}") for n in names}
            )
    if source.is_dir():
        folder = source / "intents" if (source / "intents").is_dir() else source
        files = {}
        for path in sorted(folder.glob("*.json")):
            with utils.file_errors(path):
                files[path.name] = _json(path.read_bytes(), str(path))
        return summarize(files)
    raise exceptions.FileSystemError(
        f"{source} is not a folder or zip file of Dialogflow intents."
    )


def _json(content: bytes, where: str) -> Any:
    try:
        return json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise exceptions.FileSystemError(
            f"{where} is not a valid intent JSON file ({error})."
        ) from error


def compare(new: dict[str, dict], old: dict[str, dict], source: str) -> CompareResult:
    result = CompareResult(source=source)
    for name in sorted(new.keys() - old.keys()):
        result.added.append(name)
    for name in sorted(old.keys() - new.keys()):
        result.removed.append(name)
    for name in sorted(new.keys() & old.keys()):
        details = _differences(new[name], old[name])
        if details:
            result.changed.append(IntentChange(name, details))
        else:
            result.unchanged += 1
    return result


def _differences(new: dict, old: dict) -> list[str]:
    details = []
    new_fields, old_fields = new.get("intent", {}), old.get("intent", {})
    for field in new_fields.keys() | old_fields.keys():
        if new_fields.get(field) != old_fields.get(field):
            details.append(
                f"{field}: {_show(old_fields.get(field))} \u2192 {_show(new_fields.get(field))}"
            )
    new_phrases, old_phrases = new.get("phrases", {}), old.get("phrases", {})
    for language in sorted(new_phrases.keys() | old_phrases.keys()):
        if language not in old_phrases:
            details.append(f"{language} phrases added ({len(new_phrases[language])})")
        elif language not in new_phrases:
            details.append(f"{language} phrases removed ({len(old_phrases[language])})")
        else:
            added = len(set(new_phrases[language]) - set(old_phrases[language]))
            removed = len(set(old_phrases[language]) - set(new_phrases[language]))
            if added or removed:
                details.append(f"{language} phrases: {added} added, {removed} removed")
    return sorted(details)


def _show(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, list):
        return ", ".join(value) or "none"
    return str(value)
