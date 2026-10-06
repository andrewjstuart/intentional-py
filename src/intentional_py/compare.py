"""Compare generated intents with a previous build or a Dialogflow ES agent export.

Intents are compared by name on the fields this tool writes: contexts, action,
priority, machine learning, parameters, and the training phrases per language.
IDs and timestamps are ignored, since they change with every build or export.
"""

import json
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from intentional_py import exceptions, models, utils
from intentional_py.reporting import CompareResult, IntentChange

USERSAYS = re.compile(r"(.+)_usersays_([A-Za-z-]+)$")
INTENTS_JSON = re.compile(r"^(.*?intents/)[^/]+\.json$")


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


def _intents_prefix(names: Iterable[str]) -> str:
    """The folder an export zip keeps its intent JSON under. Confirmed to be a
    top-level 'intents/' folder (alongside 'agent.json' and 'package.json'), but
    detected from the zip's own contents rather than hardcoded in case some exports
    nest it differently. Falls back to 'intents/' for an export with no intents yet.
    """
    for name in names:
        match = INTENTS_JSON.match(name)
        if match:
            return match[1]
    return "intents/"


def export_contents(export: Path) -> tuple[str, list[str]]:
    """The intents/ folder prefix and full namelist of an export zip, read once so the
    caller can work out what a removal row refers to before merge_export() rewrites it."""
    with utils.file_errors(export), zipfile.ZipFile(export) as archive:
        names = archive.namelist()
    return _intents_prefix(names), names


def removal_arcnames(
    removal: models.RemovalRow,
    prefix: str,
    names: set[str],
    languages: models.LanguageSettings,
) -> list[str]:
    """Existing zip entries a removal row refers to, mirroring
    build_intents._removal_targets() but against an export zip's namelist instead of
    the filesystem."""
    if removal.language == languages.default_language:
        found = [name for name in (f"{prefix}{removal.intent}.json",) if name in names]
        found += sorted(
            name
            for name in names
            if name.startswith(f"{prefix}{removal.intent}_usersays_")
            and name.endswith(".json")
        )
        return found
    candidate = f"{prefix}{removal.intent}_usersays_{removal.language}.json"
    return [candidate] if candidate in names else []


def merge_export(
    export: Path,
    files_to_write: dict[Path, dict],
    removed_arcnames: set[str],
    prefix: str,
    output: Path,
) -> None:
    """Write `output` as a complete copy of `export` (which replaces the whole agent,
    so anything missing is deleted): each of `files_to_write` is added, or replaces
    its existing intents/ entry, and every name in `removed_arcnames` is dropped;
    everything else - other intents, entities, agent.json, package.json - is carried
    over unchanged. `export` itself is never modified."""
    new_arcnames = {
        f"{prefix}{Path(file).name}": data for file, data in files_to_write.items()
    }
    with (
        utils.file_errors(export),
        zipfile.ZipFile(export) as source,
        utils.file_errors(output),
        zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as dest,
    ):
        for info in source.infolist():
            if info.filename in new_arcnames or info.filename in removed_arcnames:
                continue
            dest.writestr(info, source.read(info.filename))
        for arcname, data in new_arcnames.items():
            dest.writestr(arcname, json.dumps(data, indent=4))


def write_import_zip(
    files_to_write: dict[Path, dict],
    prefix: str,
    output: Path,
) -> None:
    """Write `output` as a minimal zip (which only adds new intents and overwrites
    ones with the same name, and never deletes): just this build's intent files,
    nothing from the export itself - agent.json/package.json aren't written by this
    tool, so there's nothing of ours to merge into them, and Import leaves everything
    else alone anyway. A '-'/'--' removal row has no effect here, since Import can't
    delete; those intents still need removing from the agent by hand (see
    build_intents.package_export()'s `needs_manual_removal`).
    """
    with (
        utils.file_errors(output),
        zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as dest,
    ):
        for file, data in files_to_write.items():
            dest.writestr(f"{prefix}{Path(file).name}", json.dumps(data, indent=4))
